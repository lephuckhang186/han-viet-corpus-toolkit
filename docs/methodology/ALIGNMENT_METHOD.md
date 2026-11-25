# Phương pháp Tách câu và Dóng hàng (`ALIGNMENT_METHOD.md`)

## 1. Định nghĩa bài toán
Từ bộ TXT sạch đã duyệt của mỗi tác phẩm (gồm tối đa 4 phiên bản: `Hán`, `Dịch âm`, `Dịch nghĩa`, `Dịch thơ`), tách đơn vị câu/dòng và dóng hàng thành bảng song ngữ 4 cột đúng thứ tự nguồn, không chồng lấp.

## 2. Đầu vào và Đầu ra
- **Đầu vào**: Các file TXT sạch trong `03_text_sach/{han,viet}/`.
- **Đầu ra**: Hồ sơ duyệt (`draft.json`, `review_template.json`, `clc_request.json`, `clc_response.json`, `poetry_prompt.json`) và sau khi duyệt `review.json` (`approved: true`), xuất ra `*_parallel.tsv`, `*_parallel.xlsx` (4 cột) kèm `notes.xlsx` trong `04_dong_hang/`.

## 3. Đặc điểm dữ liệu
- Văn xuôi/văn sách dùng dấu câu (`split_prose`); thơ dùng ngắt dòng (`poetry`) hoặc chế độ giữ dòng (`keep_lines=True` cho Bắc Sứ Hán).
- `Dịch âm` tương ứng chặt theo âm tiết với chữ `Hán`, trong khi `Dịch nghĩa` và `Dịch thơ` thường gộp/tách câu hoặc đảo cấu trúc diễn đạt.

## 4. Phương pháp luận
- **Tách đơn vị**: `segment()` giữ chính xác offset UTF-8 (`start`, `end`) và số phần trang (`part` theo `\f`).
- **Hán – Dịch âm**: Quy hoạch động theo độ dài ký tự/âm tiết (`phonetic_links`) kết hợp đối chiếu Levenshtein của Lab (`run_lab`) với hai từ điển Hán–Nôm/Quốc ngữ.
- **Hán – Dịch nghĩa**: Gọi endpoint `sentence-alignment` của Kim Hán Nôm CLC (`align_clc`) và khôi phục khoảng liên tục duy nhất (`clc_span`). Các backend Bertalign/Vecalign được giữ nguyên code nhưng tắt ở luồng mặc định.
- **Hán – Dịch thơ**: Sinh `poetry_prompt.json` để hỗ trợ ghép thơ (`poetry_result.json`).

## 5. Thuật toán
Các thuật toán được bảo toàn 100% tại `src/hanviet/segmentation/segmenter.py`, `src/hanviet/alignment/backends/` và `src/hanviet/alignment/validation/validators.py` (`phonetic_links` DP, `validate_links` kiểm tra đơn điệu không trùng, `make_rows` gộp khoảng giao nhau theo trục Hán).

## 6. Triển khai mã nguồn
- `src/hanviet/segmentation/segmenter.py`
- `src/hanviet/alignment/{runner,notebook_helpers,bac_su,thi_dinh}.py`
- `src/hanviet/alignment/backends/{lab_aligner,clc_aligner,embedding_aligners}.py`
- `src/hanviet/exporters/tabular.py`.

## 7. Kiểm tra thủ công
Thành viên đối chiếu `draft.json`, `clc_mismatch.json`, `notes.xlsx`, điền lý do vào `skipped` cho mọi ID chưa dóng rồi mới bật `"approved": true` trong `review.json` trước khi xuất.

## 8. Chỉ số đánh giá
Thống kê số hàng đã dóng, số đơn vị còn sót theo từng cột, số cảnh báo Lab và các chỉ số Precision/Recall/F1 (chỉ tính khi có tập chuẩn).

## 9. Phân tích lỗi
Các vấn đề hay gặp: `CLCTextMismatch` khi API tự tách lại hoặc mất khoảng trắng, ngắt câu sai do nhiễu dấu chấm OCR, hoặc khoảng giao nhau làm gộp câu ở `make_rows`.

## 10. Hạn chế
Yêu cầu khớp SHA-256 `fingerprint` giữa TXT nguồn, `draft.json` và `review.json` mới cho phép xuất nộp.

## 11. Khả năng tái lập thực nghiệm
Thuật toán tách câu và dóng hàng được khóa hành vi bằng golden fixture `tests/fixtures/baseline/alignment_baseline.json`.
