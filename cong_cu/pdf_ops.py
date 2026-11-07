"""Đọc PDF nguồn, cắt PNG và lấy lớp chữ; không tạo PDF đầu ra."""
from io import BytesIO
from pathlib import Path
import math

import pypdfium2 as pdfium

from .models import Box


def info(path: Path) -> dict:
    with pdfium.PdfDocument(str(path)) as doc:
        return {"pages": len(doc), "bytes": path.stat().st_size}


def render_page(path: Path, page_number: int, dpi: int = 100):
    if not 36 <= dpi <= 600:
        raise ValueError("DPI cần trong khoảng 36–600.")
    with pdfium.PdfDocument(str(path)) as doc:
        if not 1 <= page_number <= len(doc):
            raise ValueError(f"PDF có {len(doc)} trang, không có trang {page_number}.")
        page = doc[page_number - 1]
        try:
            bitmap = page.render(scale=dpi / 72)
            try:
                return bitmap.to_pil().convert("RGB").copy()
            finally:
                bitmap.close()
        finally:
            page.close()


def crop_png(path: Path, page_number: int, box: Box, dpi: int) -> bytes:
    image = render_page(path, page_number, dpi)
    w, h = image.size
    pixels = (math.floor(box.x0 * w), math.floor(box.y0 * h), math.ceil(box.x1 * w), math.ceil(box.y1 * h))
    region = image.crop(pixels)
    buffer = BytesIO()
    region.save(buffer, format="PNG", dpi=(dpi, dpi))
    return buffer.getvalue()


def extract_text(path: Path, page_number: int, box: Box) -> str:
    # The bounded API supports Unicode beyond BMP (important for Nôm).
    with pdfium.PdfDocument(str(path)) as doc:
        page = doc[page_number - 1]
        try:
            if page.get_rotation() != 0:
                raise ValueError("Trích text vùng PDF xoay chưa hỗ trợ. Lưu PNG hoặc dùng nguồn không xoay.")
            left, bottom, right, top = page.get_bbox()
            width, height = right - left, top - bottom
            textpage = page.get_textpage()
            try:
                text = textpage.get_text_bounded(
                    left=left + box.x0 * width, bottom=bottom + (1 - box.y1) * height,
                    right=left + box.x1 * width, top=bottom + (1 - box.y0) * height,
                )
            finally:
                textpage.close()
        finally:
            page.close()
    if not text.strip():
        raise ValueError("Vùng này không có lớp chữ trích xuất được. Lưu PNG để OCR ở bước 4; không tạo TXT rỗng.")
    return text.replace("\r\n", "\n").replace("\r", "\n")
