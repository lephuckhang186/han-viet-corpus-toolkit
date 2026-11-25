"""Human-in-the-loop manual OCR fixing, visualization, and immutable raw OCR preservation."""
from __future__ import annotations

import csv
from datetime import datetime, timezone
from html import escape
import io
import json
from pathlib import Path
from typing import Any

from hanviet.common.io import atomic_bytes, read_json, write_json

OCR_DECISIONS = {
    "ACCEPT_PRIMARY",
    "ACCEPT_SECONDARY",
    "MANUAL_EDIT",
    "KEEP_BOTH_AGREED",
    "INSERT_MASK",
    "FIX_READING_ORDER",
    "REPROCESS",
    "REQUEST_SOURCE_REVIEW",
    "DEFER",
}

REVIEW_STATUSES = {
    "PENDING",
    "IN_REVIEW",
    "REVIEWED",
    "APPROVED",
    "DEFERRED",
    "SUPERSEDED",
}


def highlight_char_ops_html(char_ops: list[dict[str, Any]], side: str) -> str:
    """Render HTML spans highlighting OCR differences with explicit operation tags (not color-only)."""
    parts: list[str] = []
    for op in char_ops:
        kind = op["op"]
        token = op["a"] if side == "primary" else op["b"]
        if kind == "equal":
            parts.append(escape(token))
        elif kind == "substitution":
            parts.append(
                f'<mark title="SUBSTITUTION: {escape(op["a"])} -> {escape(op["b"])}" '
                f'style="background:#ffe0b2;border-bottom:2px solid #e65100">[SUB:{escape(token)}]</mark>'
            )
        elif kind == "deletion" and side == "primary":
            parts.append(
                f'<mark title="DELETION (missing in secondary)" '
                f'style="background:#ffcdd2;border-bottom:2px solid #b71c1c">[DEL:{escape(token)}]</mark>'
            )
        elif kind == "insertion" and side == "secondary":
            parts.append(
                f'<mark title="INSERTION (added in secondary)" '
                f'style="background:#c8e6c9;border-bottom:2px solid #1b5e20">[INS:{escape(token)}]</mark>'
            )
    return "".join(parts)


def format_char_diff_text(char_ops: list[dict[str, Any]]) -> str:
    """Readable plain-text diff summary showing explicit SUB / INS / DEL operations."""
    diffs = []
    for op in char_ops:
        if op["op"] == "substitution":
            diffs.append(f"SUBSTITUTION {op['a']} <-> {op['b']}")
        elif op["op"] == "insertion":
            diffs.append(f"INSERTION +{op['b']}")
        elif op["op"] == "deletion":
            diffs.append(f"DELETION -{op['a']}")
    return " | ".join(diffs)


def render_region_overlay_png(
    image_path: Path,
    records: list[dict[str, Any]],
    output_path: Path,
) -> Path:
    """Draw ONLY verified bounding boxes/polygons and reading-order indices onto a copy of source image."""
    from PIL import Image, ImageDraw  # noqa: PLC0415

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(image_path) as img:
        canvas = img.convert("RGB")
    draw = ImageDraw.Draw(canvas)
    for rec in records:
        bbox = rec.get("bbox") or rec.get("polygon")
        if not bbox:
            continue
        if isinstance(bbox[0], (list, tuple)):
            pts = [(float(p[0]), float(p[1])) for p in bbox]
            draw.polygon(pts, outline=(220, 40, 40), width=2)
            label_xy = pts[0]
        elif len(bbox) == 4:
            x0, y0, x1, y1 = [float(v) for v in bbox]
            draw.rectangle((x0, y0, x1, y1), outline=(220, 40, 40), width=2)
            label_xy = (x0, y0)
        else:
            continue
        order = rec.get("reading_order", "")
        rid = rec.get("region_id", "")
        draw.text((max(0.0, label_xy[0]), max(0.0, label_xy[1] - 12)), f"#{order} (r{rid})", fill=(0, 90, 200))
    canvas.save(output_path, format="PNG")
    return output_path


