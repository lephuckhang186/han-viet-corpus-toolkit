"""Protected segmentation algorithms (exact logic from cong_cu/dong_hang.py)."""
from __future__ import annotations

import re


def clean_spacing(text: str) -> str:
    return " ".join(text.split())


def content_line_spans(text: str):
    return [match.span() for match in re.finditer(r"[^\r\n\f]+", text) if match.group().strip()]


def split_prose(text: str, start: int, end: int, kind: str):
    """Split on sentence punctuation while retaining original TXT offsets."""
    pattern = r"[。！？；]+[」』”’]*" if kind == "han" else r"[.!?…]+[\"”’»)]*(?=\s|$)"
    if kind == "nghia":
        # OCR can glue sentences across a period, for example "kịp.Vậy".
        pattern += r"|(?<=[^\W\d_]{2})\.(?=[^\W\d_])"
    cursor = start
    for mark in re.finditer(pattern, text[start:end]):
        stop = start + mark.end()
        if kind == "nghia" and stop < end and not (text[stop].isspace() or text[stop].isupper()):
            continue
        prefix = text[start + mark.start() - min(mark.start(), 10):stop]
        if kind != "han" and re.search(r"\b(?:TS|GS|PGS|ThS|TP|Q|tr|vd)\.$", prefix, re.I):
            continue
        if text[cursor:stop].strip():
            yield cursor, stop
        cursor = stop
    if text[cursor:end].strip():
        yield cursor, end


def segment(text: str, kind: str, id_prefix: str, genre: str, titles: int = 0, line_range=None, *, keep_lines: bool = False):
    lines = content_line_spans(text)
    if line_range is not None:
        first, last = line_range
        if not 1 <= first <= last <= len(lines):
            raise ValueError(f"Khoảng dòng {line_range} nằm ngoài file {kind}.")
        lines = lines[first - 1:last]
    if not 0 <= titles < len(lines):
        raise ValueError(f"Số dòng tiêu đề không hợp lệ cho {kind}.")
    lines = lines[titles:]
    start, end = lines[0][0], lines[-1][1]
    # A line of classical Chinese with no sentence marks is only a draft unit.
    use_lines = keep_lines or genre == "poetry" or (kind == "han" and not re.search(r"[。！？；]", text[start:end]))
    spans = lines if use_lines else split_prose(text, start, end, kind)
    units = []
    for index, (start, end) in enumerate(spans, 1):
        start += len(text[start:end]) - len(text[start:end].lstrip())
        units.append({
            "id": f"{id_prefix}/{kind}/{index:04}",
            "text": clean_spacing(text[start:end]),
            "start": start,
            "end": end,
            "part": text.count("\f", 0, start) + 1,
        })
    return units
