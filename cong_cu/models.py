"""Kiểu dữ liệu và kiểm tra đầu vào, không đọc/ghi file."""
from dataclasses import dataclass
from pathlib import Path
import math
import re


@dataclass(frozen=True)
class Source:
    key: str
    path: Path
    ranges: tuple[tuple[int, int], ...]
    archive_side: str = "chung"
    note: str = ""

    def contains(self, page: int) -> bool:
        return any(start <= page <= end for start, end in self.ranges)


@dataclass(frozen=True)
class Book:
    code: str
    title: str
    sources: tuple[Source, ...]
    first_work: str
    work_range: tuple[int, int] | None
    note: str

    def source(self, key: str) -> Source:
        for source in self.sources:
            if source.key == key:
                return source
        raise ValueError(f"Không có nguồn {key!r}; chọn một trong {[s.key for s in self.sources]}")


@dataclass(frozen=True)
class Box:
    """Tọa độ tỷ lệ 0..1, gốc trên-trái: x0, y0, x1, y1."""
    x0: float
    y0: float
    x1: float
    y1: float

    def __post_init__(self):
        if not all(math.isfinite(v) for v in self.as_list()):
            raise ValueError("Tọa độ phải là số hữu hạn.")
        if not (0 <= self.x0 < self.x1 <= 1 and 0 <= self.y0 < self.y1 <= 1):
            raise ValueError("Vùng cắt cần 0 <= x0 < x1 <= 1 và 0 <= y0 < y1 <= 1.")

    def as_list(self) -> list[float]:
        return [self.x0, self.y0, self.x1, self.y1]


def validate_work(work: str) -> str:
    if not re.fullmatch(r"[a-z][a-z0-9_-]{0,79}", work):
        raise ValueError("Mã tác phẩm dùng chữ thường không dấu/số/_/-, ví dụ bai0131 hoặc doan0001.")
    return work


def validate_assignment(book: Book, work: str, source: Source, page: int, allow_outside: bool):
    validate_work(work)
    if page < 1:
        raise ValueError("Trang PDF bắt đầu từ 1.")
    if allow_outside:
        return
    if not source.contains(page):
        raise ValueError("Trang ngoài phạm vi TV2. Chỉ tra cứu bổ sung khi bật --allow-outside-scope.")
    if book.work_range:
        match = re.fullmatch(r"bai(\d+)", work)
        if not match or not book.work_range[0] <= int(match[1]) <= book.work_range[1]:
            raise ValueError(f"TV2 nhận bài {book.work_range[0]}–{book.work_range[1]} của sách này.")
