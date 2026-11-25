# Phương pháp Đối chứng Hai Kết quả OCR (`OCR_CROSS_CHECK.md`)

## 1. Định nghĩa bài toán
Đối chiếu kết quả từ hai bộ OCR độc lập (`PaddleOCR` vs `CLC OCR` cho Hán; `Tesseract` vs `VietOCR` cho Việt) để định vị chính xác chỗ sai khác ký tự, thiếu dòng hoặc đảo thứ tự đọc mà không làm thay đổi dữ liệu thô gốc.

## 2. Đầu vào và Đầu ra
- **Đầu vào**: Hai danh sách `list[OCRRecord]` (`primary` và `secondary`) cùng `source_id`.
- **Đầu ra**: `cross_check.json`, bảng CSV duyệt `cross_check_review.csv`, bản xem HTML bôi màu sai khác `cross_check_diff.html`, văn bản sau sửa `corrected_text.txt` và nhật ký `correction_log.jsonl`.

## 3. Đặc điểm dữ liệu
- Một engine có thể trả tọa độ polygon (`PaddleOCR`, `Tesseract` TSV) trong khi engine kia chỉ trả danh sách dòng (`CLC OCR` khi `result_bbox=[]`) hoặc có độ chi tiết khác nhau (toàn trang vs từng dòng).
- Chữ Việt giữa các bộ OCR có thể khác chuẩn Unicode NFC vs NFD.

## 4. Phương pháp luận
1. Ghép cặp vùng theo thứ tự ưu tiên: độ chồng lấp hình học (`bbox_iou >= 0.3`), sau đó `(source_id, region_id)`, cuối cùng là `reading_order`. Nếu một bên chỉ trả toàn trang còn bên kia trả từng dòng mà không có bbox dòng, đánh dấu `NEEDS_REVIEW`, không ghép cưỡng ép.
2. Tạo bản sao chuẩn hóa Unicode NFC để so sánh (giữ nguyên chuỗi gốc trong record).
3. Căn chỉnh Levenshtein cấp ký tự (Hán) và cấp ký tự + từ (Việt).

## 5. Thuật toán
Hàm `levenshtein_align(seq_a, seq_b)` tính khoảng cách chỉnh sửa tối ưu và truy vết các thao tác `equal`, `substitution`, `insertion`, `deletion`:
- Hán: tách theo code point Unicode NFC (hỗ trợ CJK Extension B+ và giữ `[MASK]` nguyên cụm).
- Việt: đối chiếu dạng bỏ dấu (`_strip_viet_diacritics`) để tách riêng nhãn `tone_mismatch` (bất đồng dấu thanh) và biểu thức số/La Mã để phát hiện `number_or_era_mismatch`.

## 6. Triển khai mã nguồn
- `src/hanviet/extraction/cross_check/aligner.py` (`cross_check_records`, `compare_han_texts`, `compare_viet_texts`, `bbox_iou`, `levenshtein_align`).
- `src/hanviet/extraction/manual_review/reviewer.py` (`build_ocr_review_table`, `render_ocr_diff_html`, `apply_manual_ocr_decisions`).
- CLI độc lập: `scripts/run_ocr_cross_check.py`.

## 7. Kiểm tra thủ công
Người dùng đối chiếu ảnh nguồn với điểm bất đồng bôi màu và chọn một trong 7 quyết định: `ACCEPT_PRIMARY`, `ACCEPT_SECONDARY`, `MANUAL_EDIT`, `INSERT_MASK`, `FIX_READING_ORDER`, `REPROCESS`, `DEFER`. Nếu thiếu kết quả từ một engine, hệ thống ghi rõ `CROSS_CHECK_INCOMPLETE`.

## 8. Chỉ số đánh giá
Tách biệt hoàn toàn: `model_agreed_unverified`, `model_disagreements`, `incomplete_cross_check_regions`, `human_confirmed_errors`, `human_manually_fixed`, `human_deferred`.

## 9. Phân tích lỗi
Các bất đồng điển hình: chữ Hán tự dạng gần giống, sót vùng chữ mờ (`MISSING_REGION`), nhầm dấu thanh Việt (`người` vs `ngưởi`), đảo thứ tự cột dọc (`reading_order_mismatch`).

## 10. Hạn chế
Hai engine ra kết quả giống nhau (`AGREED_UNVERIFIED`) **không phải bằng chứng tuyệt đối** rằng văn bản đã đúng 100%, vì cả hai mô hình vẫn có thể mắc cùng một lỗi hệ thống trên bản in mờ.

## 11. Khả năng tái lập thực nghiệm
Các ngưỡng IoU và quy tắc so sánh được cấu hình cố định tại `configs/methods/ocr.yaml`.
