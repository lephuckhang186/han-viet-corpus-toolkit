"""Character/word-level Dual-OCR cross-check with geometry/reading-order matching (no confidence picking)."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
import re
from typing import Any
import unicodedata

from hanviet.extraction.schema import OCRRecord


def _to_rect(bbox: list[Any] | None) -> tuple[float, float, float, float] | None:
    if not bbox:
        return None
    if isinstance(bbox[0], (list, tuple)):
        xs = [float(p[0]) for p in bbox]
        ys = [float(p[1]) for p in bbox]
        return min(xs), min(ys), max(xs), max(ys)
    if len(bbox) == 4:
        return float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3])
    return None


def bbox_iou(b1: list[Any] | None, b2: list[Any] | None) -> float:
    """Compute intersection-over-union between two bboxes (quad or [x0,y0,x1,y1])."""
    r1, r2 = _to_rect(b1), _to_rect(b2)
    if r1 is None or r2 is None:
        return 0.0
    ix1, iy1 = max(r1[0], r2[0]), max(r1[1], r2[1])
    ix2, iy2 = min(r1[2], r2[2]), min(r1[3], r2[3])
    iw, ih = max(0.0, ix2 - ix1), max(0.0, iy2 - iy1)
    inter = iw * ih
    if inter <= 0.0:
        return 0.0
    area1 = max(0.0, r1[2] - r1[0]) * max(0.0, r1[3] - r1[1])
    area2 = max(0.0, r2[2] - r2[0]) * max(0.0, r2[3] - r2[1])
    union = area1 + area2 - inter
    return inter / union if union > 0 else 0.0


def levenshtein_align(seq_a: list[str], seq_b: list[str]) -> list[dict[str, Any]]:
    """Optimal Levenshtein sequence alignment yielding equal/substitution/insertion/deletion ops."""
    m, n = len(seq_a), len(seq_b)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(1, m + 1):
        dp[i][0] = i
    for j in range(1, n + 1):
        dp[0][j] = j
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            cost = 0 if seq_a[i - 1] == seq_b[j - 1] else 1
            dp[i][j] = min(
                dp[i - 1][j - 1] + cost,
                dp[i - 1][j] + 1,
                dp[i][j - 1] + 1,
            )
    ops: list[dict[str, Any]] = []
    i, j = m, n
    while i > 0 or j > 0:
        if i > 0 and j > 0:
            cost = 0 if seq_a[i - 1] == seq_b[j - 1] else 1
            if dp[i][j] == dp[i - 1][j - 1] + cost:
                op = "equal" if cost == 0 else "substitution"
                ops.append({"op": op, "a": seq_a[i - 1], "b": seq_b[j - 1], "pos_a": i - 1, "pos_b": j - 1})
                i -= 1
                j -= 1
                continue
        if i > 0 and dp[i][j] == dp[i - 1][j] + 1:
            ops.append({"op": "deletion", "a": seq_a[i - 1], "b": "", "pos_a": i - 1, "pos_b": j})
            i -= 1
        else:
            ops.append({"op": "insertion", "a": "", "b": seq_b[j - 1], "pos_a": i, "pos_b": j - 1})
            j -= 1
    ops.reverse()
    return ops


def _tokenize_han(text: str) -> list[str]:
    nfc = unicodedata.normalize("NFC", text)
    tokens: list[str] = []
    for chunk in re.split(r"(\[MASK\])", nfc):
        if chunk == "[MASK]":
            tokens.append(chunk)
        else:
            tokens.extend(list(chunk))
    return tokens


def _strip_viet_diacritics(token: str) -> str:
    nfd = unicodedata.normalize("NFD", token.lower())
    stripped = "".join(c for c in nfd if not unicodedata.category(c).startswith("M"))
    return stripped.replace("đ", "d")


_NUMBER_OR_ERA_RE = re.compile(r"\b(?:\d+|[IVXLCDM]{2,})\b")


def compare_han_texts(primary_text: str, secondary_text: str) -> dict[str, Any]:
    """Character-level Levenshtein alignment on NFC comparison copies of Han text."""
    seq_a = _tokenize_han(primary_text)
    seq_b = _tokenize_han(secondary_text)
    ops = levenshtein_align(seq_a, seq_b)
    diffs = [o for o in ops if o["op"] != "equal"]
    issue_types = sorted({o["op"] for o in diffs})
    return {
        "agreed": len(diffs) == 0,
        "agreement_note": "AGREED_UNVERIFIED" if not diffs else "DISAGREEMENT",
        "char_ops": ops,
        "disagreement_count": len(diffs),
        "issue_types": issue_types,
    }


def compare_viet_texts(primary_text: str, secondary_text: str) -> dict[str, Any]:
    """Character-level & word-level comparison on NFC copies detecting tone & number mismatches."""
    nfc_a = unicodedata.normalize("NFC", primary_text)
    nfc_b = unicodedata.normalize("NFC", secondary_text)
    char_ops = levenshtein_align(list(nfc_a), list(nfc_b))
    words_a = nfc_a.split()
    words_b = nfc_b.split()
    word_ops = levenshtein_align(words_a, words_b)

    issue_types: set[str] = set()
    tone_mismatches: list[dict[str, str]] = []
    number_mismatches: list[dict[str, str]] = []
    for op in word_ops:
        if op["op"] == "equal":
            continue
        issue_types.add(op["op"])
        if op["op"] == "substitution":
            if _strip_viet_diacritics(op["a"]) == _strip_viet_diacritics(op["b"]) and op["a"].lower() != op["b"].lower():
                issue_types.add("tone_mismatch")
                tone_mismatches.append({"primary": op["a"], "secondary": op["b"]})
            if _NUMBER_OR_ERA_RE.search(op["a"]) or _NUMBER_OR_ERA_RE.search(op["b"]):
                issue_types.add("number_or_era_mismatch")
                number_mismatches.append({"primary": op["a"], "secondary": op["b"]})
        elif _NUMBER_OR_ERA_RE.search(op["a"] or op["b"]):
            issue_types.add("number_or_era_mismatch")
            number_mismatches.append({"primary": op["a"], "secondary": op["b"]})

    char_diffs = [o for o in char_ops if o["op"] != "equal"]
    word_diffs = [o for o in word_ops if o["op"] != "equal"]
    return {
        "agreed": len(char_diffs) == 0,
        "agreement_note": "AGREED_UNVERIFIED" if not char_diffs else "DISAGREEMENT",
        "char_ops": char_ops,
        "word_ops": word_ops,
        "disagreement_count": len(char_diffs),
        "word_disagreement_count": len(word_diffs),
        "tone_mismatches": tone_mismatches,
        "number_mismatches": number_mismatches,
        "issue_types": sorted(issue_types),
    }


@dataclass
class CrossCheckItem:
    item_id: str
    source_id: str
    variant: str
    primary: OCRRecord | None
    secondary: OCRRecord | None
    match_method: str
    status: str  # AGREED_UNVERIFIED | DISAGREEMENT | MISSING_REGION | NEEDS_REVIEW | CROSS_CHECK_INCOMPLETE
    issue_types: list[str] = field(default_factory=list)
    comparison: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "item_id": self.item_id,
            "source_id": self.source_id,
            "variant": self.variant,
            "primary": self.primary.to_dict() if self.primary else None,
            "secondary": self.secondary.to_dict() if self.secondary else None,
            "match_method": self.match_method,
            "status": self.status,
            "issue_types": self.issue_types,
            "comparison": self.comparison,
        }


def cross_check_records(
    primary_records: list[OCRRecord],
    secondary_records: list[OCRRecord],
    *,
    variant: str,
    iou_threshold: float = 0.3,
) -> dict[str, Any]:
    """Match primary & secondary OCR records without selecting winners by uncalibrated confidence."""
    compare_fn = compare_han_texts if variant == "han" else compare_viet_texts

    usable_sec = [r for r in secondary_records if r.status not in {"FAILED", "UNPROCESSED"}]
    if not usable_sec:
        items = [
            CrossCheckItem(
                item_id=f"xc_{idx:04d}",
                source_id=p.source_id,
                variant=variant,
                primary=p,
                secondary=None,
                match_method="single_engine_only",
                status="CROSS_CHECK_INCOMPLETE",
                issue_types=["cross_check_incomplete"],
                comparison={},
            )
            for idx, p in enumerate(primary_records, 1)
        ]
        return {
            "status": "CROSS_CHECK_INCOMPLETE",
            "variant": variant,
            "items": [it.to_dict() for it in items],
            "summary": {"total": len(items), "agreed_unverified": 0, "disagreements": 0, "incomplete": len(items)},
        }

    # Handle page-level vs line-level granularity mismatch ONLY when the single record represents page-level text
    # (no per-line bbox or multi-line joined text), so genuine missing line detections still run bbox/region matching.
    def _is_page_level(recs: list[OCRRecord]) -> bool:
        return len(recs) == 1 and (recs[0].bbox is None or "\n" in recs[0].text)

    if len(primary_records) != len(usable_sec) and (_is_page_level(primary_records) or _is_page_level(usable_sec)):
        p_joined = "\n".join(r.text for r in primary_records)
        s_joined = "\n".join(r.text for r in usable_sec)
        comp = compare_fn(p_joined, s_joined)
        p_rep = primary_records[0] if len(primary_records) == 1 else OCRRecord(
            **{**asdict(primary_records[0]), "text": p_joined, "reading_order": 1, "region_id": "page_joined"}
        )
        s_rep = usable_sec[0] if len(usable_sec) == 1 else OCRRecord(
            **{**asdict(usable_sec[0]), "text": s_joined, "reading_order": 1, "region_id": "page_joined"}
        )
        item = CrossCheckItem(
            item_id="xc_page_0001",
            source_id=p_rep.source_id,
            variant=variant,
            primary=p_rep,
            secondary=s_rep,
            match_method="granularity_page_vs_line_needs_review",
            status="NEEDS_REVIEW",
            issue_types=sorted(set(comp["issue_types"]) | {"granularity_mismatch"}),
            comparison=comp,
        )
        return {
            "status": "NEEDS_REVIEW",
            "variant": variant,
            "items": [item.to_dict()],
            "summary": {"total": 1, "agreed_unverified": 0, "disagreements": 1, "incomplete": 0},
        }

    # Match by geometry IoU first if both provide bboxes, else by (source_id, region_id / reading_order)
    matched_sec: set[int] = set()
    items: list[CrossCheckItem] = []

    for idx, p in enumerate(primary_records, 1):
        best_s_idx = None
        method = ""

        # 1) Bbox IoU matching when coordinates are present
        if p.bbox is not None and any(s.bbox is not None for s in usable_sec):
            best_score = 0.0
            for s_idx, s in enumerate(usable_sec):
                if s_idx in matched_sec or s.source_id != p.source_id:
                    continue
                iou = bbox_iou(p.bbox, s.bbox)
                if iou >= iou_threshold and iou > best_score:
                    best_score = iou
                    best_s_idx = s_idx
                    method = "bbox_iou"

        # 2) Region ID + source ID fallback
        if best_s_idx is None:
            for s_idx, s in enumerate(usable_sec):
                if s_idx not in matched_sec and s.source_id == p.source_id and s.region_id == p.region_id:
                    best_s_idx = s_idx
                    method = "source_and_region_id"
                    break

        # 3) Reading order fallback when region counts match
        if best_s_idx is None and len(primary_records) == len(usable_sec):
            for s_idx, s in enumerate(usable_sec):
                if s_idx not in matched_sec and s.source_id == p.source_id and s.reading_order == p.reading_order:
                    best_s_idx = s_idx
                    method = "reading_order"
                    break

        if best_s_idx is None:
            items.append(
                CrossCheckItem(
                    item_id=f"xc_{idx:04d}",
                    source_id=p.source_id,
                    variant=variant,
                    primary=p,
                    secondary=None,
                    match_method="unmatched",
                    status="MISSING_REGION",
                    issue_types=["missing_region"],
                    comparison={},
                )
            )
            continue

        matched_sec.add(best_s_idx)
        s = usable_sec[best_s_idx]
        comp = compare_fn(p.text, s.text)
        issues = list(comp["issue_types"])
        if p.reading_order is not None and s.reading_order is not None and p.reading_order != s.reading_order:
            issues.append("reading_order_mismatch")
        status = "AGREED_UNVERIFIED" if not issues else "DISAGREEMENT"
        items.append(
            CrossCheckItem(
                item_id=f"xc_{idx:04d}",
                source_id=p.source_id,
                variant=variant,
                primary=p,
                secondary=s,
                match_method=method,
                status=status,
                issue_types=sorted(set(issues)),
                comparison=comp,
            )
        )

    # Any extra secondary regions not matched to primary
    for s_idx, s in enumerate(usable_sec):
        if s_idx not in matched_sec:
            items.append(
                CrossCheckItem(
                    item_id=f"xc_extra_{s_idx + 1:04d}",
                    source_id=s.source_id,
                    variant=variant,
                    primary=None,
                    secondary=s,
                    match_method="unmatched_secondary",
                    status="MISSING_REGION",
                    issue_types=["missing_region"],
                    comparison={},
                )
            )

    agreed_count = sum(1 for it in items if it.status == "AGREED_UNVERIFIED")
    disagree_count = len(items) - agreed_count
    overall = "COMPLETE" if not any(it.status == "MISSING_REGION" for it in items) else "NEEDS_REVIEW"
    return {
        "status": overall,
        "variant": variant,
        "items": [it.to_dict() for it in items],
        "summary": {
            "total": len(items),
            "agreed_unverified": agreed_count,
            "disagreements": disagree_count,
            "incomplete": 0,
        },
    }
