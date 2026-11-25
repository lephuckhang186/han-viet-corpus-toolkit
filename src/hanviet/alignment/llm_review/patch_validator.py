"""Deterministic code validator for LLM alignment repair proposals."""
from __future__ import annotations

from typing import Any

from hanviet.alignment.validation.validators import validate_links, verify_identity

ALLOWED_OPERATIONS = {
    "KEEP",
    "MERGE",
    "SPLIT",
    "RELINK",
    "ADD_LINK",
    "REMOVE_LINK",
    "FLAG_OCR",
    "FLAG_CLEANING",
    "REQUEST_REVIEW",
}


def validate_alignment_proposals(
    draft: dict[str, Any],
    llm_response: dict[str, Any],
    *,
    existing_review: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate repair proposals against work ID, fingerprint, segment existence, order, and approved review locks."""
    verify_identity(llm_response, draft["work"], draft["fingerprint"])

    if existing_review is not None and existing_review.get("approved") is True:
        return {
            "valid_proposals": [],
            "rejected_proposals": [
                {
                    "proposal": prop,
                    "validation_errors": ["Existing review.json has approved=true; LLM cannot mutate approved reviews."],
                }
                for prop in llm_response.get("proposals", [])
            ],
            "locked_by_approved_review": True,
        }

    units = draft["units"]
    han_lookup = {u["id"]: idx for idx, u in enumerate(units.get("han", []))}
    target_lookups = {
        kind: {u["id"]: idx for idx, u in enumerate(units.get(kind, []))}
        for kind in ("am", "nghia", "tho")
    }

    valid: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    seen_han_by_kind: dict[str, set[str]] = {"am": set(), "nghia": set(), "tho": set()}

    for prop in llm_response.get("proposals", []):
        errors: list[str] = []
        op = prop.get("operation")
        kind = prop.get("target_kind")
        if op not in ALLOWED_OPERATIONS:
            errors.append(f"Unsupported operation: {op!r}")
        if kind not in {"am", "nghia", "tho"}:
            errors.append(f"Invalid target_kind: {kind!r}")
            rejected.append({"proposal": prop, "validation_errors": errors})
            continue

        if any(k in prop for k in ("new_text", "fabricated_translation", "edited_source_text", "approved")):
            errors.append("Proposal attempts disallowed mutation (source edit, translation fabrication, or auto-approve).")

        han_ids = prop.get("han_ids", [])
        target_ids = prop.get("target_ids", [])
        if any(hid not in han_lookup for hid in han_ids):
            errors.append("han_ids contains non-existent segment ID")
        if any(tid not in target_lookups[kind] for tid in target_ids):
            errors.append(f"target_ids contains non-existent {kind} ID")

        # Validate replacement_links structure & contiguity via protected validate_links
        rep_links = prop.get("replacement_links")
        if op in {"MERGE", "SPLIT", "RELINK", "ADD_LINK"}:
            candidate_links = rep_links if rep_links is not None else [{"han_ids": han_ids, "target_ids": target_ids}]
            converted = [{"han_ids": l.get("han_ids", []), f"{kind}_ids": l.get("target_ids", [])} for l in candidate_links]
            try:
                validate_links(converted, units["han"], units[kind], kind)
            except ValueError as exc:
                errors.append(f"Invalid link structure/order/contiguity: {exc}")

            for link in converted:
                if any(hid in seen_han_by_kind[kind] for hid in link["han_ids"]):
                    errors.append("Overlapping han_ids across repair proposals for same target kind")
                    break

        if errors:
            rejected.append({"proposal": prop, "validation_errors": errors})
        else:
            if rep_links is not None:
                for l in rep_links:
                    seen_han_by_kind[kind].update(l.get("han_ids", []))
            elif op in {"MERGE", "SPLIT", "RELINK", "ADD_LINK"}:
                seen_han_by_kind[kind].update(han_ids)
            valid.append(prop)

    return {
        "valid_proposals": valid,
        "rejected_proposals": rejected,
        "locked_by_approved_review": False,
    }
