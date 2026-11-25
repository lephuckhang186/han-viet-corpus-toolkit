"""Vietnamese line crop & quad rectification (preserved from ocr_nlp.ipynb)."""
from __future__ import annotations

import math


def line_crop(image, polygon, padding: int = 0):
    """Rectify quad polygon (TL, TR, BR, BL) into an upright line image in memory."""
    from PIL import Image

    if len(polygon) != 4 or any(len(p) != 2 for p in polygon):
        raise ValueError("Vùng dòng phải có đúng bốn đỉnh (x, y).")
    points = [(float(x), float(y)) for x, y in polygon]
    if not all(math.isfinite(v) for p in points for v in p):
        raise ValueError("Tọa độ dòng không hữu hạn.")
    tl, tr, br, bl = points
    distance = lambda a, b: math.hypot(a[0] - b[0], a[1] - b[1])
    width = max(distance(tl, tr), distance(bl, br))
    height = max(distance(tl, bl), distance(tr, br))
    area = abs(sum(points[i][0] * points[(i + 1) % 4][1] - points[(i + 1) % 4][0] * points[i][1] for i in range(4))) / 2
    if width < 1 or height < 1 or area < 1 or any(distance(points[i], points[(i + 1) % 4]) < 1 for i in range(4)):
        raise ValueError("Vùng dòng rỗng hoặc suy biến; giữ lỗi để rà soát ảnh.")
    ux, uy = (tr[0] - tl[0]) / distance(tl, tr), (tr[1] - tl[1]) / distance(tl, tr)
    vx, vy = (bl[0] - tl[0]) / distance(tl, bl), (bl[1] - tl[1]) / distance(tl, bl)
    padded = [
        (x + sx * padding * ux + sy * padding * vx, y + sx * padding * uy + sy * padding * vy)
        for (x, y), sx, sy in zip(points, [-1, 1, 1, -1], [-1, -1, 1, 1])
    ]
    quad = tuple(v for i in [0, 3, 2, 1] for v in padded[i])
    size = (math.ceil(width + 2 * padding), math.ceil(height + 2 * padding))
    source = image if image.mode == "RGB" else image.convert("RGB")
    crop = source.transform(size, Image.Transform.QUAD, quad, resample=Image.Resampling.BICUBIC, fillcolor="white")
    return crop, padded
