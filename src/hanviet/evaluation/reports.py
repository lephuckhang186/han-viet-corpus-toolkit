"""Write machine-readable and Markdown stage evaluation reports."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from hanviet.common.io import atomic_bytes, write_json


def export_evaluation_report(
    output_dir: Path,
    *,
    report_name: str,
    metrics: dict[str, Any],
) -> tuple[Path, Path]:
    """Write `<report_name>.json` and `<report_name>.md` into 07_danh_gia/."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    json_path = out / f"{report_name}.json"
    md_path = out / f"{report_name}.md"
    write_json(json_path, metrics)

    lines = [f"# Evaluation Report: {report_name}", ""]
    for key, value in metrics.items():
        if isinstance(value, dict):
            lines.append(f"## {key}")
            for sub_k, sub_v in value.items():
                lines.append(f"- **{sub_k}**: `{sub_v}`")
            lines.append("")
        else:
            lines.append(f"- **{key}**: `{value}`")
    atomic_bytes(md_path, ("\n".join(lines) + "\n").encode("utf-8"))
    return json_path, md_path
