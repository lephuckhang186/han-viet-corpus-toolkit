"""Shared cleaning rules and Han classical text cleaner (protected logic from clean_text.ipynb)."""
from __future__ import annotations

import re
import unicodedata

from .viet_cleaner import normalize_spaces, word_spans

EMPTY_BRACKETS = re.compile(r"\(\s*\)|\[\s*\]|（\s*）|【\s*】")
NOTE_MARK = re.compile(r"\(\s*\d+\s*\)|\[\s*\d+[a-z]?\s*\]|（\s*\d+\s*）|【\s*\d+\s*】")


def clean_shared(
    line: str,
    punctuation_replacements: dict[str, str] | None = None,
) -> tuple[str, list[str]]:
    """Normalize spaces, strip empty brackets, and apply optional punctuation mapping while preserving [MASK]."""
    replacements = punctuation_replacements or {}
    text = normalize_spaces(line)
    rules = ["whitespace"] if text != line else []
    without_empty = normalize_spaces(EMPTY_BRACKETS.sub(" ", text))
    if without_empty != text:
        rules.append("empty_brackets")
    text = without_empty
    if "[MASK]" not in text:  # Custom punctuation replacements never touch MASK.
        replaced = text
        for old, new in replacements.items():
            replaced = replaced.replace(old, new)
        if replaced != text:
            rules.append("punctuation_config")
        text = replaced
    return text, rules


def common_flags(text: str) -> list[str]:
    """Detect suspicious line patterns without mutating source content."""
    visible = text.replace("[MASK]", "")
    flags: list[str] = []
    if NOTE_MARK.search(visible):
        flags.append("possible_note_marker")
    if any(visible.count(a) != visible.count(b) for a, b in [("(", ")"), ("[", "]"), ("（", "）"), ("【", "】")]):
        flags.append("unbalanced_brackets")
    if re.fullmatch(r"\d+", visible.strip()):
        flags.append("standalone_number")
    if any(
        any(c.isalpha() for c in token) and any(c.isdigit() for c in token)
        for _, _, token in word_spans(visible)
    ):
        flags.append("letters_attached_to_digits")
    if re.search(r"[_#@=<>\\|{}~^$]", visible) or any(
        unicodedata.category(c) in {"Cc", "Cf"} or c == "\ufffd" for c in visible
    ):
        flags.append("unexpected_symbol")
    return flags


def clean_han(
    line: str,
    punctuation_replacements: dict[str, str] | None = None,
) -> tuple[str, list[str], list[str]]:
    """Preserve Han/Nom code points (including Extension B+ and PUA) while flagging anomalies."""
    text, rules = clean_shared(line, punctuation_replacements=punctuation_replacements)
    flags = common_flags(text)
    if any(c.isalpha() and "LATIN" in unicodedata.name(c, "") for c in text.replace("[MASK]", "")):
        flags.append("latin_in_han")
    if re.search(r"[%％○]", text):
        flags.append("han_symbol_check")
    return text, rules, flags
