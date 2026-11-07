"""TV2: văn sách bài 14–18; ranh giới từng phần phải kiểm tra trực quan."""
from ten_file import MA_TAC_PHAM, TEN_NGUON
from cong_cu.models import Book, Source
from cong_cu.cli import run

# Chỉ là mốc bắt đầu đã kiểm tra từ mục lục, không suy ra mọi trang đều hợp lệ.
MOC_BAI = {
    14: {"trang": (188, 220), "dich_nghia": 197, "han": 210},
    15: {"trang": (221, 253), "dich_nghia": 229, "han": 244},
    16: {"trang": (254, 300), "dich_nghia": 266, "han": 285},
    17: {"trang": (301, 333), "dich_nghia": 309, "han": 324},
    18: {"trang": (334, 365), "dich_nghia": 343, "han": 356},
}
BOOK = Book(
    code=MA_TAC_PHAM["van_sach"], title="Văn sách thi Đình Thăng Long–Hà Nội, tập 2",
    sources=(Source("chung", TEN_NGUON["van_sach"], ((188, 365),)),),
    first_work="bai0014", work_range=(14, 18),
    note="TV2: bài 14–18 / PDF 188–365. Bài 14: dịch nghĩa bắt đầu 197, Hán bắt đầu 210; "
         "bài 15: 229/244; bài 16: 266/285; bài 17: 309/324; bài 18: 343/356. "
         "Gom từng bài, không coi toàn bộ khoảng trang là một loại văn bản.",
)

if __name__ == "__main__":
    run(BOOK)
