"""Vietnamese rule-based cleaner and dictionary loader (protected logic from clean_text.ipynb)."""
from __future__ import annotations

import csv
from pathlib import Path
import re
import unicodedata


VIET_LABELS = {
    "dich_am": {"phiên âm", "dịch âm"},
    "dich_nghia": {"dịch nghĩa"},
    "dich_tho": {"dịch thơ"},
}


def normalize_latin(text: str) -> str:
    """Normalize decomposed Latin accent runs to NFC without altering non-Latin characters."""
    result, pending = [], []
    for ch in text:
        is_latin = "LATIN" in unicodedata.name(ch, "")
        is_mark = unicodedata.category(ch).startswith("M")
        if is_latin or (is_mark and pending):
            pending.append(ch)
        else:
            if pending:
                result.append(unicodedata.normalize("NFC", "".join(pending)))
                pending = []
            result.append(ch)
    if pending:
        result.append(unicodedata.normalize("NFC", "".join(pending)))
    return "".join(result)


def normalize_spaces(line: str) -> str:
    """Normalize horizontal space/tabs/Zs separators to single ASCII spaces."""
    line = "".join(" " if c == "\t" or unicodedata.category(c) == "Zs" else c for c in line)
    return re.sub(r" +", " ", line).strip(" ")


def word_spans(text: str):
    """Yield (start, end, token) spans for L/M/N Unicode character runs."""
    start = None
    for i, ch in enumerate(text + " "):
        inside = unicodedata.category(ch)[0] in "LMN"
        if inside and start is None:
            start = i
        elif not inside and start is not None:
            yield start, i, text[start:i]
            start = None


def suffix_digit_suggestion(text: str) -> str:
    """Suggest removal of trailing note digits attached directly to words (never standalone numbers)."""
    edits = []
    for start, end, token in word_spans(text):
        split = len(token)
        while split and token[split - 1].isdigit():
            split -= 1
        prefix = token[:split]
        if split < len(token) and any(c.isalpha() for c in prefix) and not any(c.isdigit() for c in prefix):
            edits.append((start + split, end))
    for start, end in reversed(edits):
        text = text[:start] + text[end:]
    return text


def load_pronunciation_vocabulary(path: Path | str) -> set[str]:
    """Load casefolded QuocNgu vocabulary from QuocNgu_SinoNom_TongHop3.csv."""
    path = Path(path)
    if not path.is_file():
        return set()
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames or "QuocNgu" not in reader.fieldnames:
            raise ValueError("Từ điển cần cột QuocNgu.")
        return {normalize_latin(row["QuocNgu"].strip()).casefold() for row in reader}


def clean_viet(
    line: str,
    kind: str,
    *,
    native_pdf: bool = False,
    punctuation_replacements: dict[str, str] | None = None,
) -> tuple[str, list[str], list[str]]:
    """Clean Vietnamese line per protected rules from clean_text.ipynb."""
    from .han_cleaner import clean_shared, common_flags

    nfc = normalize_latin(line)
    normalized = nfc.translate(str.maketrans("Ƣƣ", "Ưư")) if native_pdf else nfc
    without_folios = re.sub(r"\[\d{1,3}[ab]\]", "", normalized) if native_pdf else normalized
    text, rules = clean_shared(without_folios, punctuation_replacements=punctuation_replacements)
    if without_folios != normalized:
        rules.insert(0, "vietnamese_pdf_folio")
    if normalized != nfc:
        rules.insert(0, "vietnamese_pdf_glyph")
    if nfc != line:
        rules.insert(0, "vietnamese_nfc")
    if text.casefold().rstrip(":").rstrip() in VIET_LABELS.get(kind, set()):
        return "", rules + ["standalone_version_label"], []
    flags = common_flags(text)
    if re.search(r"[%％]", text):
        flags.append("percent_check")
    if re.fullmatch(r"chú thích\s*:?", text, re.IGNORECASE):
        flags.append("possible_note_section")
    return text, rules, flags
