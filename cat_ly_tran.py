"""TV2: cắt từng tác phẩm Lý–Trần 131–207, PDF 187–366."""
from ten_file import MA_TAC_PHAM, TEN_NGUON
from cong_cu.models import Book, Source
from cong_cu.cli import run

BOOK = Book(
    code=MA_TAC_PHAM["ly_tran"], title="Thơ văn Lý–Trần, tập 3",
    sources=(Source("chung", TEN_NGUON["ly_tran"], ((187, 366),)),),
    first_work="bai0131", work_range=(131, 207),
    note="TV2: bài 131–207. PDF 187 chứa cuối bài 130 của TV1 và đầu bài 131 của bạn. "
         "Chọn đúng bài; gom đủ Hán, dịch âm, dịch nghĩa, dịch thơ qua các trang. "
         "Bài 207: Hán ở PDF 365, dịch nghĩa ở PDF 366.",
)

if __name__ == "__main__":
    run(BOOK)
