"""Human-in-the-loop manual OCR fixing and immutable raw OCR preservation."""
from __future__ import annotations

import csv
from datetime import datetime, timezone
from html import escape
import io
import json
from pathlib import Path
from typing import Any

from hanviet.common.io import atomic_bytes, write_json

OCR_DECISIONS = {
    "ACCEPT_PRIMARY",
    "ACCEPT_SECONDARY",
    "MANUAL_EDIT",
    "INSERT_MASK",
    "FIX_READING_ORDER",
    "REPROCESS",
    "DEFER",
}


def highlight_char_ops_html(char_ops: list[dict[str, Any]], side: str) -> str:
    """Render HTML spans highlighting OCR differences without altering source text."""
    parts: list[str] = []
    for op in char_ops:
        kind = op["op"]
        token = op["a"] if side == "primary" else op["b"]
        if kind == "equal":
            parts.append(escape(token))
        elif kind == "substitution":
            parts.append(f'<mark style="background:#ffe0b2">{escape(token)}</mark>')
        elif (kind == "deletion" and side == "primary") or (kind == "insertion" and side == "secondary"):
            parts.append(f'<mark style="background:#ffcdd2">{escape(token)}</mark>')
    return "".join(parts)


def build_ocr_review_table(cross_check_report: dict[str, Any]) -> list[dict[str, Any]]:
    """Build flat tabular review rows preserving both engines' predictions and confidences separately."""
    rows: list[dict[str, Any]] = []
    incomplete_global = cross_check_report.get("status") == "CROSS_CHECK_INCOMPLETE"
    for item in cross_check_report.get("items", []):
        p = item.get("primary") or {}
        s = item.get("secondary") or {}
        rows.append(
            {
                "item_id": item["item_id"],
                "source_id": item["source_id"],
                "variant": item["variant"],
                "status": item["status"],
                "cross_check_complete": not incomplete_global and bool(p) and bool(s),
                "image_reference": p.get("image_reference") or s.get("image_reference") or "",
                "primary_bbox": json.dumps(p.get("bbox")) if p.get("bbox") is not None else "",
                "secondary_bbox": json.dumps(s.get("bbox")) if s.get("bbox") is not None else "",
                "primary_engine": p.get("engine", ""),
                "primary_text": p.get("text", ""),
                "primary_confidence": "" if p.get("confidence") is None else p.get("confidence"),
                "secondary_engine": s.get("engine", ""),
                "secondary_text": s.get("text", ""),
                "secondary_confidence": "" if s.get("confidence") is None else s.get("confidence"),
                "issue_types": ";".join(item.get("issue_types", [])),
                "decision": "",
                "corrected_text": "",
                "reading_order_override": "",
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


def render_ocr_diff_html(cross_check_report: dict[str, Any]) -> str:
    """Render human-reviewable HTML report showing both engines and highlighted character diffs."""
    lines = [
        "<html><head><meta charset='utf-8'><style>"
        "table{border-collapse:collapse;width:100%;font-family:sans-serif}"
        "th,td{border:1px solid #ccc;padding:6px;vertical-align:top;text-align:left}"
        "</style></head><body>",
        f"<h3>Dual-OCR Cross-Check Review ({escape(cross_check_report.get('variant', ''))}) — Status: {escape(cross_check_report.get('status', ''))}</h3>",
        "<table><tr><th>ID</th><th>Status</th><th>Primary</th><th>Secondary</th><th>Issues</th></tr>",
    ]
    for item in cross_check_report.get("items", []):
        p = item.get("primary") or {}
        s = item.get("secondary") or {}
        ops = (item.get("comparison") or {}).get("char_ops", [])
        p_html = highlight_char_ops_html(ops, "primary") if ops else escape(p.get("text", ""))
        s_html = highlight_char_ops_html(ops, "secondary") if ops else escape(s.get("text", ""))
        p_conf = f" (conf={p.get('confidence')})" if p.get("confidence") is not None else ""
        s_conf = f" (conf={s.get('confidence')})" if s.get("confidence") is not None else ""
        lines.append(
            f"<tr><td>{escape(item['item_id'])}</td><td>{escape(item['status'])}</td>"
            f"<td><b>{escape(p.get('engine', '-'))}{escape(p_conf)}</b><br>{p_html}</td>"
            f"<td><b>{escape(s.get('engine', '-'))}{escape(s_conf)}</b><br>{s_html}</td>"
            f"<td>{escape(', '.join(item.get('issue_types', [])))}</td></tr>"
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
) -> dict[str, Any]:
    """Apply explicit human OCR decisions while never modifying raw engine files.

    [MASK] is inserted only on explicit INSERT_MASK or MANUAL_EDIT decisions, never automatically.
    """
    by_id = {d["item_id"]: d for d in decisions}
    output_lines: list[tuple[int, str]] = []
    logs: list[dict[str, Any]] = []
    reviewed_records: list[dict[str, Any]] = []

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
        elif action in {"REPROCESS", "DEFER", ""}:
            chosen_text = None
            status = action or "DEFERRED"

        order = int(dec["reading_order_override"]) if str(dec.get("reading_order_override", "")).strip() else pos
        if chosen_text is not None:
            output_lines.append((order, chosen_text))

        entry = {
            "item_id": iid,
            "decision": action or "DEFER",
            "status": status,
            "primary_text": p_text,
            "secondary_text": s_text,
            "final_text": chosen_text,
            "reading_order": order,
            "note": dec.get("note", ""),
            "cross_check_complete": bool(p and s and item.get("status") != "CROSS_CHECK_INCOMPLETE"),
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
    result = {
        "cross_check_status": cross_check_report.get("status"),
        "reviewed_count": sum(1 for r in reviewed_records if r["final_text"] is not None),
        "deferred_count": sum(1 for r in reviewed_records if r["final_text"] is None),
        "transcription_text": ordered_text,
        "records": reviewed_records,
    }
    if reviewed_json_path is not None:
        write_json(Path(reviewed_json_path), result)
    return result
