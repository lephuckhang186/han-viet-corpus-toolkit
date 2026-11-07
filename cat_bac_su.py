"""Bắc sứ: hai nguồn riêng, không giả định cùng số trang là bản dịch tương ứng."""
from ten_file import MA_TAC_PHAM, TEN_NGUON
from cong_cu.models import Book, Source
from cong_cu.cli import run

MOC_DOI_CHIEU = {"loi_tua": (9, 2), "loi_de_tu": (11, 4), "quyen_1": (13, 7), "quyen_4": (93, 55)}
BOOK = Book(
    code=MA_TAC_PHAM["bac_su"], title="Bắc sứ thông lục",
    sources=(
        Source("viet", TEN_NGUON["bac_su_viet"], ((39, 75),), "viet", "Mốc phân công nội dung theo bản Việt."),
        Source("han", TEN_NGUON["bac_su_han"], ((54, 106),), "han", "Chỉ chia kiểm kê nguồn, chưa ánh xạ với Việt 39–75."),
    ),
    first_work="doan0001", work_range=None,
    note="Đặt một mã cho từng đoạn độc lập đã xác định. Hán PDF 54–106 chỉ là phạm vi kiểm kê TV2; "
         "KHÔNG mặc định tương ứng Việt PDF 39–75. Dò quyển/đoạn trước khi dùng cùng mã tác phẩm. "
         "Các mốc bắt đầu Hán/Việt: lời tựa 9/2, đề từ 11/4, quyển 1 13/7, quyển 4 93/55.",
)

if __name__ == "__main__":
    run(BOOK)
