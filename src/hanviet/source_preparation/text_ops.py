"""Cắt TXT theo dòng/ký tự; giữ nguyên chữ và nội dung, không OCR/làm sạch."""
from pathlib import Path


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def select_lines(path: Path, start: int, end: int) -> tuple[str, dict]:
    text = read_text(path)
    lines = text.splitlines(keepends=True)
    if not 1 <= start <= end <= len(lines):
        raise ValueError(f"TXT có {len(lines)} dòng; cần 1 <= dòng đầu <= dòng cuối <= tổng dòng.")
    return "".join(lines[start - 1:end]), {"line_start": start, "line_end": end}


def select_characters(path: Path, start: int, end: int) -> tuple[str, dict]:
    text = read_text(path)
    if not 0 <= start < end <= len(text):
        raise ValueError("Khoảng ký tự TXT không hợp lệ.")
    return text[start:end], {"char_start": start, "char_end_exclusive": end}


def join_parts(parts: list[str]) -> str:
    # Only separate successive crops: preserve each raw part internally.
    return "\n".join(parts)
