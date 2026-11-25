"""Han image preprocessing, column grouping, and horizontal row splitting (extracted from ocr_nlp.ipynb)."""
from __future__ import annotations

import math
from pathlib import Path
import statistics
from typing import Any


BAC_MAIN_PREPROCESS_PARAMS_DEFAULT = {
    "red_hue_width": 18,
    "red_min_saturation": 50,
    "red_min_r_minus_g": 20,
    "red_protect_max_below": 100,
    "background_max_side": 768,
    "background_filter_size": 31,
    "background_blur": 5.0,
    "black_point": 65,
    "white_point": 195,
    "tone_gamma": 1.15,
    "binary_threshold": None,
}

HAN_ROW_SETTINGS_DEFAULT = {
    "max_side": 2048,
    "ink_threshold": 160,
    "min_ink_fraction": 0.02,
    "bridge_gap": 2,
    "min_height_fraction": 0.008,
    "padding_fraction": 0.25,
    "min_padding_fraction": 0.02,
}


def bac_su_preprocess(image, params: dict[str, Any] | None = None):
    """Derive de-redded/background-normalized variants preserving source pixel dimensions (1:1 coordinate transform)."""
    from PIL import Image, ImageChops, ImageFilter, ImageMath, ImageOps

    params = params or BAC_MAIN_PREPROCESS_PARAMS_DEFAULT
    expected = set(BAC_MAIN_PREPROCESS_PARAMS_DEFAULT)
    if set(params) != expected:
        raise ValueError("Thiếu/thừa khóa BAC_PREPROCESS_PARAMS: " + str(set(params) ^ expected))
    if (
        not 0 <= params["red_hue_width"] <= 40
        or not 0 <= params["red_min_saturation"] <= 255
        or not 0 <= params["red_min_r_minus_g"] <= 255
        or not 0 <= params["red_protect_max_below"] <= 255
        or params["background_max_side"] < 32
        or params["background_filter_size"] < 3
        or params["background_filter_size"] % 2 != 1
        or params["background_blur"] < 0
        or not 0 <= params["black_point"] < params["white_point"] <= 255
        or params["tone_gamma"] <= 0
        or (params["binary_threshold"] is not None and not 0 <= params["binary_threshold"] <= 255)
    ):
        raise ValueError("Tham số tiền xử lý nằm ngoài phạm vi hợp lệ.")
    rgb = image.convert("RGB")
    hue, saturation, value = rgb.convert("HSV").split()
    red, green, _ = rgb.split()
    hue_mask = hue.point(
        [255 if h <= params["red_hue_width"] or h >= 256 - params["red_hue_width"] else 0 for h in range(256)]
    )
    saturation_mask = saturation.point([255 if s >= params["red_min_saturation"] else 0 for s in range(256)])
    dominance = ImageChops.subtract(red, green).point(
        [255 if d >= params["red_min_r_minus_g"] else 0 for d in range(256)]
    )
    protected = value.point([255 if v >= params["red_protect_max_below"] else 0 for v in range(256)])
    red_mask = ImageChops.multiply(
        ImageChops.multiply(hue_mask, saturation_mask), ImageChops.multiply(dominance, protected)
    )
    gray_original = ImageOps.grayscale(rgb)
    background = gray_original.copy()
    background.thumbnail((params["background_max_side"], params["background_max_side"]))
    background = background.filter(ImageFilter.MaxFilter(params["background_filter_size"]))
    background = background.filter(ImageFilter.GaussianBlur(params["background_blur"]))
    background = background.resize(rgb.size, Image.Resampling.BILINEAR)
    no_red = Image.composite(background, gray_original, red_mask)
    normalized = Image.new("L", rgb.size)
    for top in range(0, rgb.height, 256):
        box = (0, top, rgb.width, min(top + 256, rgb.height))
        foreground = no_red.crop(box).convert("F")
        base = background.crop(box).point([max(1, v) for v in range(256)]).convert("F")
        stripe = ImageMath.lambda_eval(lambda a: a["fg"] * 255 / a["bg"], fg=foreground, bg=base).convert("L")
        normalized.paste(stripe, (0, top))
    black, white = params["black_point"], params["white_point"]
    curve = [round(255 * min(1.0, max(0.0, (v - black) / (white - black))) ** params["tone_gamma"]) for v in range(256)]
    soft = normalized.point(curve)
    histogram = soft.histogram()
    threshold = params["binary_threshold"]
    if threshold is None:
        total = sum(histogram)
        sum_all = sum(i * count for i, count in enumerate(histogram))
        count_low, sum_low, best = 0, 0, -1.0
        threshold = 127
        for i, count in enumerate(histogram):
            count_low += count
            sum_low += i * count
            count_high = total - count_low
            if not count_low or not count_high:
                continue
            difference = sum_low / count_low - (sum_all - sum_low) / count_high
            score = count_low * count_high * difference * difference
            if score > best:
                best, threshold = score, i
    binary = soft.point([0 if v <= threshold else 255 for v in range(256)])
    overlay = Image.composite(Image.new("RGB", rgb.size, (255, 0, 180)), rgb, red_mask)
    mask_count = red_mask.histogram()[255]
    stats = {
        "algorithm": "bac_su_color_background_tone_v1",
        "source_size": list(rgb.size),
        "coordinate_transform": {"scale_x": 1.0, "scale_y": 1.0, "offset_x": 0, "offset_y": 0},
        "red_mask_pixels": mask_count,
        "red_mask_fraction": mask_count / (rgb.width * rgb.height),
        "white_fraction_soft": soft.histogram()[255] / (rgb.width * rgb.height),
        "binary_threshold": threshold,
        "output_mode": "RGB",
        "params": dict(params),
    }
    return {
        "original": rgb,
        "red_mask": red_mask,
        "red_overlay": overlay,
        "gray_only": gray_original.convert("RGB"),
        "soft_gray": soft.convert("RGB"),
        "binary_otsu": binary.convert("RGB"),
    }, stats


