"""Protected alignment DP, link validation, grouping, and fingerprint verification."""
from __future__ import annotations

import re
import unicodedata

VERSIONS = {
    "han": "han",
    "am": "viet/dich_am",
    "nghia": "viet/dich_nghia",
    "tho": "viet/dich_tho",
}


def public_units(units):
    return [{"id": item["id"], "text": item["text"]} for item in units]


def lab_text(text, kind):
    """Strip punctuation on the comparison copy, preserving [MASK] and tone marks."""
    chunks = re.split(r"(\[MASK\])", unicodedata.normalize("NFC", text))
    separator = "" if kind == "han" else " "
    for i in range(0, len(chunks), 2):
        chunks[i] = "".join(separator if unicodedata.category(c)[0] in "PS" else c for c in chunks[i])
    return separator.join("".join(chunks).split())


def phonetic_links(han, am):
    """Propose adjacent spans by length before the Lab's character alignment."""
    glyphs = [len(re.sub(r"\[MASK\]", "□", lab_text(u["text"], "han"))) for u in han]
    syllables = [len(lab_text(u["text"], "am").split()) for u in am]
    steps = ((1, 1), (1, 2), (2, 1), (1, 0), (0, 1))
    costs = {(0, 0): 0}
    back = {}
    for i in range(len(han) + 1):
        for j in range(len(am) + 1):
            if (i, j) == (0, 0):
                continue
            candidates = []
            for a, b in steps:
                if i < a or j < b:
                    continue
                size_h, size_a = sum(glyphs[i - a : i]), sum(syllables[j - b : j])
                if a and b and size_h and size_a:
                    cost = abs(size_h - size_a) / max(size_h, size_a) + (0.1 if a != b else 0)
                elif a and b:
                    continue
                else:
                    cost = 0.7
                if (i - a, j - b) in costs:
                    candidates.append((costs[i - a, j - b] + cost, (a, b)))
            costs[i, j], back[i, j] = min(candidates, key=lambda candidate: candidate[0])
    links = []
    i, j = len(han), len(am)
    while i or j:
        a, b = back[i, j]
        if a and b:
            links.append(
                {
                    "han_ids": [u["id"] for u in han[i - a : i]],
                    "am_ids": [u["id"] for u in am[j - b : j]],
                }
            )
        i, j = i - a, j - b
    return links[::-1]


def indices(ids, lookup):
    if not isinstance(ids, list) or not ids or any(not isinstance(i, str) or i not in lookup for i in ids):
        raise ValueError(f"Danh sách ID không hợp lệ: {ids}")
    values = [lookup[i] for i in ids]
    if values != list(range(values[0], values[0] + len(values))):
        raise ValueError(f"Các ID phải liền nhau và theo đúng thứ tự: {ids}")
    return values


def validate_links(links, han, viet, kind):
    if not isinstance(links, list):
        raise ValueError(f"Danh sách liên kết {kind} không hợp lệ.")
    han_ids = {u["id"]: i for i, u in enumerate(han)}
    viet_ids = {u["id"]: i for i, u in enumerate(viet)}
    previous_han = previous_viet = -1
    for link in links:
        if not isinstance(link, dict):
            raise ValueError(f"Liên kết {kind} phải là một object.")
        h = indices(link.get("han_ids"), han_ids)
        v = indices(link.get(f"{kind}_ids"), viet_ids)
        if h[0] <= previous_han or v[0] <= previous_viet:
            raise ValueError(f"Liên kết {kind} trùng hoặc chéo thứ tự.")
        previous_han, previous_viet = h[-1], v[-1]
    return links


def make_rows(units, links):
    han_position = {u["id"]: i for i, u in enumerate(units["han"])}
    text = {u["id"]: u["text"] for entries in units.values() for u in entries}
    ranges = []
    for kind in ("am", "nghia", "tho"):
        validate_links(links.get(kind, []), units["han"], units[kind], kind)
        for link in links.get(kind, []):
            first, last = (han_position[link["han_ids"][i]] for i in (0, -1))
            ranges.append((first, last, kind, link[f"{kind}_ids"]))
    groups = []
    for first, last, kind, target in sorted(ranges):
        if groups and first <= groups[-1]["end"]:
            group = groups[-1]
            group["end"] = max(group["end"], last)
            group[kind].extend(target)
        else:
            group = dict(start=first, end=last, am=[], nghia=[], tho=[])
            group[kind].extend(target)
            groups.append(group)
    rows = []
    for group in groups:
        ids = [u["id"] for u in units["han"][group["start"] : group["end"] + 1]]
        rows.append(
            {
                "han_ids": ids,
                "cells": [
                    " ".join(text[i] for i in selected)
                    for selected in (ids, group["am"], group["nghia"], group["tho"])
                ],
            }
        )
    return rows


def unmatched_ids(units, links):
    used = {kind: set() for kind in VERSIONS}
    for kind in ("am", "nghia", "tho"):
        for link in links.get(kind, []):
            used["han"].update(link["han_ids"])
            used[kind].update(link[f"{kind}_ids"])
    return {kind: [u["id"] for u in members if u["id"] not in used[kind]] for kind, members in units.items()}


def verify_identity(record, work, fingerprint):
    if record.get("work") != work or record.get("fingerprint") != fingerprint:
        raise ValueError("Mã bài hoặc dấu vân tay văn bản không khớp. Lấy lại JSON hiện tại.")
