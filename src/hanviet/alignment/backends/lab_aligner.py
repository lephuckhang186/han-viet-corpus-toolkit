"""Protected adapter for the SN-QN Levenshtein Lab script."""
from __future__ import annotations

import csv
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from urllib.request import urlopen

LAB_REVISION = "57d4ff99d410ece36914f4d046450ba3be36232a"
LAB_SCRIPT_URL = (
    f"https://raw.githubusercontent.com/VongHaiYen11/SN-QN-alignment/{LAB_REVISION}/align_texts.py"
)
LAB_SCRIPT_SHA256 = "43dad2b97b4b75c3caed3ae9d367e3b6b20114734d3a45ff3b6f462253e97c3d"


def lab_script(path):
    path = Path(path)
    if not path.is_file():
        with urlopen(LAB_SCRIPT_URL, timeout=20) as response:
            code = response.read()
        if hashlib.sha256(code).hexdigest() != LAB_SCRIPT_SHA256:
            raise ValueError("Hash của code Lab tải về không khớp phiên bản đã chốt.")
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as stream:
            stream.write(code)
    if hashlib.sha256(path.read_bytes()).hexdigest() != LAB_SCRIPT_SHA256:
        raise ValueError(f"Code Lab đã thay đổi hoặc không đúng phiên bản: {path}")
    return path.resolve()


def run_lab(script_path, dictionaries, folder, pairs):
    """Run the original CLI. Return the Lab's proposed changes by pair ID."""
    import yaml

    script = lab_script(script_path)
    folder = Path(folder).resolve()
    folder.mkdir(parents=True, exist_ok=True)
    input_file = folder / "input.csv"
    config_file = folder / "config.yaml"
    result_file = folder / "lab.tsv"
    with input_file.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["ID", "HanNom", "DichAm"])
        writer.writeheader()
        writer.writerows(pairs)
    config = {
        "dataset": {
            "name": folder.parent.name,
            "input_file": str(input_file),
            "columns": {
                "encoding": "utf-8-sig",
                "id_column": "ID",
                "sinonom_column": "HanNom",
                "quocngu_column": "DichAm",
                "fallback_column": None,
            },
        },
        "dictionary": {
            "translation_dict": str(dictionaries[0].resolve()),
            "similarity_dict": str(dictionaries[1].resolve()),
            "encoding": "utf-8-sig",
        },
        "alignment": {
            "damaged_tokens": ["[MASK]"],
            "costs": {"match": 0, "mismatch": 1, "insertion": 1, "deletion": 1},
        },
        "output": {
            "directory": str(folder),
            "filename": result_file.name,
            "statistics_filename": "statistic.json",
        },
        "processing": {"verbose": False, "show_progress": False},
        "quick_test": False,
    }
    config_file.write_text(yaml.safe_dump(config, allow_unicode=True), encoding="utf-8")
    try:
        result = subprocess.run(
            [sys.executable, str(script), str(config_file)],
            cwd=folder,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            timeout=180,
        )
    except subprocess.TimeoutExpired as error:
        raise ValueError("Code Lab vượt quá thời gian chạy cho bài hiện tại.") from error
    if result.returncode or not result_file.is_file():
        raise ValueError(f"Code Lab chưa tạo kết quả: {(result.stderr or result.stdout)[-1200:]}")
    with result_file.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream, delimiter="\t"))
    if [row["ID"] for row in rows] != [pair["ID"] for pair in pairs]:
        raise ValueError("Kết quả code Lab không khớp danh sách ID đầu vào.")
    statistics = json.loads((folder / "statistic.json").read_text(encoding="utf-8"))
    return rows, {row["ID"]: row for row in statistics["rows"]}