def horizontal_han_rows(image, settings: dict[str, Any] | None = None, manual_boxes=None):
    """Detect horizontal Han line boxes in source image pixels without modifying source pixels."""
    from PIL import ImageFilter

    settings = {**HAN_ROW_SETTINGS_DEFAULT, **(settings or {})}
    width, height = image.size
    if manual_boxes is not None:
        boxes = []
        for box in manual_boxes:
            if len(box) != 4 or any(type(v) is not int for v in box):
                raise ValueError("row_boxes cần bốn tọa độ pixel nguyên cho mỗi hàng.")
            x1, y1, x2, y2 = box
            if not (0 <= x1 < x2 <= width and 0 <= y1 < y2 <= height):
                raise ValueError("row_boxes nằm ngoài ảnh hoặc có diện tích bằng 0.")
            boxes.append(list(box))
        if not boxes:
            raise ValueError("row_boxes không được rỗng; bỏ khóa này để tự tách hàng.")
        return boxes, {"method": "manual_rows", "source_size": [width, height], "flags": []}

    analysis = image.convert("L")
    analysis.thumbnail((settings["max_side"], settings["max_side"]))
    aw, ah = analysis.size
    mask = analysis.filter(ImageFilter.MedianFilter(3)).point(
        [255 if value < settings["ink_threshold"] else 0 for value in range(256)]
    )
    pixels = mask.tobytes()
    ink = [pixels[y * aw : (y + 1) * aw].count(255) for y in range(ah)]
    minimum = max(3, math.ceil(aw * settings["min_ink_fraction"]))
    bands, start, last = [], None, None
    for y, count in enumerate(ink):
        if count < minimum:
            continue
        if start is None:
            start = y
        elif y - last - 1 > settings["bridge_gap"]:
            bands.append((start, last + 1))
            start = y
        last = y
    if start is not None:
        bands.append((start, last + 1))
    minimum_height = max(4, math.ceil(aw * settings["min_height_fraction"]))
    rejected = [list(b) for b in bands if b[1] - b[0] < minimum_height]
    bands = [b for b in bands if b[1] - b[0] >= minimum_height]
    boxes = []
    for i, (top, bottom) in enumerate(bands):
        upper = (bands[i - 1][1] + top) // 2 if i else 0
        lower = (bottom + bands[i + 1][0]) // 2 if i + 1 < len(bands) else ah
        padding = max(
            2,
            math.ceil(aw * settings["min_padding_fraction"]),
            math.ceil((bottom - top) * settings["padding_fraction"]),
        )
        y1 = max(upper, top - padding)
        y2 = min(lower, bottom + padding)
        boxes.append([0, math.floor(y1 * height / ah), width, math.ceil(y2 * height / ah)])
    flags = []
    if not boxes:
        flags.append("no_horizontal_rows")
    median_height = statistics.median([b[1] - b[0] for b in bands]) if bands else 0
    tall = [i for i, (a, z) in enumerate(bands) if z - a > 1.8 * median_height]
    if tall:
        flags.append("unusual_row_height")
    covered = set()
    for _, y1, _, y2 in boxes:
        covered.update(range(max(0, math.floor(y1 * ah / height)), min(ah, math.ceil(y2 * ah / height))))
    total_ink = sum(ink)
    outside = sum(value for y, value in enumerate(ink) if y not in covered)
    outside_fraction = outside / total_ink if total_ink else 0.0
    if outside_fraction > 0.02:
        flags.append("ink_outside_rows")
    return boxes, {
        "method": "horizontal_projection_v1",
        "source_size": [width, height],
        "analysis_size": [aw, ah],
        "settings": settings,
        "bands": [list(b) for b in bands],
        "rejected_short_bands": rejected,
        "unusual_row_indices": tall,
        "outside_ink_fraction": outside_fraction,
        "flags": flags,
    }