def build_ocr_review_table(cross_check_report: dict[str, Any]) -> list[dict[str, Any]]:
    """Build flat tabular review rows preserving both engines' predictions and confidences separately."""
    rows: list[dict[str, Any]] = []
    incomplete_global = cross_check_report.get("status") == "CROSS_CHECK_INCOMPLETE"
    for item in cross_check_report.get("items", []):
        p = item.get("primary") or {}
        s = item.get("secondary") or {}
        ops = (item.get("comparison") or {}).get("char_ops", [])
        rows.append(
            {
                "item_id": item["item_id"],
                "source_id": item["source_id"],
                "work_id": p.get("work_id") or s.get("work_id") or "",
                "pdf_page": p.get("pdf_page") if p.get("pdf_page") is not None else s.get("pdf_page"),
                "region_id": p.get("region_id") if p.get("region_id") is not None else s.get("region_id"),
                "variant": item["variant"],
                "match_type": item.get("match_type", "1-1"),
                "status": item["status"],
                "cross_check_complete": not incomplete_global and bool(p) and bool(s),
                "image_reference": p.get("image_reference") or s.get("image_reference") or "",
                "input_sha256": p.get("input_sha256") or s.get("input_sha256") or "",
                "primary_bbox": json.dumps(p.get("bbox")) if p.get("bbox") is not None else "",
                "secondary_bbox": json.dumps(s.get("bbox")) if s.get("bbox") is not None else "",
                "primary_engine": p.get("engine", ""),
                "primary_text": p.get("text", ""),
                "primary_confidence": "" if p.get("confidence") is None else p.get("confidence"),
                "secondary_engine": s.get("engine", ""),
                "secondary_text": s.get("text", ""),
                "secondary_confidence": "" if s.get("confidence") is None else s.get("confidence"),
                "char_diff_summary": format_char_diff_text(ops) if ops else "",
                "issue_types": ";".join(item.get("issue_types", [])),
                "decision": "",
                "corrected_text": "",
                "reading_order_override": "",
                "reason": "",
                "reviewed_by": "",
                "note": "",
            }
        )
    return rows


def export_ocr_review_csv(path: Path, review_rows: list[dict[str, Any]]) -> Path:
    path = Path(path)
    if not review_rows:
        raise ValueError("No cross-check rows to export.")
    fields = list(review_rows[0].keys())
    buf = io.StringIO(newline="")
    writer = csv.DictWriter(buf, fieldnames=fields)
    writer.writeheader()
    writer.writerows(review_rows)
    atomic_bytes(path, buf.getvalue().encode("utf-8-sig"))
    return path


def export_cross_check_xlsx(path: Path, review_rows: list[dict[str, Any]], *, sheet_name: str = "CROSS_CHECK") -> Path:
    """Export tabular cross-check rows or unmatched regions cleanly to Excel (.xlsx)."""
    import xlsxwriter  # noqa: PLC0415

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    headers = list(review_rows[0].keys()) if review_rows else ["item_id", "status", "note"]
    buf = io.BytesIO()
    wb = xlsxwriter.Workbook(buf, {"in_memory": True})
    ws = wb.add_worksheet(sheet_name[:31])
    hdr_fmt = wb.add_format({"bold": True, "bg_color": "#EFEFEF", "border": 1})
    for col, h in enumerate(headers):
        ws.write(0, col, h, hdr_fmt)
    for row_idx, row in enumerate(review_rows, 1):
        for col, h in enumerate(headers):
            val = row.get(h, "")
            ws.write(row_idx, col, "" if val is None else str(val))
    wb.close()
    atomic_bytes(path, buf.getvalue())
    return path


def render_ocr_diff_html(cross_check_report: dict[str, Any]) -> str:
    """Render human-reviewable HTML report showing both engines and explicit tagged character diffs."""
    lines = [
        "<html><head><meta charset='utf-8'><style>"
        "table{border-collapse:collapse;width:100%;font-family:sans-serif}"
        "th,td{border:1px solid #ccc;padding:6px;vertical-align:top;text-align:left}"
        "</style></head><body>",
        f"<h3>Dual-OCR Cross-Check Review ({escape(cross_check_report.get('variant', ''))}) — Status: {escape(cross_check_report.get('status', ''))}</h3>",
        "<table><tr><th>ID</th><th>Status</th><th>Primary</th><th>Secondary</th><th>Issues & Diff Ops</th></tr>",
    ]
    for item in cross_check_report.get("items", []):
        p = item.get("primary") or {}
        s = item.get("secondary") or {}
        ops = (item.get("comparison") or {}).get("char_ops", [])
        p_html = highlight_char_ops_html(ops, "primary") if ops else escape(p.get("text", ""))
        s_html = highlight_char_ops_html(ops, "secondary") if ops else escape(s.get("text", ""))
        diff_summary = format_char_diff_text(ops) if ops else ""
        p_conf = f" (conf={p.get('confidence')})" if p.get("confidence") is not None else ""
        s_conf = f" (conf={s.get('confidence')})" if s.get("confidence") is not None else ""
        lines.append(
            f"<tr><td>{escape(item['item_id'])}<br><small>{escape(item.get('match_type', ''))}</small></td>"
            f"<td>{escape(item['status'])}</td>"
            f"<td><b>{escape(p.get('engine', '-'))}{escape(p_conf)}</b><br>{p_html}</td>"
            f"<td><b>{escape(s.get('engine', '-'))}{escape(s_conf)}</b><br>{s_html}</td>"
            f"<td>{escape(', '.join(item.get('issue_types', [])))}"
            f"{'<br><small>' + escape(diff_summary) + '</small>' if diff_summary else ''}</td></tr>"
        )
    lines.append("</table></body></html>")
    return "\n".join(lines)


