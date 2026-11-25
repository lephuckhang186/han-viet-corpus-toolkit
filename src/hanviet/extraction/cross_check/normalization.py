"""Han OCR comparison normalization preserving source raw strings and exact code-point spans."""
from __future__ import annotations

from dataclasses import dataclass
import re
import unicodedata

MASK_TOKEN = "[MASK]"

# Variation Selectors (BMP U+FE00..U+FE0F and Ideographic Variation Selectors U+E0100..U+E01EF)
def _is_selector_or_mark(ch: str) -> bool:
    code = ord(ch)
    if unicodedata.category(ch).startswith("M"):
        return True
    return (0xFE00 <= code <= 0xFE0F) or (0xE0100 <= code <= 0xE01EF)


def is_rare_han_token(token: str) -> bool:
    """Detect CJK Extension B+, CJK Compatibility Ideographs, or PUA glyphs without dropping them."""
    if not token or token == MASK_TOKEN:
        return False
    for ch in token:
        cp = ord(ch)
        if cp >= 0x20000 or (0xE000 <= cp <= 0xF8FF) or (0xF900 <= cp <= 0xFAFF):
            return True
    return False


_HAN_NUMBER_RE = re.compile(r"(?:\d+|[〇零一二三四五六七八九十百千萬億廿卅]+)")


def is_number_or_era_token(token: str) -> bool:
    return bool(token and token != MASK_TOKEN and _HAN_NUMBER_RE.fullmatch(token))


def is_punctuation_token(token: str) -> bool:
    if not token or token == MASK_TOKEN:
        return False
    return all(unicodedata.category(ch).startswith("P") for ch in token)


def is_whitespace_token(token: str) -> bool:
    return bool(token) and all(ch.isspace() for ch in token)


@dataclass(frozen=True)
class ComparisonToken:
    unit: str
    orig_start: int
    orig_end: int
    norm_start: int
    norm_end: int


@dataclass(frozen=True)
class NormalizedHan:
    original: str
    normalized: str
    profile: str
    tokens: list[ComparisonToken]


def tokenize_han_with_spans(
    text: str,
    *,
    profile: str = "strict",
    punctuation_equivalents: dict[str, str] | None = None,
) -> NormalizedHan:
    """Normalize a comparison copy of Han text while mapping every comparison unit to original code-point spans.

    Rules enforced:
    - Original text is never mutated.
    - Never converts Traditional <-> Simplified Chinese or runs lossy NFKC.
    - Keeps `[MASK]` intact as a single atomic unit.
    - Keeps base code point + CJK variation selectors / combining marks together as one unit.
    - `strict` preserves punctuation and spacing; `content` collapses runs of whitespace and applies only
      explicit punctuation equivalents when provided.
    """
    if profile not in {"strict", "content"}:
        raise ValueError(f"Unsupported Han normalization profile: {profile!r}")

    # Step 1: normalize line endings while tracking original offsets via regex scanning
    tokens: list[ComparisonToken] = []
    norm_chunks: list[str] = []
    norm_cursor = 0
    pos = 0
    length = len(text)

    while pos < length:
        if text.startswith(MASK_TOKEN, pos):
            end = pos + len(MASK_TOKEN)
            tokens.append(ComparisonToken(MASK_TOKEN, pos, end, norm_cursor, norm_cursor + len(MASK_TOKEN)))
            norm_chunks.append(MASK_TOKEN)
            norm_cursor += len(MASK_TOKEN)
            pos = end
            continue

        # Normalize CRLF / CR -> single LF unit
        if text[pos] == "\r":
            end = pos + 2 if (pos + 1 < length and text[pos + 1] == "\n") else pos + 1
            if profile == "content":
                # Collapse contiguous whitespace in content profile
                while end < length and text[end] in {" ", "\t", "\r", "\n"}:
                    end += 1
                unit = " "
            else:
                unit = "\n"
            tokens.append(ComparisonToken(unit, pos, end, norm_cursor, norm_cursor + len(unit)))
            norm_chunks.append(unit)
            norm_cursor += len(unit)
            pos = end
            continue

        if profile == "content" and text[pos] in {" ", "\t", "\n", "\u3000"}:
            end = pos + 1
            while end < length and text[end] in {" ", "\t", "\n", "\r", "\u3000"}:
                end += 1
            unit = " "
            tokens.append(ComparisonToken(unit, pos, end, norm_cursor, norm_cursor + 1))
            norm_chunks.append(unit)
            norm_cursor += 1
            pos = end
            continue

        # Grab base code point plus trailing variation selectors / combining marks
        end = pos + 1
        while end < length and _is_selector_or_mark(text[end]) and not text.startswith(MASK_TOKEN, end):
            end += 1
        raw_cluster = text[pos:end]
        nfc_cluster = unicodedata.normalize("NFC", raw_cluster)
        if profile == "content" and punctuation_equivalents:
            nfc_cluster = "".join(punctuation_equivalents.get(ch, ch) for ch in nfc_cluster)

        tokens.append(ComparisonToken(nfc_cluster, pos, end, norm_cursor, norm_cursor + len(nfc_cluster)))
        norm_chunks.append(nfc_cluster)
        norm_cursor += len(nfc_cluster)
        pos = end

    # Strip leading/trailing technical spaces in content profile only
    if profile == "content":
        while tokens and tokens[0].unit == " ":
            tokens.pop(0)
        while tokens and tokens[-1].unit == " ":
            tokens.pop()
        normalized = "".join(t.unit for t in tokens)
        # Recompute norm_start/norm_end cleanly
        reindexed: list[ComparisonToken] = []
        cursor = 0
        for tok in tokens:
            reindexed.append(ComparisonToken(tok.unit, tok.orig_start, tok.orig_end, cursor, cursor + len(tok.unit)))
            cursor += len(tok.unit)
        tokens = reindexed
    else:
        normalized = "".join(norm_chunks)

    return NormalizedHan(original=text, normalized=normalized, profile=profile, tokens=tokens)
