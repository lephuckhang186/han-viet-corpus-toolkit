"""Hierarchical region matching, reading-order validation, and DP line/grouped-line matching."""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any

from hanviet.extraction.cross_check.normalization import tokenize_han_with_spans
from hanviet.extraction.schema import OCRRecord


def to_rect(bbox: list[Any] | None) -> tuple[float, float, float, float] | None:
    if not bbox:
        return None
    if isinstance(bbox[0], (list, tuple)):
        xs = [float(p[0]) for p in bbox]
        ys = [float(p[1]) for p in bbox]
        return min(xs), min(ys), max(xs), max(ys)
    if len(bbox) == 4:
        return float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3])
    return None


def bbox_iou(b1: list[Any] | None, b2: list[Any] | None) -> float:
    """Compute intersection-over-union between two bboxes (quad or [x0,y0,x1,y1])."""
    r1, r2 = to_rect(b1), to_rect(b2)
    if r1 is None or r2 is None:
        return 0.0
    ix1, iy1 = max(r1[0], r2[0]), max(r1[1], r2[1])
    ix2, iy2 = min(r1[2], r2[2]), min(r1[3], r2[3])
    iw, ih = max(0.0, ix2 - ix1), max(0.0, iy2 - iy1)
    inter = iw * ih
    if inter <= 0.0:
        return 0.0
    area1 = max(0.0, r1[2] - r1[0]) * max(0.0, r1[3] - r1[1])
    area2 = max(0.0, r2[2] - r2[0]) * max(0.0, r2[3] - r2[1])
    union = area1 + area2 - inter
    return inter / union if union > 0 else 0.0


def bbox_overlap_ratio(b1: list[Any] | None, b2: list[Any] | None) -> float:
    """Compute intersection / min(area1, area2), useful for 1-to-n sub-line fragments."""
    r1, r2 = to_rect(b1), to_rect(b2)
    if r1 is None or r2 is None:
        return 0.0
    ix1, iy1 = max(r1[0], r2[0]), max(r1[1], r2[1])
    ix2, iy2 = min(r1[2], r2[2]), min(r1[3], r2[3])
    inter = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)
    if inter <= 0.0:
        return 0.0
    area1 = max(0.0, r1[2] - r1[0]) * max(0.0, r1[3] - r1[1])
    area2 = max(0.0, r2[2] - r2[0]) * max(0.0, r2[3] - r2[1])
    denom = min(area1, area2)
    return inter / denom if denom > 0 else 0.0


def bbox_center_distance(b1: list[Any] | None, b2: list[Any] | None) -> float | None:
    r1, r2 = to_rect(b1), to_rect(b2)
    if r1 is None or r2 is None:
        return None
    cx1, cy1 = (r1[0] + r1[2]) / 2.0, (r1[1] + r1[3]) / 2.0
    cx2, cy2 = (r2[0] + r2[2]) / 2.0, (r2[1] + r2[3]) / 2.0
    dist = math.hypot(cx1 - cx2, cy1 - cy2)
    scale = max(1.0, math.hypot(max(r1[2], r2[2]) - min(r1[0], r2[0]), max(r1[3], r2[3]) - min(r1[1], r2[1])))
    return min(1.0, dist / scale)


def same_coordinate_space(recs_a: list[OCRRecord], recs_b: list[OCRRecord]) -> bool:
    spaces_a = {r.coordinate_space for r in recs_a if r.bbox is not None and r.coordinate_space}
    spaces_b = {r.coordinate_space for r in recs_b if r.bbox is not None and r.coordinate_space}
    return bool(spaces_a and spaces_b and spaces_a == spaces_b)


def _merge_rects(rects: list[tuple[float, float, float, float]]) -> list[float] | None:
    if not rects:
        return None
    return [
        min(r[0] for r in rects),
        min(r[1] for r in rects),
        max(r[2] for r in rects),
        max(r[3] for r in rects),
    ]


