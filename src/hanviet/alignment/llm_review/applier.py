"""Apply human-approved LLM alignment repair patches safely without auto-approving."""
from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

from hanviet.alignment.validation.validators import make_rows, unmatched_ids, validate_links, verify_identity
from hanviet.common.io import write_json


def apply_approved_alignment_repairs(
    draft: dict[str, Any],
    validated: dict[str, Any],
    human_approvals: dict[str, str],  # proposal_id -> "APPROVE" | "REJECT" | "DEFER"
    *,
    existing_review: dict[str, Any] | None = None,
    stage_dir: Path | None = None,
) -> dict[str, Any]:
    """Produce a candidate review structure (`approved: false`) applying only user-approved patches."""
    if existing_review is not None and existing_review.get("approved") is True:
        raise ValueError("Refusing to overwrite approved review.json.")

    units = draft["units"]
    links = {kind: copy.deepcopy(draft["links"].get(kind, [])) for kind in ("am", "nghia", "tho")}
    applied_log: list[dict[str, Any]] = []
    stage_warnings: list[dict[str, Any]] = []

    for prop in validated.get("valid_proposals", []):
        pid = prop["proposal_id"]
        verdict = (human_approvals.get(pid) or "DEFER").strip().upper()
        if verdict != "APPROVE":
            applied_log.append({"proposal_id": pid, "verdict": verdict, "applied": False})
            continue

        op = prop["operation"]
        kind = prop["target_kind"]
        if op in {"FLAG_OCR", "FLAG_CLEANING", "REQUEST_REVIEW"}:
            stage_warnings.append(
                {
                    "proposal_id": pid,
                    "operation": op,
                    "requires_earlier_stage": prop.get("requires_earlier_stage"),
                    "reason": prop.get("reason"),
                }
            )
            applied_log.append({"proposal_id": pid, "verdict": "APPROVE", "applied": "warning_recorded"})
            continue

        if op == "KEEP":
            applied_log.append({"proposal_id": pid, "verdict": "APPROVE", "applied": "kept"})
            continue

        han_set = set(prop.get("han_ids", []))
        target_set = set(prop.get("target_ids", []))
        remaining = [
            link
            for link in links[kind]
            if not (set(link["han_ids"]) & han_set or set(link[f"{kind}_ids"]) & target_set)
        ]

        if op != "REMOVE_LINK":
            rep_links = prop.get("replacement_links") or [{"han_ids": prop["han_ids"], "target_ids": prop["target_ids"]}]
            for rlink in rep_links:
                remaining.append({"han_ids": list(rlink["han_ids"]), f"{kind}_ids": list(rlink["target_ids"])})

        han_pos = {u["id"]: i for i, u in enumerate(units["han"])}
        remaining.sort(key=lambda l: han_pos[l["han_ids"][0]])
        validate_links(remaining, units["han"], units[kind], kind)
        links[kind] = remaining
        applied_log.append({"proposal_id": pid, "verdict": "APPROVE", "applied": True, "operation": op})

    missing = unmatched_ids(units, links)
    rows = make_rows(units, links)
    candidate_review = {
        "work": draft["work"],
        "fingerprint": draft["fingerprint"],
        "approved": False,  # Human must explicitly confirm final review before export.
        "links": links,
        "skipped": {uid: "" for ids in missing.values() for uid in ids},
    }
    verify_identity(candidate_review, draft["work"], draft["fingerprint"])

    result = {
        "candidate_review": candidate_review,
        "rows": rows,
        "unmatched": missing,
        "applied_log": applied_log,
        "stage_warnings": stage_warnings,
    }
    if stage_dir is not None:
        stage_dir = Path(stage_dir)
        write_json(stage_dir / "patches" / "validated_patches.json", validated)
        write_json(stage_dir / "manual_review" / "approval_decisions.json", applied_log)
        write_json(stage_dir / "after" / "review_candidate.json", candidate_review)
    return result