def apply_manual_ocr_decisions(
    cross_check_report: dict[str, Any],
    decisions: list[dict[str, Any]],
    *,
    corrected_text_path: Path | None = None,
    correction_log_path: Path | None = None,
    reviewed_json_path: Path | None = None,
    raw_protected_roots: list[Path] | None = None,
    expected_work_id: str | None = None,
    expected_member_id: str | None = None,
    reviewer: str = "",
    allow_overwrite_approved: bool = False,
) -> dict[str, Any]:
    """Apply explicit human OCR decisions safely while preserving immutable raw OCR & approved versions.

    Enforces:
    - All `item_id`s in `decisions` must exist in `cross_check_report` and must not duplicate/overlap.
    - `base_fingerprint` / `region_id` / `before` must match when supplied (stale decisions raise ValueError).
    - Raw OCR directories and existing APPROVED outputs cannot be overwritten unless explicitly allowed.
    - `[MASK]` is inserted ONLY via explicit INSERT_MASK or MANUAL_EDIT decisions.
    """
    for target in (corrected_text_path, correction_log_path, reviewed_json_path):
        if target is None:
            continue
        t_resolved = Path(target).resolve()
        for raw_root in raw_protected_roots or ():
            r_resolved = Path(raw_root).resolve()
            if t_resolved == r_resolved or r_resolved in t_resolved.parents:
                raise PermissionError(f"Refusing to overwrite protected raw OCR location: {t_resolved}")

    if reviewed_json_path is not None and Path(reviewed_json_path).is_file() and not allow_overwrite_approved:
        existing = read_json(Path(reviewed_json_path))
        if existing.get("review_status") == "APPROVED" or existing.get("approved") is True:
            raise FileExistsError(
                f"Refusing to overwrite already APPROVED OCR transcription: {reviewed_json_path}"
            )

    items_by_id = {it["item_id"]: it for it in cross_check_report.get("items", [])}
    by_id: dict[str, dict[str, Any]] = {}
    for dec in decisions:
        iid = dec.get("item_id")
        if iid not in items_by_id:
            raise ValueError(f"Invalid or unknown OCR item_id in decision: {iid!r}")
        if iid in by_id:
            raise ValueError(f"Overlapping/duplicate manual OCR decision for item_id: {iid!r}")

        it = items_by_id[iid]
        p = it.get("primary") or {}
        s = it.get("secondary") or {}
        if expected_work_id and (p.get("work_id") or s.get("work_id")) not in {None, "", expected_work_id}:
            raise ValueError(f"Decision work_id mismatch for {iid}: expected {expected_work_id!r}")
        if expected_member_id and (p.get("member_id") or s.get("member_id")) not in {None, "", expected_member_id}:
            raise ValueError(f"Decision member_id mismatch for {iid}: expected {expected_member_id!r}")
        if "region_id" in dec and dec["region_id"] not in {None, "", p.get("region_id"), s.get("region_id")}:
            raise ValueError(f"Decision region_id mismatch for {iid}: {dec['region_id']!r}")
        actual_fp = p.get("input_sha256") or s.get("input_sha256") or ""
        if dec.get("base_fingerprint") and actual_fp and dec["base_fingerprint"] != actual_fp:
            raise ValueError(
                f"Stale input fingerprint for {iid}: decision={dec['base_fingerprint']!r}, current={actual_fp!r}"
            )
        if dec.get("before") is not None and dec["before"] not in {p.get("text", ""), s.get("text", "")}:
            raise ValueError(f"Stale 'before' text mismatch for {iid}.")
        by_id[iid] = dec

    output_lines: list[tuple[int, str]] = []
    logs: list[dict[str, Any]] = []
    reviewed_records: list[dict[str, Any]] = []
    corr_counter = 0

    for pos, item in enumerate(cross_check_report.get("items", []), 1):
        iid = item["item_id"]
        dec = by_id.get(iid, {})
        action = (dec.get("decision") or "").strip().upper()
        if action and action not in OCR_DECISIONS:
            raise ValueError(f"Unsupported manual OCR decision for {iid}: {action!r}")

        p = item.get("primary") or {}
        s = item.get("secondary") or {}
        p_text = p.get("text", "")
        s_text = s.get("text", "")
        chosen_text: str | None = None
        status = "PENDING_REVIEW"

        if action == "ACCEPT_PRIMARY":
            chosen_text = p_text
            status = "REVIEWED" if item.get("status") != "CROSS_CHECK_INCOMPLETE" else "REVIEWED_SINGLE_ENGINE_ONLY"
        elif action == "ACCEPT_SECONDARY":
            if not s:
                raise ValueError(f"Cannot ACCEPT_SECONDARY for {iid}: secondary record missing.")
            chosen_text = s_text
            status = "REVIEWED"
        elif action == "KEEP_BOTH_AGREED":
            if item.get("status") != "AGREED_UNVERIFIED" and p_text != s_text:
                raise ValueError(f"Cannot KEEP_BOTH_AGREED for {iid}: primary and secondary disagree.")
            chosen_text = p_text or s_text
            status = "REVIEWED"
        elif action == "MANUAL_EDIT":
            chosen_text = str(dec.get("corrected_text", ""))
            status = "REVIEWED"
        elif action == "INSERT_MASK":
            if dec.get("corrected_text"):
                chosen_text = str(dec["corrected_text"])
                if "[MASK]" not in chosen_text:
                    raise ValueError(f"INSERT_MASK for {iid} must contain [MASK].")
            else:
                chosen_text = "[MASK]"
            status = "REVIEWED_WITH_MASK"
        elif action == "FIX_READING_ORDER":
            chosen_text = str(dec.get("corrected_text") or p_text or s_text)
            status = "REVIEWED_ORDER_FIXED"
        elif action in {"REPROCESS", "REQUEST_SOURCE_REVIEW", "DEFER", ""}:
            chosen_text = None
            status = action or "DEFERRED"

        order = int(dec["reading_order_override"]) if str(dec.get("reading_order_override", "")).strip() else pos
        if chosen_text is not None:
            output_lines.append((order, chosen_text))

        corr_counter += 1
        entry = {
            "correction_id": f"correction_{corr_counter:04d}",
            "item_id": iid,
            "region_id": p.get("region_id") if p.get("region_id") is not None else s.get("region_id"),
            "disagreement_ids": [
                d["disagreement_id"]
                for d in cross_check_report.get("disagreements", [])
                if d.get("item_id") == iid
            ],
            "decision": action or "DEFER",
            "status": status,
            "primary_text": p_text,
            "secondary_text": s_text,
            "before": p_text or s_text,
            "after": chosen_text,
            "final_text": chosen_text,
            "reading_order": order,
            "reason": dec.get("reason") or dec.get("note", ""),
            "note": dec.get("note", ""),
            "reviewed_by": dec.get("reviewed_by") or reviewer,
            "base_fingerprint": p.get("input_sha256") or s.get("input_sha256") or "",
            "cross_check_complete": bool(p and s and item.get("status") != "CROSS_CHECK_INCOMPLETE"),
            "reviewed_at": datetime.now(timezone.utc).isoformat(),
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        }
        reviewed_records.append(entry)
        if action:
            logs.append(entry)

    ordered_text = "\n".join(text for _, text in sorted(output_lines, key=lambda pair: pair[0]))
    if corrected_text_path is not None:
        atomic_bytes(Path(corrected_text_path), ordered_text.encode("utf-8"))
    if correction_log_path is not None:
        atomic_bytes(
            Path(correction_log_path),
            "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in logs).encode("utf-8"),
        )

    reviewed_count = sum(1 for r in reviewed_records if r["final_text"] is not None)
    deferred_count = sum(1 for r in reviewed_records if r["final_text"] is None)
    overall_status = "APPROVED" if (reviewed_records and deferred_count == 0) else (
        "IN_REVIEW" if reviewed_count > 0 else "PENDING"
    )
    result = {
        "cross_check_status": cross_check_report.get("status"),
        "review_status": overall_status,
        "approved": overall_status == "APPROVED",
        "reviewed_count": reviewed_count,
        "deferred_count": deferred_count,
        "transcription_text": ordered_text,
        "records": reviewed_records,
    }
    if reviewed_json_path is not None:
        write_json(Path(reviewed_json_path), result)
    return result
