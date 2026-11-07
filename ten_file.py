"""Tên và đường dẫn dùng chung. Không đặt thuật toán cắt trong file này."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
MA_DE_TAI = "CV06"  # Đổi thành mã đăng ký thật của nhóm khi đã xác nhận.
THANH_VIEN = 2
OUTPUT_ROOT = ROOT / "san_pham" / f"TV{THANH_VIEN:02d}"
DPI = 300

TEN_NGUON = {
    "ly_tran": DATA / "Nguyễn Huệ Chi (chủ biên) - Thơ văn Lý Trần 3.pdf",
    "van_sach": DATA / "Van_sach_thi_Dinh_Thang_Long_Ha_Noi_T2.pdf",
    "hich": DATA / "HichTuongSi_TranQuocTuan.pdf",
    "bac_su_han": DATA / "bắc sứ thông lục" / "BắcSứThôngLục_北使通錄(Q1_4).pdf",
    "bac_su_viet": DATA / "bắc sứ thông lục" / "Bắc Sứ Thông Lục.pdf",
}
MA_TAC_PHAM = {"bac_su": "CPO_09", "hich": "CPO_10", "van_sach": "CPO_11", "ly_tran": "CPO_12"}
CAC_BAN = {
    "han": ("Hán", Path("han")),
    "dich_am": ("Dịch âm", Path("viet") / "dich_am"),
    "dich_nghia": ("Dịch nghĩa", Path("viet") / "dich_nghia"),
    "dich_tho": ("Dịch thơ", Path("viet") / "dich_tho"),
}


def ten_tac_pham(ma_sach: str, tac_pham: str, ban: str, phien_ban: int) -> str:
    return f"{ma_sach}_TV{THANH_VIEN:02d}_{tac_pham}_{ban}_v{phien_ban:02d}"


def ten_vung(thu_tu: int, trang: int | None) -> str:
    moc = f"pdfp{trang:04d}" if trang is not None else "text"
    return f"phan{thu_tu:04d}_{moc}"