def grouped_vertical_columns(data: dict[str, Any], center_ratio: float = 0.45) -> dict[str, Any]:
    """Group vertical regions into RTL columns using fixed tall-anchor centers."""
    texts, polygons = data.get("rec_texts", []), data.get("rec_polys", [])
    if len(polygons) != len(texts):
        raise ValueError("Không đủ tọa độ để nhóm cột.")
    if not 0 < center_ratio < 1:
        raise ValueError("Dung sai nhóm cột phải nằm giữa 0 và 1.")
    if not texts:
        return {"order": [], "groups": [], "ambiguous_indices": [], "tolerance": 0.0}
    bounds = []
    for points in polygons:
        if not points or any(not math.isfinite(float(v)) for point in points for v in point):
            raise ValueError("Tọa độ cột không hợp lệ.")
        x1, x2 = min(p[0] for p in points), max(p[0] for p in points)
        y1, y2 = min(p[1] for p in points), max(p[1] for p in points)
        bounds.append((float(x1), float(y1), float(x2), float(y2)))
    centers = [(b[0] + b[2]) / 2 for b in bounds]
    widths = [max(1.0, b[2] - b[0]) for b in bounds]
    heights = [max(1.0, b[3] - b[1]) for b in bounds]
    tall = [i for i in range(len(texts)) if heights[i] >= 2 * widths[i]]
    typical = statistics.median([widths[i] for i in tall] or widths)
    tolerance = typical * center_ratio
    anchors, groups, ambiguous = [], [], []
    candidates = sorted(tall, key=lambda i: (-heights[i], -centers[i], i))
    candidates += sorted(set(range(len(texts))) - set(tall), key=lambda i: (-centers[i], bounds[i][1], i))
    for index in candidates:
        near = [(abs(centers[index] - x), group) for group, x in enumerate(anchors) if abs(centers[index] - x) <= tolerance]
        if near:
            if len(near) > 1:
                ambiguous.append(index)
            group = min(near)[1]
            groups[group].append(index)
        else:
            anchors.append(centers[index])
            groups.append([index])
    columns = [
        sorted(groups[g], key=lambda i: (bounds[i][1], -centers[i], i))
        for g in sorted(range(len(groups)), key=lambda g: (-anchors[g], g))
    ]
    return {
        "order": [i for column in columns for i in column],
        "groups": columns,
        "ambiguous_indices": ambiguous,
        "tolerance": tolerance,
    }


def text_order(data: dict[str, Any], mode: str, column_center_ratio: float = 0.45) -> list[int]:
    indices = list(range(len(data["rec_texts"])))
    if mode == "model" or not indices:
        return indices
    polygons = data.get("rec_polys")
    if polygons is None or len(polygons) != len(indices):
        raise ValueError("Không đủ tọa độ để xếp cột dọc.")
    if mode == "vertical_columns_rtl":
        return grouped_vertical_columns(data, column_center_ratio)["order"]
    if mode == "top_to_bottom":
        return sorted(indices, key=lambda i: (min(p[1] for p in polygons[i]), min(p[0] for p in polygons[i])))
    return sorted(
        indices,
        key=lambda i: (-sum(p[0] for p in polygons[i]) / len(polygons[i]), min(p[1] for p in polygons[i])),
    )