def _lev_distance(a: list[str], b: list[str]) -> int:
    m, n = len(a), len(b)
    if m == 0:
        return n
    if n == 0:
        return m
    prev = list(range(n + 1))
    for i in range(1, m + 1):
        curr = [i] + [0] * n
        for j in range(1, n + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            curr[j] = min(prev[j] + 1, curr[j - 1] + 1, prev[j - 1] + cost)
        prev = curr
    return prev[n]


@dataclass(frozen=True)
class LineMatchGroup:
    match_type: str  # 1-1 | 1-n | n-1 | primary_only | secondary_only
    primary_indices: tuple[int, ...]
    secondary_indices: tuple[int, ...]
    cost: float
    text_distance: float
    geometry_distance: float | None
    ambiguous: bool = False
    match_method: str = "dp_line_match"


def _group_pair_cost(
    p_recs: list[OCRRecord],
    s_recs: list[OCRRecord],
    *,
    alpha: float,
    beta: float,
    gamma: float,
    delta: float,
    use_geometry: bool,
) -> tuple[float, float, float | None]:
    p_joined = "".join(r.text for r in p_recs)
    s_joined = "".join(r.text for r in s_recs)
    p_toks = [t.unit for t in tokenize_han_with_spans(p_joined, profile="content").tokens]
    s_toks = [t.unit for t in tokenize_han_with_spans(s_joined, profile="content").tokens]
    max_len = max(len(p_toks), len(s_toks), 1)
    text_dist = _lev_distance(p_toks, s_toks) / max_len
    len_diff = abs(len(p_toks) - len(s_toks)) / max_len
    group_penalty = (max(0, len(p_recs) - 1) + max(0, len(s_recs) - 1)) * 0.5

    geom_dist: float | None = None
    eff_alpha, eff_beta = alpha, beta
    if use_geometry:
        p_rects = [to_rect(r.bbox) for r in p_recs if r.bbox is not None]
        s_rects = [to_rect(r.bbox) for r in s_recs if r.bbox is not None]
        if len(p_rects) == len(p_recs) and len(s_rects) == len(s_recs):
            p_box = _merge_rects([r for r in p_rects if r is not None])
            s_box = _merge_rects([r for r in s_rects if r is not None])
            iou = bbox_iou(p_box, s_box)
            overlap = bbox_overlap_ratio(p_box, s_box)
            cdist = bbox_center_distance(p_box, s_box) or 0.0
            geom_dist = max(0.0, 0.5 * (1.0 - max(iou, overlap)) + 0.5 * cdist)
    if geom_dist is None:
        # Renormalize text weight cleanly when real coordinates are absent (never fake bbox distances).
        total_w = alpha + gamma + delta
        eff_alpha = alpha / total_w if total_w > 0 else 1.0
        eff_gamma = gamma / total_w if total_w > 0 else 0.0
        eff_delta = delta / total_w if total_w > 0 else 0.0
        cost = eff_alpha * text_dist + eff_gamma * len_diff + eff_delta * group_penalty
        return cost, text_dist, None

    cost = eff_alpha * text_dist + eff_beta * geom_dist + gamma * len_diff + delta * group_penalty
    return cost, text_dist, geom_dist


def match_lines_dp(
    primary_lines: list[OCRRecord],
    secondary_lines: list[OCRRecord],
    *,
    alpha: float = 0.65,
    beta: float = 0.15,
    gamma: float = 0.10,
    delta: float = 0.10,
    max_group_size: int = 3,
    skip_cost: float = 0.85,
) -> list[LineMatchGroup]:
    """Configurable Dynamic Programming line/grouped-line matcher supporting 1-1, 1-n, n-1, and skips."""
    m, n = len(primary_lines), len(secondary_lines)
    if m == 0 and n == 0:
        return []
    use_geom = same_coordinate_space(primary_lines, secondary_lines)

    inf = float("inf")
    dp = [[inf] * (n + 1) for _ in range(m + 1)]
    back: list[list[tuple[int, int, str, float, float, float | None, bool] | None]] = [
        [None] * (n + 1) for _ in range(m + 1)
    ]
    dp[0][0] = 0.0

    for i in range(m + 1):
        for j in range(n + 1):
            base = dp[i][j]
            if base == inf:
                continue

            # Skip primary
            if i < m:
                cand = base + skip_cost
                if cand < dp[i + 1][j]:
                    dp[i + 1][j] = cand
                    back[i + 1][j] = (i, j, "primary_only", skip_cost, 1.0, None, False)

            # Skip secondary
            if j < n:
                cand = base + skip_cost
                if cand < dp[i][j + 1]:
                    dp[i][j + 1] = cand
                    back[i][j + 1] = (i, j, "secondary_only", skip_cost, 1.0, None, False)

            # 1-to-k (k in 1..max_group_size)
            if i < m:
                for k in range(1, min(max_group_size, n - j) + 1):
                    step_cost, t_dist, g_dist = _group_pair_cost(
                        [primary_lines[i]],
                        secondary_lines[j : j + k],
                        alpha=alpha,
                        beta=beta,
                        gamma=gamma,
                        delta=delta,
                        use_geometry=use_geom,
                    )
                    cand = base + step_cost
                    mtype = "1-1" if k == 1 else "1-n"
                    amb = k > 1 and t_dist > 0.45
                    if cand < dp[i + 1][j + k]:
                        dp[i + 1][j + k] = cand
                        back[i + 1][j + k] = (i, j, mtype, step_cost, t_dist, g_dist, amb)

            # k-to-1 (k in 2..max_group_size)
            if j < n:
                for k in range(2, min(max_group_size, m - i) + 1):
                    step_cost, t_dist, g_dist = _group_pair_cost(
                        primary_lines[i : i + k],
                        [secondary_lines[j]],
                        alpha=alpha,
                        beta=beta,
                        gamma=gamma,
                        delta=delta,
                        use_geometry=use_geom,
                    )
                    cand = base + step_cost
                    amb = t_dist > 0.45
                    if cand < dp[i + k][j + 1]:
                        dp[i + k][j + 1] = cand
                        back[i + k][j + 1] = (i, j, "n-1", step_cost, t_dist, g_dist, amb)

    groups: list[LineMatchGroup] = []
    ci, cj = m, n
    while ci > 0 or cj > 0:
        entry = back[ci][cj]
        assert entry is not None
        pi, pj, mtype, scost, t_dist, g_dist, amb = entry
        p_idx = tuple(range(pi, ci))
        s_idx = tuple(range(pj, cj))
        groups.append(
            LineMatchGroup(
                match_type=mtype,
                primary_indices=p_idx,
                secondary_indices=s_idx,
                cost=round(scost, 6),
                text_distance=round(t_dist, 6),
                geometry_distance=round(g_dist, 6) if g_dist is not None else None,
                ambiguous=amb,
                match_method="dp_geometry_and_text" if g_dist is not None else "dp_text_match",
            )
        )
        ci, cj = pi, pj
    groups.reverse()
    return groups


def scope_key(record: OCRRecord) -> tuple[str, str, str, int | None]:
    """Hierarchical scope key preventing cross-work or cross-page leaks."""
    return (record.corpus_id, record.work_id, record.source_id, record.pdf_page)


def validate_reading_order(
    matched_items: list[dict[str, Any]],
    *,
    strict_index_equality: bool = True,
) -> list[dict[str, Any]]:
    """Detect reading-order inversions between primary & secondary records without mutating texts."""
    warnings: list[dict[str, Any]] = []
    last_s_order = -1
    for item in matched_items:
        p = item.get("primary")
        s = item.get("secondary")
        if not p or not s:
            continue
        po = p.get("reading_order")
        so = s.get("reading_order")
        if po is None or so is None:
            continue
        crossed = so < last_s_order
        index_diff = strict_index_equality and (po != so)
        if crossed or index_diff:
            warnings.append(
                {
                    "item_id": item["item_id"],
                    "source_id": item["source_id"],
                    "primary_reading_order": po,
                    "secondary_reading_order": so,
                    "reason": (
                        "Secondary engine reading order crosses primary reading order."
                        if crossed
                        else "Secondary engine reading order index differs from primary."
                    ),
                }
            )
        if so > last_s_order:
            last_s_order = so
    return warnings


def detect_duplicate_regions(records: list[OCRRecord], *, iou_threshold: float = 0.85) -> list[dict[str, Any]]:
    """Detect likely duplicated OCR regions within the same (source_id, pdf_page)."""
    duplicates: list[dict[str, Any]] = []
    for i in range(len(records)):
        for j in range(i + 1, len(records)):
            a, b = records[i], records[j]
            if scope_key(a) != scope_key(b):
                continue
            high_iou = a.bbox is not None and b.bbox is not None and bbox_iou(a.bbox, b.bbox) >= iou_threshold
            same_nonempty_text = bool(a.text.strip()) and a.text.strip() == b.text.strip() and len(a.text.strip()) >= 3
            if high_iou or (same_nonempty_text and abs((a.reading_order or 0) - (b.reading_order or 0)) <= 1):
                duplicates.append(
                    {
                        "engine": a.engine,
                        "source_id": a.source_id,
                        "record_ids": [a.record_id, b.record_id],
                        "region_ids": [a.region_id, b.region_id],
                        "reason": "Overlapping geometry" if high_iou else "Consecutive identical multi-char text",
                    }
                )
    return duplicates
