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


def compute_han_ocr_evaluation(
    cross_check_report: dict[str, Any],
    manual_result: dict[str, Any] | None = None,
    *,
    gold_references: list[str] | None = None,
    gold_disagreement_flags: list[bool] | None = None,
    processing_seconds: float | None = None,
    manual_review_seconds: float | None = None,
) -> dict[str, Any]:
    """Comprehensive Task 17 evaluation separating CER vs gold, agreement rate, coverage, detection P/R, and manual fixing."""
    items = cross_check_report.get("items", [])
    summary = cross_check_report.get("summary", {})
    strict_agreements: list[float] = []
    content_agreements: list[float] = []
    both_empty_count = 0

    for item in items:
        p_txt = (item.get("primary") or {}).get("text", "")
        s_txt = (item.get("secondary") or {}).get("text", "")
        if item.get("primary") and item.get("secondary") and not p_txt and not s_txt:
            both_empty_count += 1
        comp = item.get("comparison") or {}
        if "agreement_rate" in comp:
            strict_agreements.append(float(comp["agreement_rate"]))
            cc = comp.get("content_comparison") or {}
            if "agreement_rate" in cc:
                content_agreements.append(float(cc["agreement_rate"]))

    pages = {(it.get("primary") or it.get("secondary") or {}).get("pdf_page") for it in items}
    pages.discard(None)
    p_count = sum(1 for it in items if it.get("primary") is not None)
    s_count = sum(1 for it in items if it.get("secondary") is not None)

    recs = (manual_result or {}).get("records", [])
    decision_counts: dict[str, int] = {}
    for r in recs:
        dec = str(r.get("decision") or "DEFER")
        decision_counts[dec] = decision_counts.get(dec, 0) + 1

    mask_count = sum((r.get("final_text") or "").count("[MASK]") for r in recs)
    reviewed_count = (manual_result or {}).get("reviewed_count", 0)
    total_items = len(items)

    # Gold CER/WER (micro & macro) + false agreement rate (primary == secondary != gold)
    cer_block: dict[str, Any] = {"status": "CER_NOT_AVAILABLE", "micro_cer": None, "macro_cer": None}
    false_agreement: dict[str, Any] = {"gold_available": False, "false_agreement_rate": None, "count": None}
    detection_metrics: dict[str, Any] = {"unit": "region", "gold_available": False, "precision": None, "recall": None}

    if gold_references is not None:
        if len(gold_references) != total_items:
            raise ValueError("gold_references must match cross_check_report items length.")
        p_preds = [(it.get("primary") or {}).get("text", "") for it in items]
        s_preds = [(it.get("secondary") or {}).get("text", "") for it in items]
        p_micro = compute_cer_wer(p_preds, gold_references)
        s_micro = compute_cer_wer(s_preds, gold_references)

        def _macro(preds: list[str], refs: list[str]) -> float | None:
            per = []
            for pred, ref in zip(preds, refs):
                if ref:
                    edits = sum(1 for o in levenshtein_align(list(ref), list(pred)) if o["op"] != "equal")
                    per.append(edits / len(ref))
            return round(sum(per) / len(per), 6) if per else None

        corr_cer = None
        if manual_result is not None and len(recs) == total_items:
            c_preds = [r.get("final_text") or "" for r in recs]
            corr_micro = compute_cer_wer(c_preds, gold_references)
            corr_cer = {"micro_cer": corr_micro["cer"], "macro_cer": _macro(c_preds, gold_references)}

        cer_block = {
            "status": "COMPUTED_AGAINST_GOLD",
            "primary_micro_cer": p_micro["cer"],
            "primary_macro_cer": _macro(p_preds, gold_references),
            "secondary_micro_cer": s_micro["cer"],
            "secondary_macro_cer": _macro(s_preds, gold_references),
            "corrected": corr_cer,
        }

        agreed_items = [
            (it, g) for it, g in zip(items, gold_references) if it.get("status") == "AGREED_UNVERIFIED"
        ]
        if agreed_items:
            false_cnt = sum(1 for it, g in agreed_items if (it.get("primary") or {}).get("text", "") != g)
            false_agreement = {
                "gold_available": True,
                "agreed_checked": len(agreed_items),
                "count": false_cnt,
                "false_agreement_rate": round(false_cnt / len(agreed_items), 6),
            }

        # Region-level error detection P/R using explicit gold error flags if supplied, or gold != primary
        actual_errors = (
            gold_disagreement_flags
            if gold_disagreement_flags is not None
            else [((it.get("primary") or {}).get("text", "") != g or (it.get("secondary") or {}).get("text", "") != g) for it, g in zip(items, gold_references)]
        )
        flagged = [it.get("status") != "AGREED_UNVERIFIED" for it in items]
        tp = sum(1 for fl, ac in zip(flagged, actual_errors) if fl and ac)
        fp = sum(1 for fl, ac in zip(flagged, actual_errors) if fl and not ac)
        fn = sum(1 for fl, ac in zip(flagged, actual_errors) if not fl and ac)
        prec = tp / (tp + fp) if (tp + fp) else 0.0
        rec = tp / (tp + fn) if (tp + fn) else 0.0
        detection_metrics = {
            "unit": "region",
            "gold_available": True,
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "precision": round(prec, 6),
            "recall": round(rec, 6),
        }

    return {
        "cross_check_status": cross_check_report.get("status"),
        "agreement": {
            "note": "Agreement rate measures inter-engine consistency, NOT OCR accuracy.",
            "strict_mean": round(sum(strict_agreements) / len(strict_agreements), 6) if strict_agreements else None,
            "content_mean": round(sum(content_agreements) / len(content_agreements), 6) if content_agreements else None,
            "both_empty_regions": both_empty_count,
        },
        "coverage": {
            "pages_selected": len(pages),
            "total_items": total_items,
            "primary_items": p_count,
            "secondary_items": s_count,
            "matched_agreed_unverified": summary.get("agreed_unverified", 0),
            "disagreements": summary.get("disagreements", 0),
            "incomplete_items": summary.get("incomplete", 0),
            "missing_regions": sum(1 for it in items if it.get("status") == "MISSING_REGION"),
        },
        "cer": cer_block,
        "false_agreement": false_agreement,
        "error_detection": detection_metrics,
        "manual_fixing": {
            "available": manual_result is not None,
            "review_status": (manual_result or {}).get("review_status", "PENDING"),
            "reviewed_count": reviewed_count,
            "deferred_count": (manual_result or {}).get("deferred_count", total_items),
            "completion_rate": round(reviewed_count / total_items, 6) if total_items else 0.0,
            "decision_counts": decision_counts,
            "mask_count": mask_count,
            "manual_review_seconds": manual_review_seconds,
        },
        "processing_seconds": processing_seconds if processing_seconds is not None else cross_check_report.get("processing_seconds"),
    }


