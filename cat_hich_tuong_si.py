"""Mẫu chung: TV2 kiểm tra, không nhân đôi số cặp của nhóm."""
from ten_file import MA_TAC_PHAM, TEN_NGUON
from cong_cu.models import Book, Source
from cong_cu.cli import run

BOOK = Book(
    code=MA_TAC_PHAM["hich"], title="Hịch tướng sĩ — mẫu chung",
    sources=(Source("chung", TEN_NGUON["hich"], ((4, 6), (11, 26))),),
    first_work="hich_tuong_si", work_range=None,
    note="Mẫu chung do TV1 quản lý, TV2 kiểm tra; không tính thêm một bộ cặp. "
         "Dịch nghĩa PDF 4–6; Hán và dịch âm xen kẽ PDF 11–20; diễn thơ PDF 21–26. "
         "Không lấy tiếng Anh PDF 27–30. Chú thích riêng PDF 7–10 để đối chiếu.",
)

if __name__ == "__main__":
    run(BOOK)
