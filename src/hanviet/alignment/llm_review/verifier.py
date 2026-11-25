"""Post-alignment LLM verification running strictly after draft.json and before manual review."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from hanviet.common.io import read_json, write_json
from hanviet.common.llm_client import LLMClient, LLMConfig
from hanviet.common.paths import resolve_paths

ALIGNMENT_REPAIR_SCHEMA = {
    "type": "object",
    "required": ["work", "fingerprint", "findings", "proposals"],
    "properties": {
        "work": {"type": "string"},
        "fingerprint": {"type": "string"},
        "findings": {"type": "array"},
        "proposals": {"type": "array"},
    },
}


def load_alignment_schema(project_root: Path | None = None) -> dict[str, Any]:
    paths = resolve_paths(user_root=project_root)
    schema_path = paths.schemas_root / "alignment_repair.schema.json"
    return read_json(schema_path) if schema_path.is_file() else ALIGNMENT_REPAIR_SCHEMA


def load_alignment_prompts(project_root: Path | None = None) -> str:
    paths = resolve_paths(user_root=project_root)
    verify_md = (paths.prompts_root / "alignment" / "alignment_verification.md").read_text(encoding="utf-8")
    repair_md = (paths.prompts_root / "alignment" / "alignment_repair.md").read_text(encoding="utf-8")
    return verify_md + "\n\n---\n\n" + repair_md


def run_llm_alignment_verification(
    draft: dict[str, Any],
    *,
    llm_config: LLMConfig,
    client: LLMClient | None = None,
    stage_dir: Path | None = None,
    project_root: Path | None = None,
) -> dict[str, Any]:
    """Verify draft alignment links and unmatched segments without altering protected aligners.

    Snapshots `before/` state and writes `requests/`, `responses/` in stage 06 directory when supplied.
    """
    if client is None:
        client = LLMClient(llm_config, project_root=project_root)
    schema = load_alignment_schema(project_root=project_root)
    system_prompt = load_alignment_prompts(project_root=project_root)

    if stage_dir is not None:
        stage_dir = Path(stage_dir)
        for sub in ("before", "requests", "responses", "patches", "manual_review", "after"):
            (stage_dir / sub).mkdir(parents=True, exist_ok=True)
        write_json(
            stage_dir / "before" / "draft_snapshot.json",
            {
                "work": draft["work"],
                "fingerprint": draft["fingerprint"],
                "links": draft.get("links", {}),
                "unmatched": draft.get("unmatched", {}),
                "status": draft.get("status", {}),
            },
        )

    payload = {
        "work": draft["work"],
        "fingerprint": draft["fingerprint"],
        "settings": draft.get("settings", {}),
        "missing_versions_in_source": [k for k, v in draft.get("units", {}).items() if not v],
        "units": {
            k: [{"id": u["id"], "text": u["text"]} for u in members]
            for k, members in draft.get("units", {}).items()
        },
        "links": draft.get("links", {}),
        "unmatched": draft.get("unmatched", {}),
        "lab_diagnostics": draft.get("lab_diagnostics", []),
    }

    if stage_dir is not None:
        client.export_manual_request(
            stage_dir / "requests" / "verification_request.json",
            system_prompt=system_prompt,
            user_payload=payload,
            schema=schema,
            schema_id="alignment_verification_repair",
        )

    result = client.request_structured(
        system_prompt=system_prompt,
        user_payload=payload,
        schema=schema,
        schema_id="alignment_verification_repair",
    )

    report: dict[str, Any] = {
        "work": draft["work"],
        "fingerprint": draft["fingerprint"],
        "status": result.status,
        "input_hash": result.input_hash,
        "prompt_version": result.prompt_version,
        "cache_hit": result.cache_hit,
        "latency_ms": result.latency_ms,
        "usage": result.usage,
        "error": result.error,
        "response": result.parsed_json if result.status == "OK" else None,
    }
    if stage_dir is not None:
        write_json(stage_dir / "responses" / "verification_response.json", report)
    return report