def experiment_matrix_template() -> list[dict[str, Any]]:
    """Return structured H01-H06 experiment matrix without fabricated metrics."""
    return [
        {"experiment_id": "H01", "method": "PaddleOCR on original image", "metrics": ["CER_micro", "CER_macro", "coverage"], "status": "NOT_RUN"},
        {"experiment_id": "H02", "method": "PaddleOCR with Bac Su / Han preprocessing", "metrics": ["CER_micro", "CER_macro", "coverage"], "status": "NOT_RUN"},
        {"experiment_id": "H03", "method": "CLC OCR on original image", "metrics": ["CER_micro", "CER_macro", "coverage"], "status": "NOT_RUN"},
        {"experiment_id": "H04", "method": "CLC OCR with preprocessing (if service supports)", "metrics": ["CER_micro", "CER_macro"], "status": "NOT_RUN"},
        {"experiment_id": "H05", "method": "PaddleOCR + CLC OCR cross-check", "metrics": ["strict_agreement", "content_agreement", "detection_precision", "detection_recall", "false_agreement_rate", "unmatched_regions"], "status": "NOT_RUN"},
        {"experiment_id": "H06", "method": "Cross-check-assisted manual fixing", "metrics": ["corrected_CER", "manual_time_sec", "completion_rate", "mask_count"], "status": "NOT_RUN"},
    ]


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
