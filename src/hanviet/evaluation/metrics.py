"""Honest corpus evaluation metrics distinguishing model disagreement, LLM predictions, and human-confirmed ground truth."""
from __future__ import annotations

from typing import Any

from hanviet.extraction.cross_check.aligner import levenshtein_align


def compute_cer_wer(
    predictions: list[str],
    gold_references: list[str],
) -> dict[str, Any]:
    """Compute CER and WER ONLY against an explicit human-verified gold reference dataset."""
    if len(predictions) != len(gold_references):
        raise ValueError("predictions and gold_references must have identical lengths.")
    if not gold_references:
        return {"reference_available": False, "cer": None, "wer": None}

    total_chars = 0
    char_edits = 0
    total_words = 0
    word_edits = 0
    for pred, ref in zip(predictions, gold_references):
        c_ops = levenshtein_align(list(ref), list(pred))
        char_edits += sum(1 for o in c_ops if o["op"] != "equal")
        total_chars += len(ref)

        ref_w, pred_w = ref.split(), pred.split()
        w_ops = levenshtein_align(ref_w, pred_w)
        word_edits += sum(1 for o in w_ops if o["op"] != "equal")
        total_words += len(ref_w)

    return {
        "reference_available": True,
        "cer": round(char_edits / total_chars, 6) if total_chars else None,
        "wer": round(word_edits / total_words, 6) if total_words else None,
        "char_edits": char_edits,
        "reference_chars": total_chars,
        "word_edits": word_edits,
        "reference_words": total_words,
    }


def compute_alignment_eval(
    predicted_pairs: list[tuple[tuple[str, ...], tuple[str, ...]]],
    gold_pairs: list[tuple[tuple[str, ...], tuple[str, ...]]],
) -> dict[str, Any]:
    """Compute strict exact-span precision, recall, and F1 ONLY against an explicit gold alignment set."""
    if not gold_pairs:
        return {"gold_available": False, "precision": None, "recall": None, "f1": None}
    pred_set = set(predicted_pairs)
    gold_set = set(gold_pairs)
    tp = len(pred_set & gold_set)
    prec = tp / len(pred_set) if pred_set else 0.0
    rec = tp / len(gold_set) if gold_set else 0.0
    f1 = (2 * prec * rec / (prec + rec)) if (prec + rec) else 0.0
    return {
        "gold_available": True,
        "true_positives": tp,
        "predicted_count": len(pred_set),
        "gold_count": len(gold_set),
        "precision": round(prec, 6),
        "recall": round(rec, 6),
        "f1": round(f1, 6),
    }


def summarize_ocr_cross_check(
    cross_check_report: dict[str, Any],
    manual_result: dict[str, Any] | None = None,
    *,
    gold_references: list[str] | None = None,
    processing_seconds: float | None = None,
) -> dict[str, Any]:
    """Summarize OCR Dual-Engine statistics without conflating agreement with verified accuracy."""
    summary = cross_check_report.get("summary", {})
    stats: dict[str, Any] = {
        "cross_check_status": cross_check_report.get("status"),
        "total_regions": summary.get("total", len(cross_check_report.get("items", []))),
        "model_agreed_unverified": summary.get("agreed_unverified", 0),
        "model_disagreements": summary.get("disagreements", 0),
        "incomplete_cross_check_regions": summary.get("incomplete", 0),
        "human_confirmed_errors": None,
        "human_manually_fixed": None,
        "human_deferred": None,
        "processing_seconds": processing_seconds,
    }
    if manual_result is not None:
        recs = manual_result.get("records", [])
        stats["human_confirmed_errors"] = sum(
            1 for r in recs if r.get("decision") in {"MANUAL_EDIT", "INSERT_MASK", "FIX_READING_ORDER"}
        )
        stats["human_manually_fixed"] = manual_result.get("reviewed_count", 0)
        stats["human_deferred"] = manual_result.get("deferred_count", 0)
        if gold_references is not None:
            preds = [r.get("final_text") or "" for r in recs]
            stats["gold_eval"] = compute_cer_wer(preds, gold_references)
    return stats


def summarize_cleaning_stage(
    records: list[dict[str, Any]],
    llm_report: dict[str, Any] | None = None,
    approvals_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Summarize rule-based warnings vs LLM predicted proposals vs human approvals."""
    return {
        "total_lines": len(records),
        "rule_based_modified_lines": sum(1 for r in records if r.get("raw") != r.get("clean")),
        "rule_based_flagged_lines": sum(1 for r in records if r.get("reasons")),
        "llm_status": llm_report.get("status") if llm_report else "LLM_NOT_RUN",
        "llm_predicted_proposals": len(llm_report.get("proposals", [])) if llm_report else 0,
        "human_approved": (approvals_summary or {}).get("approved", 0),
        "human_edited": (approvals_summary or {}).get("edited", 0),
        "human_rejected": (approvals_summary or {}).get("rejected", 0),
        "human_deferred": (approvals_summary or {}).get("deferred", 0),
    }


def summarize_alignment_review(
    draft: dict[str, Any],
    llm_verification_report: dict[str, Any] | None = None,
    post_apply_result: dict[str, Any] | None = None,
    *,
    api_cost_usd: float | None = None,
) -> dict[str, Any]:
    """Summarize before/after alignment metrics and LLM verification outcomes."""
    units = draft.get("units", {})
    before_unmatched = draft.get("unmatched", {})
    before_valid = len(draft.get("rows", []))

    resp = (llm_verification_report or {}).get("response") or {}
    findings = resp.get("findings", [])
    proposals = resp.get("proposals", [])

    after_valid = len(post_apply_result["rows"]) if post_apply_result else before_valid
    after_unmatched = post_apply_result["unmatched"] if post_apply_result else before_unmatched
    applied_log = post_apply_result.get("applied_log", []) if post_apply_result else []

    return {
        "han_units": len(units.get("han", [])),
        "am_units": len(units.get("am", [])),
        "nghia_units": len(units.get("nghia", [])),
        "tho_units": len(units.get("tho", [])),
        "before_llm": {
            "aligned_rows": before_valid,
            "unmatched_counts": {k: len(v) for k, v in before_unmatched.items()},
        },
        "llm_verification": {
            "status": (llm_verification_report or {}).get("status", "LLM_NOT_RUN"),
            "predicted_findings": len(findings),
            "predicted_formal_errors": sum(1 for f in findings if f.get("formal_error") != "NONE"),
            "predicted_proposals": len(proposals),
            "human_approved_repairs": sum(1 for l in applied_log if l.get("verdict") == "APPROVE"),
            "human_rejected_repairs": sum(1 for l in applied_log if l.get("verdict") == "REJECT"),
            "latency_ms": (llm_verification_report or {}).get("latency_ms"),
            "usage": (llm_verification_report or {}).get("usage", {}),
            "api_cost_usd": api_cost_usd,
        },
        "after_llm_candidate": {
            "aligned_rows": after_valid,
            "unmatched_counts": {k: len(v) for k, v in after_unmatched.items()},
        },
    }
