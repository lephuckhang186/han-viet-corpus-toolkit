# Phương pháp Làm sạch Văn bản theo Luật (`TEXT_CLEANING.md`)

## 1. Định nghĩa bài toán
Chuẩn hóa khoảng trắng, dấu ngoặc rỗng, bảng mã Unicode và các ký hiệu phi nội dung rõ ràng trên bản OCR/PDF Text đã rà soát, đồng thời **bảo toàn tuyệt đối dị thể tự Hán Nôm, ký hiệu `[MASK]`, số liệu lịch sử, niên hiệu và văn phong gốc của bản dịch**.

## 2. Đầu vào và Đầu ra
- **Đầu vào**: TXT từng ảnh (`parts`) hoặc đã ghép (`_ocr_tho.txt`) trong `02_ocr_tho/`, cùng TXT PDF Text thô tại `01_nguon/` (Việt Bắc Sứ).
- **Đầu ra**: Bảng duyệt 22 cột `duyet_lam_sach.csv`, TXT sạch theo từng tác phẩm/phiên bản tại `03_text_sach/{han,viet}/`, `work_manifest.json`, `changes.jsonl` và `summary.json`.

## 3. Đặc điểm dữ liệu
- Chứa chữ Hán/Nôm hiếm ngoài BMP, dấu thanh tiếng Việt tách tổ hợp (NFD), ký tự lỗi font PDF cổ (`Ƣ`/`ƣ` $\rightarrow$ `Ư`/`ư`), chỉ mục chú thích `[1]`, `(1)`, ký hiệu tờ `[53b]` và dấu ngắt trang `\f`.

## 4. Phương pháp luận
- Không dùng stemming, stopword removal, chuyển phồn–giản hay xóa từ ngoài từ điển.
- Chỉ tự động áp dụng các quy tắc an toàn (`whitespace`, `empty_brackets`, `vietnamese_nfc`, `vietnamese_pdf_glyph`, `vietnamese_pdf_folio`, `standalone_version_label`); các trường hợp có rủi ro ngữ nghĩa đều chuyển thành cờ nghi vấn (`reasons`) để người dùng xác nhận qua CSV.

## 5. Thuật toán
Các hàm **protected logic** nằm trong `src/hanviet/cleaning/{han_cleaner,viet_cleaner,pipeline}.py`:
- `normalize_latin`: chuẩn hóa NFC trên từng chuỗi ký tự Latin kèm dấu tổ hợp.
- `clean_shared`: chuẩn hóa khoảng trắng, xóa `EMPTY_BRACKETS`, giữ nguyên `[MASK]`.
- `clean_han` & `clean_viet`: kiểm tra cờ nghi vấn Hán (`latin_in_han`, `han_symbol_check`) và Việt (`percent_check`, `possible_note_section`, `suffix_digit_suggestion`).
- `build_records`, `read_decisions`, `apply_decisions`, `assemble_works`: sinh `row_id` SHA-256, đối chiếu 5 cột bất biến và ghép trang `\f` / nối dòng `join_next`.

## 6. Triển khai mã nguồn
- `src/hanviet/cleaning/{han_cleaner,viet_cleaner,pipeline}.py`
- Hướng dẫn & prompt thủ công: `src/hanviet/cleaning/README.md` và `notebooks/clean_text.ipynb`.
- Kiểm thử hồi quy tại `tests/test_regression_protected_logic.py`.

## 7. Kiểm tra thủ công
Thành viên xem bảng `duyet_lam_sach.csv` kết hợp xem ảnh cắt theo `polygon` / `pdf_page` (mục 4.3 của notebook), rồi điền `action` hợp lệ (`keep`, `replace`, `delete`, `join_next`).

## 8. Chỉ số đánh giá
Thống kê số dòng được chỉnh tự động (`raw != clean`), số dòng gắn cờ nghi vấn (`reasons`), số từ `dich_am` ngoài từ điển tham khảo và số dòng chưa duyệt (`unresolved`).

## 9. Phân tích lỗi
Các đặc điểm biên của luật hiện tại (như `ƣ` ngoài `native_pdf=True` hay nối dòng `join_next` qua `\f`) được ghi nhận chi tiết tại [KNOWN_ISSUES.md](../refactoring/KNOWN_ISSUES.md).

## 10. Hạn chế
Biểu thức chính quy không tự phân biệt được số chú thích dính vào từ với số mang nghĩa lịch sử nếu không xét ngữ cảnh câu; do đó cần lớp kiểm tra thủ công hoặc hỗ trợ của LLM Prompt.

## 11. Khả năng tái lập thực nghiệm
Thuật toán làm sạch được giữ bất biến và kiểm chứng bằng golden fixture `tests/fixtures/baseline/cleaning_baseline.json`.
