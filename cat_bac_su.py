"""Bắc sứ: hai nguồn riêng, không giả định cùng số trang là bản dịch tương ứng."""
from ten_file import MA_TAC_PHAM, TEN_NGUON
from cong_cu.models import Book, Source
from cong_cu.cli import run

MOC_DOI_CHIEU = {"loi_tua": (9, 2), "loi_de_tu": (11, 4), "quyen_1": (13, 7), "quyen_4": (93, 55)}
BOOK = Book(
    code=MA_TAC_PHAM["bac_su"], title="Bắc sứ thông lục",
    sources=(
        Source("viet", TEN_NGUON["bac_su_viet"], ((32, 61),), "viet", "PDF Text, bàn giao TXT nguồn thô: bắt đầu sau mục 21 ở PDF 32; kết thúc đúng câu được giao tại PDF 61. Giữ chú thích và ký tự nguồn, chưa làm sạch."),
        Source("han", TEN_NGUON["bac_su_han"], ((49, 101),), "han", "Theo bảng mới phancong.md: PDF 49–101. PDF gốc giữ đủ trang; ảnh nộp bỏ PDF 57, 58, 63, 64, 71, 72, 79, 80, 91, 92 theo yêu cầu người dùng."),
    ),
    first_work="doan0001", work_range=None,
    note="Chuẩn bị nguồn TV2 theo phancong.md: Việt PDF Text 32–61 bàn giao TXT thô; Hán PDF 49–101 cắt ảnh vùng lớn. "
         "Việt 32 lấy sau mục 21; Việt 61 dừng sau câu để tôi thêm vui vẻ cảm kích. "
         "Không tách từng cột/đoạn, không dóng hàng, không mở rộng sang Hán 102. "
         "Giữ chung mã phần quyển qua các trang. 10 trang trắng/giấy đánh dấu chỉ giữ trong PDF gốc; bản Việt nộp TXT nguồn thô trong 01_nguon/viet/dich_nghia/, không OCR hoặc làm sạch. Ảnh Việt cũ chỉ để tra lại.",
)

if __name__ == "__main__":
    run(BOOK)
