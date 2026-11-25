"""Character/word-level Dual-OCR cross-check with normalization profiles, DP matching, and structured disagreements."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
import re
import time
from typing import Any
import unicodedata

from hanviet.extraction.cross_check.matcher import (
    bbox_center_distance,
    bbox_iou,
    bbox_overlap_ratio,
    detect_duplicate_regions,
    match_lines_dp,
    scope_key,
    validate_reading_order,
)
from hanviet.extraction.cross_check.normalization import (
    MASK_TOKEN,
    is_number_or_era_token,
    is_punctuation_token,
    is_rare_han_token,
    is_whitespace_token,
    tokenize_han_with_spans,
)
from hanviet.extraction.schema import OCRRecord


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


def _attach_original_spans(
    ops: list[dict[str, Any]],
    toks_a: list[Any],
    toks_b: list[Any],
) -> list[dict[str, Any]]:
    enriched: list[dict[str, Any]] = []
    for op in ops:
        item = dict(op)
        pa, pb = op["pos_a"], op["pos_b"]
        if op["op"] in {"equal", "substitution"}:
            ta, tb = toks_a[pa], toks_b[pb]
            item["orig_start_a"], item["orig_end_a"] = ta.orig_start, ta.orig_end
            item["orig_start_b"], item["orig_end_b"] = tb.orig_start, tb.orig_end
        elif op["op"] == "deletion":
            ta = toks_a[pa]
            item["orig_start_a"], item["orig_end_a"] = ta.orig_start, ta.orig_end
            b_off = toks_b[pb].orig_start if pb < len(toks_b) else (toks_b[-1].orig_end if toks_b else 0)
            item["orig_start_b"] = b_off
            item["orig_end_b"] = b_off
        else:
            tb = toks_b[pb]
            a_off = toks_a[pa].orig_start if pa < len(toks_a) else (toks_a[-1].orig_end if toks_a else 0)
            item["orig_start_a"] = a_off
            item["orig_end_a"] = a_off
            item["orig_start_b"], item["orig_end_b"] = tb.orig_start, tb.orig_end
        enriched.append(item)
    return enriched


def _strip_viet_diacritics(token: str) -> str:
    nfd = unicodedata.normalize("NFD", token.lower())
    stripped = "".join(c for c in nfd if not unicodedata.category(c).startswith("M"))
    return stripped.replace("đ", "d")


_NUMBER_OR_ERA_RE = re.compile(r"\b(?:\d+|[IVXLCDM]{2,})\b")


def compare_han_texts(
    primary_text: str,
    secondary_text: str,
    *,
    profile: str = "strict",
    punctuation_equivalents: dict[str, str] | None = None,
    include_content_profile: bool = True,
    max_dp_tokens: int = 4000,
) -> dict[str, Any]:
    """Character-level Levenshtein alignment on NFC comparison copies of Han text with strict & content profiles."""
    norm_a = tokenize_han_with_spans(primary_text, profile=profile, punctuation_equivalents=punctuation_equivalents)
    norm_b = tokenize_han_with_spans(secondary_text, profile=profile, punctuation_equivalents=punctuation_equivalents)
    seq_a = [t.unit for t in norm_a.tokens]
    seq_b = [t.unit for t in norm_b.tokens]

    warnings: list[str] = []
    if len(seq_a) * len(seq_b) > max_dp_tokens * max_dp_tokens:
        warnings.append(
            f"Character DP size exceeded cap ({len(seq_a)}x{len(seq_b)}); split into shorter lines/regions before alignment."
        )

    ops = _attach_original_spans(levenshtein_align(seq_a, seq_b), norm_a.tokens, norm_b.tokens)
    diffs = [o for o in ops if o["op"] != "equal"]
    issue_types = sorted({o["op"] for o in diffs})
    max_len = max(len(seq_a), len(seq_b))
    agreement_rate = 1.0 if max_len == 0 else max(0.0, 1.0 - (len(diffs) / max_len))

    result: dict[str, Any] = {
        "profile": profile,
        "agreed": len(diffs) == 0,
        "agreement_note": "AGREED_UNVERIFIED" if not diffs else "DISAGREEMENT",
        "agreement_rate": round(agreement_rate, 6),
        "char_ops": ops,
        "disagreement_count": len(diffs),
        "issue_types": issue_types,
        "offset_unit": "unicode_codepoint_original",
        "primary_normalized": norm_a.normalized,
        "secondary_normalized": norm_b.normalized,
        "warnings": warnings,
    }
    if profile == "strict" and include_content_profile:
        content_res = compare_han_texts(
            primary_text,
            secondary_text,
            profile="content",
            punctuation_equivalents=punctuation_equivalents,
            include_content_profile=False,
            max_dp_tokens=max_dp_tokens,
        )
        result["content_comparison"] = {
            "agreed": content_res["agreed"],
            "agreement_rate": content_res["agreement_rate"],
            "disagreement_count": content_res["disagreement_count"],
            "issue_types": content_res["issue_types"],
        }
    return result


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


def _classify_han_char_op(op: dict[str, Any]) -> tuple[str, str]:
    kind = op["op"]
    a, b = op["a"], op["b"]
    if MASK_TOKEN in {a, b}:
        return "UNREADABLE_CHARACTER", "HIGH"
    if is_rare_han_token(a) or is_rare_han_token(b):
        return "RARE_CHARACTER_MISMATCH", "HIGH"
    if is_number_or_era_token(a) or is_number_or_era_token(b):
        return "NUMBER_MISMATCH", "HIGH"
    if kind == "substitution" and is_punctuation_token(a) and is_punctuation_token(b):
        return "PUNCTUATION_MISMATCH", "MEDIUM"
    if (kind == "deletion" and is_punctuation_token(a)) or (kind == "insertion" and is_punctuation_token(b)):
        return "PUNCTUATION_MISMATCH", "MEDIUM"
    if (kind == "deletion" and is_whitespace_token(a)) or (kind == "insertion" and is_whitespace_token(b)) or (
        kind == "substitution" and is_whitespace_token(a) and is_whitespace_token(b)
    ):
        return "WHITESPACE_MISMATCH", "MEDIUM"
    if kind == "substitution":
        return "CHARACTER_MISMATCH", "HIGH"
    if kind == "insertion":
        return "CHARACTER_INSERTION", "HIGH"
    return "CHARACTER_DELETION", "HIGH"


def extract_han_disagreements(
    cross_check_report: dict[str, Any],
    *,
    low_confidence_threshold: float = 0.60,
) -> list[dict[str, Any]]:
    """Build structured Task 09 disagreement records across matched, unmatched, duplicate, and low-confidence items."""
    disagreements: list[dict[str, Any]] = []
    counter = 0
    items = cross_check_report.get("items", [])

    def _next_id() -> str:
        nonlocal counter
        counter += 1
        return f"diff_{counter:04d}"

    for idx, item in enumerate(items):
        p = item.get("primary")
        s = item.get("secondary")
        p_ids = item.get("primary_record_ids") or ([p["record_id"]] if p else [])
        s_ids = item.get("secondary_record_ids") or ([s["record_id"]] if s else [])
        ref = p or s or {}
        region_id = ref.get("region_id")
        work_id = ref.get("work_id", "")
        pdf_page = ref.get("pdf_page")
        src_img = ref.get("image_reference", "")
        prev_text = ((items[idx - 1].get("primary") or items[idx - 1].get("secondary") or {}).get("text", "")) if idx > 0 else ""
        next_text = (
            ((items[idx + 1].get("primary") or items[idx + 1].get("secondary") or {}).get("text", ""))
            if idx + 1 < len(items)
            else ""
        )

        status = item.get("status", "")
        if status == "CROSS_CHECK_INCOMPLETE":
            disagreements.append(
                {
                    "disagreement_id": _next_id(),
                    "item_id": item["item_id"],
                    "region_id": region_id,
                    "work_id": work_id,
                    "pdf_page": pdf_page,
                    "primary_record_ids": p_ids,
                    "secondary_record_ids": s_ids,
                    "primary_engine": (p or {}).get("engine", "paddleocr"),
                    "secondary_engine": None,
                    "primary_text": (p or {}).get("text", ""),
                    "secondary_text": "",
                    "primary_span": {"start": 0, "end": len((p or {}).get("text", "")), "offset_unit": "unicode_codepoint_original"},
                    "secondary_span": {"start": 0, "end": 0, "offset_unit": "unicode_codepoint_original"},
                    "operation": "CROSS_CHECK_INCOMPLETE",
                    "error_category": "CROSS_CHECK_INCOMPLETE",
                    "priority": "MEDIUM",
                    "source_image": src_img,
                    "context_before": prev_text,
                    "context_after": next_text,
                    "status": "PENDING",
                }
            )
            continue

        if status == "MISSING_REGION":
            is_primary_only = p is not None and s is None
            cat = "MISSING_LINE" if is_primary_only and ref.get("bbox") is not None else (
                "EXTRA_LINE" if not is_primary_only and ref.get("bbox") is not None else "MISSING_REGION"
            )
            disagreements.append(
                {
                    "disagreement_id": _next_id(),
                    "item_id": item["item_id"],
                    "region_id": region_id,
                    "work_id": work_id,
                    "pdf_page": pdf_page,
                    "primary_record_ids": p_ids,
                    "secondary_record_ids": s_ids,
                    "primary_engine": (p or {}).get("engine"),
                    "secondary_engine": (s or {}).get("engine"),
                    "primary_text": (p or {}).get("text", ""),
                    "secondary_text": (s or {}).get("text", ""),
                    "primary_span": {"start": 0, "end": len((p or {}).get("text", "")), "offset_unit": "unicode_codepoint_original"},
                    "secondary_span": {"start": 0, "end": len((s or {}).get("text", "")), "offset_unit": "unicode_codepoint_original"},
                    "operation": "MISSING_REGION",
                    "error_category": cat,
                    "priority": "CRITICAL",
                    "source_image": src_img,
                    "context_before": prev_text,
                    "context_after": next_text,
                    "status": "PENDING",
                }
            )
            continue

        if "reading_order_mismatch" in item.get("issue_types", []):
            disagreements.append(
                {
                    "disagreement_id": _next_id(),
                    "item_id": item["item_id"],
                    "region_id": region_id,
                    "work_id": work_id,
                    "pdf_page": pdf_page,
                    "primary_record_ids": p_ids,
                    "secondary_record_ids": s_ids,
                    "primary_engine": (p or {}).get("engine"),
                    "secondary_engine": (s or {}).get("engine"),
                    "primary_text": (p or {}).get("text", ""),
                    "secondary_text": (s or {}).get("text", ""),
                    "primary_span": {"start": 0, "end": len((p or {}).get("text", "")), "offset_unit": "unicode_codepoint_original"},
                    "secondary_span": {"start": 0, "end": len((s or {}).get("text", "")), "offset_unit": "unicode_codepoint_original"},
                    "operation": "READING_ORDER_MISMATCH",
                    "error_category": "READING_ORDER_MISMATCH",
                    "priority": "CRITICAL",
                    "source_image": src_img,
                    "context_before": prev_text,
                    "context_after": next_text,
                    "status": "PENDING",
                }
            )

        if "ambiguous_match" in item.get("issue_types", []):
            disagreements.append(
                {
                    "disagreement_id": _next_id(),
                    "item_id": item["item_id"],
                    "region_id": region_id,
                    "work_id": work_id,
                    "pdf_page": pdf_page,
                    "primary_record_ids": p_ids,
                    "secondary_record_ids": s_ids,
                    "primary_engine": (p or {}).get("engine"),
                    "secondary_engine": (s or {}).get("engine"),
                    "primary_text": (p or {}).get("text", ""),
                    "secondary_text": (s or {}).get("text", ""),
                    "primary_span": {"start": 0, "end": len((p or {}).get("text", "")), "offset_unit": "unicode_codepoint_original"},
                    "secondary_span": {"start": 0, "end": len((s or {}).get("text", "")), "offset_unit": "unicode_codepoint_original"},
                    "operation": "AMBIGUOUS_MATCH",
                    "error_category": "AMBIGUOUS_MATCH",
                    "priority": "MEDIUM",
                    "source_image": src_img,
                    "context_before": prev_text,
                    "context_after": next_text,
                    "status": "PENDING",
                }
            )

        p_conf = (p or {}).get("confidence")
        if p_conf is not None and float(p_conf) < low_confidence_threshold:
            disagreements.append(
                {
                    "disagreement_id": _next_id(),
                    "item_id": item["item_id"],
                    "region_id": region_id,
                    "work_id": work_id,
                    "pdf_page": pdf_page,
                    "primary_record_ids": p_ids,
                    "secondary_record_ids": s_ids,
                    "primary_engine": (p or {}).get("engine"),
                    "secondary_engine": (s or {}).get("engine"),
                    "primary_text": (p or {}).get("text", ""),
                    "secondary_text": (s or {}).get("text", ""),
                    "primary_span": {"start": 0, "end": len((p or {}).get("text", "")), "offset_unit": "unicode_codepoint_original"},
                    "secondary_span": {"start": 0, "end": len((s or {}).get("text", "")), "offset_unit": "unicode_codepoint_original"},
                    "operation": "LOW_CONFIDENCE",
                    "error_category": "LOW_CONFIDENCE",
                    "priority": "HIGH",
                    "source_image": src_img,
                    "context_before": prev_text,
                    "context_after": next_text,
                    "status": "PENDING",
                }
            )

        for op in (item.get("comparison") or {}).get("char_ops", []):
            if op["op"] == "equal":
                continue
            cat, prio = _classify_han_char_op(op)
            disagreements.append(
                {
                    "disagreement_id": _next_id(),
                    "item_id": item["item_id"],
                    "region_id": region_id,
                    "work_id": work_id,
                    "pdf_page": pdf_page,
                    "primary_record_ids": p_ids,
                    "secondary_record_ids": s_ids,
                    "primary_engine": (p or {}).get("engine"),
                    "secondary_engine": (s or {}).get("engine"),
                    "primary_text": op["a"],
                    "secondary_text": op["b"],
                    "primary_span": {
                        "start": op.get("orig_start_a", op["pos_a"]),
                        "end": op.get("orig_end_a", op["pos_a"] + len(op["a"])),
                        "offset_unit": "unicode_codepoint_original",
                    },
                    "secondary_span": {
                        "start": op.get("orig_start_b", op["pos_b"]),
                        "end": op.get("orig_end_b", op["pos_b"] + len(op["b"])),
                        "offset_unit": "unicode_codepoint_original",
                    },
                    "operation": op["op"].upper(),
                    "error_category": cat,
                    "priority": prio,
                    "source_image": src_img,
                    "context_before": prev_text,
                    "context_after": next_text,
                    "status": "PENDING",
                }
            )

    for dup in cross_check_report.get("duplicate_regions", []):
        disagreements.append(
            {
                "disagreement_id": _next_id(),
                "item_id": "duplicate",
                "region_id": dup["region_ids"][0],
                "work_id": "",
                "pdf_page": None,
                "primary_record_ids": dup["record_ids"] if dup["engine"] == "paddleocr" else [],
                "secondary_record_ids": dup["record_ids"] if dup["engine"] != "paddleocr" else [],
                "primary_engine": dup["engine"],
                "secondary_engine": None,
                "primary_text": "",
                "secondary_text": "",
                "primary_span": {"start": 0, "end": 0, "offset_unit": "unicode_codepoint_original"},
                "secondary_span": {"start": 0, "end": 0, "offset_unit": "unicode_codepoint_original"},
                "operation": "DUPLICATE_REGION",
                "error_category": "DUPLICATE_REGION",
                "priority": "MEDIUM",
                "source_image": "",
                "context_before": "",
                "context_after": "",
                "status": "PENDING",
            }
        )
    return disagreements


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
    match_type: str = "1-1"
    primary_record_ids: list[str] = field(default_factory=list)
    secondary_record_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "item_id": self.item_id,
            "source_id": self.source_id,
            "variant": self.variant,
            "match_type": self.match_type,
            "primary_record_ids": self.primary_record_ids or ([self.primary.record_id] if self.primary else []),
            "secondary_record_ids": self.secondary_record_ids or ([self.secondary.record_id] if self.secondary else []),
            "primary": self.primary.to_dict() if self.primary else None,
            "secondary": self.secondary.to_dict() if self.secondary else None,
            "match_method": self.match_method,
            "status": self.status,
            "issue_types": self.issue_types,
            "comparison": self.comparison,
        }


def _aggregate_group_record(records: list[OCRRecord], match_type: str) -> OCRRecord:
    if len(records) == 1:
        return records[0]
    first = records[0]
    joined = "".join(r.text for r in records)
    confs = [r.confidence for r in records if r.confidence is not None]
    min_conf = min(confs) if confs else None
    return OCRRecord(
        record_id="+".join(r.record_id for r in records),
        source_id=first.source_id,
        region_id="+".join(str(r.region_id) for r in records),
        work_id=first.work_id,
        corpus_id=first.corpus_id,
        member_id=first.member_id,
        variant=first.variant,
        pdf_page=first.pdf_page,
        reading_order=first.reading_order,
        engine=first.engine,
        model_version=first.model_version,
        text=joined,
        bbox=None if any(r.bbox is None for r in records) else [r.bbox for r in records],
        confidence=min_conf,
        layout=first.layout,
        image_reference=first.image_reference,
        input_sha256=first.input_sha256,
        original_image_sha256=first.original_image_sha256,
        processed_image_sha256=first.processed_image_sha256,
        status=first.status,
        coordinate_space=first.coordinate_space,
        extra={"grouped_match_type": match_type, "member_record_ids": [r.record_id for r in records]},
    )


def cross_check_records(
    primary_records: list[OCRRecord],
    secondary_records: list[OCRRecord],
    *,
    variant: str,
    iou_threshold: float = 0.3,
    use_dp_line_match: bool = False,
    dp_weights: dict[str, float] | None = None,
    max_group_size: int = 3,
    low_confidence_threshold: float = 0.60,
    punctuation_equivalents: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Match primary & secondary OCR records cleanly by work/source/page/region without confidence picking."""
    t0 = time.perf_counter()
    compare_fn = (
        (lambda a, b: compare_han_texts(a, b, punctuation_equivalents=punctuation_equivalents))
        if variant == "han"
        else compare_viet_texts
    )

    usable_sec = [
        r for r in secondary_records if r.status not in {"FAILED", "UNPROCESSED", "API_NOT_CONFIGURED"}
    ]
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
        report = {
            "status": "CROSS_CHECK_INCOMPLETE",
            "variant": variant,
            "items": [it.to_dict() for it in items],
            "duplicate_regions": detect_duplicate_regions(primary_records),
            "reading_order_warnings": [],
            "processing_seconds": round(time.perf_counter() - t0, 4),
            "summary": {"total": len(items), "agreed_unverified": 0, "disagreements": 0, "incomplete": len(items)},
        }
        report["disagreements"] = extract_han_disagreements(report, low_confidence_threshold=low_confidence_threshold) if variant == "han" else []
        return report

    def _is_page_level(recs: list[OCRRecord]) -> bool:
        return len(recs) == 1 and (recs[0].bbox is None or "\n" in recs[0].text)

    if not use_dp_line_match and len(primary_records) != len(usable_sec) and (
        _is_page_level(primary_records) or _is_page_level(usable_sec)
    ):
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
            primary_record_ids=[r.record_id for r in primary_records],
            secondary_record_ids=[r.record_id for r in usable_sec],
        )
        report = {
            "status": "NEEDS_REVIEW",
            "variant": variant,
            "items": [item.to_dict()],
            "duplicate_regions": detect_duplicate_regions(primary_records) + detect_duplicate_regions(usable_sec),
            "reading_order_warnings": [],
            "processing_seconds": round(time.perf_counter() - t0, 4),
            "summary": {"total": 1, "agreed_unverified": 0, "disagreements": 1, "incomplete": 0},
        }
        report["disagreements"] = extract_han_disagreements(report, low_confidence_threshold=low_confidence_threshold) if variant == "han" else []
        return report

    items: list[CrossCheckItem] = []

    if use_dp_line_match:
        # Group strictly by hierarchical (corpus_id, work_id, source_id, pdf_page) scope!
        scopes: list[tuple[str, str, str, int | None]] = []
        p_by_scope: dict[tuple[str, str, str, int | None], list[OCRRecord]] = {}
        s_by_scope: dict[tuple[str, str, str, int | None], list[OCRRecord]] = {}
        for r in primary_records:
            k = scope_key(r)
            if k not in p_by_scope:
                scopes.append(k)
            p_by_scope.setdefault(k, []).append(r)
        for r in usable_sec:
            k = scope_key(r)
            if k not in p_by_scope and k not in s_by_scope:
                scopes.append(k)
            s_by_scope.setdefault(k, []).append(r)

        weights = dp_weights or {}
        idx_counter = 0
        for sc in scopes:
            p_list = p_by_scope.get(sc, [])
            s_list = s_by_scope.get(sc, [])
            dp_groups = match_lines_dp(
                p_list,
                s_list,
                alpha=float(weights.get("alpha", 0.65)),
                beta=float(weights.get("beta", 0.15)),
                gamma=float(weights.get("gamma", 0.10)),
                delta=float(weights.get("delta", 0.10)),
                max_group_size=max_group_size,
            )
            for grp in dp_groups:
                idx_counter += 1
                if grp.match_type == "primary_only":
                    p_rec = p_list[grp.primary_indices[0]]
                    items.append(
                        CrossCheckItem(
                            item_id=f"xc_{idx_counter:04d}",
                            source_id=p_rec.source_id,
                            variant=variant,
                            primary=p_rec,
                            secondary=None,
                            match_method=grp.match_method,
                            status="MISSING_REGION",
                            issue_types=["missing_region"],
                            comparison={},
                            match_type="primary_only",
                            primary_record_ids=[p_rec.record_id],
                            secondary_record_ids=[],
                        )
                    )
                    continue
                if grp.match_type == "secondary_only":
                    s_rec = s_list[grp.secondary_indices[0]]
                    items.append(
                        CrossCheckItem(
                            item_id=f"xc_{idx_counter:04d}",
                            source_id=s_rec.source_id,
                            variant=variant,
                            primary=None,
                            secondary=s_rec,
                            match_method=grp.match_method,
                            status="MISSING_REGION",
                            issue_types=["missing_region"],
                            comparison={},
                            match_type="secondary_only",
                            primary_record_ids=[],
                            secondary_record_ids=[s_rec.record_id],
                        )
                    )
                    continue

                p_grp = [p_list[i] for i in grp.primary_indices]
                s_grp = [s_list[i] for i in grp.secondary_indices]
                p_agg = _aggregate_group_record(p_grp, grp.match_type)
                s_agg = _aggregate_group_record(s_grp, grp.match_type)
                comp = compare_fn(p_agg.text, s_agg.text)
                issues = list(comp["issue_types"])
                if grp.ambiguous:
                    issues.append("ambiguous_match")
                status = "AGREED_UNVERIFIED" if not issues else "DISAGREEMENT"
                items.append(
                    CrossCheckItem(
                        item_id=f"xc_{idx_counter:04d}",
                        source_id=p_agg.source_id,
                        variant=variant,
                        primary=p_agg,
                        secondary=s_agg,
                        match_method=grp.match_method,
                        status=status,
                        issue_types=sorted(set(issues)),
                        comparison=comp,
                        match_type=grp.match_type,
                        primary_record_ids=[r.record_id for r in p_grp],
                        secondary_record_ids=[r.record_id for r in s_grp],
                    )
                )
    else:
        matched_sec: set[int] = set()
        for idx, p in enumerate(primary_records, 1):
            best_s_idx = None
            method = ""

            # 1) Bbox IoU + overlap/center matching strictly within same work/source scope
            if p.bbox is not None and any(s.bbox is not None for s in usable_sec):
                best_score = 0.0
                for s_idx, s in enumerate(usable_sec):
                    if s_idx in matched_sec or scope_key(s) != scope_key(p):
                        continue
                    iou = bbox_iou(p.bbox, s.bbox)
                    overlap = bbox_overlap_ratio(p.bbox, s.bbox)
                    cdist = bbox_center_distance(p.bbox, s.bbox)
                    score = max(iou, 0.7 * overlap) - (0.05 * cdist if cdist is not None else 0.0)
                    if (iou >= iou_threshold or overlap >= 0.65) and score > best_score:
                        best_score = score
                        best_s_idx = s_idx
                        method = "bbox_iou"

            # 2) Region ID + scope fallback
            if best_s_idx is None:
                for s_idx, s in enumerate(usable_sec):
                    if s_idx not in matched_sec and scope_key(s) == scope_key(p) and s.region_id == p.region_id:
                        best_s_idx = s_idx
                        method = "source_and_region_id"
                        break

            # 3) Reading order fallback when counts match in scope
            if best_s_idx is None and len(primary_records) == len(usable_sec):
                for s_idx, s in enumerate(usable_sec):
                    if s_idx not in matched_sec and scope_key(s) == scope_key(p) and s.reading_order == p.reading_order:
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
                        match_type="primary_only",
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
                        match_type="secondary_only",
                    )
                )

    dict_items = [it.to_dict() for it in items]
    ro_warnings = validate_reading_order(dict_items, strict_index_equality=not use_dp_line_match)
    for w in ro_warnings:
        for it in dict_items:
            if it["item_id"] == w["item_id"] and "reading_order_mismatch" not in it["issue_types"]:
                it["issue_types"] = sorted(set(it["issue_types"]) | {"reading_order_mismatch"})
                if it["status"] == "AGREED_UNVERIFIED":
                    it["status"] = "DISAGREEMENT"

    agreed_count = sum(1 for it in dict_items if it["status"] == "AGREED_UNVERIFIED")
    disagree_count = len(dict_items) - agreed_count
    overall = "COMPLETE" if not any(it["status"] == "MISSING_REGION" for it in dict_items) else "NEEDS_REVIEW"
    report = {
        "status": overall,
        "variant": variant,
        "items": dict_items,
        "duplicate_regions": detect_duplicate_regions(primary_records) + detect_duplicate_regions(usable_sec),
        "reading_order_warnings": ro_warnings,
        "processing_seconds": round(time.perf_counter() - t0, 4),
        "summary": {
            "total": len(dict_items),
            "agreed_unverified": agreed_count,
            "disagreements": disagree_count,
            "incomplete": 0,
        },
    }
    report["disagreements"] = (
        extract_han_disagreements(report, low_confidence_threshold=low_confidence_threshold) if variant == "han" else []
    )
    return report
