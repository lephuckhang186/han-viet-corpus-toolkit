# Báo cáo Triển khai OCR Hán — Cross-Check & Manual Fixing

Tài liệu báo cáo đầy đủ 21 hạng mục cho yêu cầu triển khai mô-đun **Dual-engine Han OCR Cross-check with Human-in-the-loop Correction**.

---

## 1. Đánh giá Repository (Repository Assessment)
- Đã kiểm toán mã nguồn hiện có trên nhánh `refactor/modular-toolkit-vi-docs` (phân hệ `src/hanviet/extraction/`, `src/hanviet/evaluation/`, `cong_cu/clc_ocr.py`, `notebooks/ocr_nlp.ipynb`, `configs/methods/ocr.yaml`, `TaiLieuAPI_HanNom_CLC.pdf`).
- Giữ nguyên toàn bộ logic được bảo vệ (`source_preparation`, `clean_han`, `clean_viet`, `segmentation`, `alignment` Lab/CLC, `exporters`).

## 2. Thành phần OCR hiện có được tái sử dụng
- Toàn bộ tiền xử lý ảnh Hán tại [han_preprocess.py](../../src/hanviet/extraction/preprocessing/han_preprocess.py): `bac_su_preprocess` (`gray_only`, `soft_gray`, `binary_otsu`, mặt nạ khử đỏ), `horizontal_han_rows`, `grouped_vertical_columns`, `text_order`, `HAN_IMAGE_OVERRIDES`.
- Bộ điều phối tỉ lệ/cửa sổ Việt tại [viet_preprocess.py](../../src/hanviet/extraction/preprocessing/viet_preprocess.py) (giữ nguyên cho `OCR_viet.ipynb`).
- Toàn bộ cell OCR Việt/Hán ban đầu trong [OCR_viet.ipynb](../../notebooks/02_ocr/OCR_viet.ipynb) (được di chuyển từ `notebooks/ocr_nlp.ipynb`).
- Hợp đồng CLC Web OCR API đã kiểm chứng từ `TaiLieuAPI_HanNom_CLC.pdf` (`image-upload` + `image-ocr`) và cơ chế rate limit SQLite từ `clc_aligner.reserve_clc_request`.

## 3. Các file được tạo mới
- [notebooks/02_ocr/OCR_han.ipynb](../../notebooks/02_ocr/OCR_han.ipynb): Notebook 19 mục, 9 chế độ chạy độc lập cho OCR Hán.
- [notebooks/02_ocr/README.md](../../notebooks/02_ocr/README.md): Tài liệu 15 mục tiếng Việt cho OCR Hán.
- [src/hanviet/extraction/cross_check/normalization.py](../../src/hanviet/extraction/cross_check/normalization.py): Chuẩn hóa bản sao `strict`/`content` có ánh xạ offset và bảo toàn `[MASK]` + Variation Selectors.
- [src/hanviet/extraction/cross_check/matcher.py](../../src/hanviet/extraction/cross_check/matcher.py): Khớp phân cấp, IoU/overlap/center distance, kiểm tra reading order, DP khớp dòng/nhóm dòng (`1-1`, `1-n`, `n-1`, skip) và phát hiện vùng trùng lặp.
- [src/hanviet/extraction/exporter.py](../../src/hanviet/extraction/exporter.py): Quản lý cấu trúc thư mục 6 lớp và projection exporter tương thích 100% với Stage 03 Text Cleaning.
- [tests/test_han_ocr_pipeline.py](../../tests/test_han_ocr_pipeline.py): Bộ kiểm thử tự động toàn diện cho chuẩn hóa, 15 trường hợp dóng ký tự, DP matching, CLC retry/401/429/cache/import, safe correction applier, evaluation và tương thích Stage 03 cleaning.
- `docs/refactoring/HAN_OCR_IMPLEMENTATION.md`: Báo cáo triển khai này.

## 4. Các file được cập nhật
- [src/hanviet/extraction/schema.py](../../src/hanviet/extraction/schema.py)
- [src/hanviet/extraction/engines/paddle_han.py](../../src/hanviet/extraction/engines/paddle_han.py)
- [src/hanviet/extraction/engines/clc_han.py](../../src/hanviet/extraction/engines/clc_han.py)
- [src/hanviet/extraction/cross_check/aligner.py](../../src/hanviet/extraction/cross_check/aligner.py) & [\_\_init\_\_.py](../../src/hanviet/extraction/cross_check/__init__.py)
- [src/hanviet/extraction/manual_review/reviewer.py](../../src/hanviet/extraction/manual_review/reviewer.py) & [\_\_init\_\_.py](../../src/hanviet/extraction/manual_review/__init__.py)
- [src/hanviet/evaluation/metrics.py](../../src/hanviet/evaluation/metrics.py)
- [scripts/run_ocr_cross_check.py](../../scripts/run_ocr_cross_check.py)
- [README.md](../../README.md) & [notebooks/README.md](../../notebooks/README.md)

## 5. Các file được di chuyển / đổi tên
- `notebooks/ocr_nlp.ipynb` → [notebooks/02_ocr/OCR_viet.ipynb](../../notebooks/02_ocr/OCR_viet.ipynb)
- `notebooks/02_ocr/02_dual_ocr_and_cross_check.ipynb` → [notebooks/02_ocr/OCR_han.ipynb](../../notebooks/02_ocr/OCR_han.ipynb)

## 6. Triển khai PaddleOCR
- `PaddleHanEngine` giữ nguyên `PP-OCRv6_medium_det`/`rec`, `horizontal_han_rows`, `vertical_rtl`, `top_to_bottom`, hỗ trợ `order_indices`, `row_settings`, `manual_boxes`, `bac_su_preprocess` (`soft_gray`/`binary_otsu`/`gray_only`) kèm ghi nhận cả `original_image_sha256` và `processed_image_sha256`.

## 7. Trạng thái tích hợp CLC OCR
- **API Endpoint đã xác minh** từ `TaiLieuAPI_HanNom_CLC.pdf`: `image-upload` + `image-ocr` (chặn tuyệt đối `/sentence-alignment`).
- **Đã triển khai**: Retry với `Retry-After` cho HTTP `429`, exponential backoff cho `5xx`/timeout, dừng ngay HTTP `401`/`403`, cache theo `sha256 + service + options + model_version + parser_version`, lưu cache không chứa token, trạng thái `API_NOT_CONFIGURED` khi thiếu khóa và chế độ `import_clc_ocr_json` / `import_clc_ocr_text` yêu cầu ánh xạ tường minh.
- **Giới hạn kiểm chứng live**: Chưa gọi HTTP thật tới server CLC trong bài kiểm thử tự động và trong môi trường không có token/mạng ngoài sandbox; toàn bộ luồng upload/retry/401/429/cache được kiểm chứng qua `unittest` với `MagicMock` session và JSON fixture.

## 8. Triển khai Region Matching
- Thực thi giới hạn phạm vi theo `(corpus_id, work_id, source_id, pdf_page)` ở cả bộ khớp tiêu chuẩn và DP line matcher (`scope_key`), tránh rò rỉ hoặc ghép nhầm giữa hai tác phẩm/trang.
- Kết hợp `bbox_iou`, `bbox_overlap_ratio` và `bbox_center_distance` khi cả hai engine đều có bbox cùng hệ tọa độ.

## 9. Triển khai Line Matching
- `match_lines_dp` hỗ trợ `1-1`, `1-n`, `n-1`, `primary_only`, `secondary_only` (giới hạn `max_group_size=3`) với hàm chi phí cấu hình `(alpha, beta, gamma, delta)`. Khi thiếu tọa độ bbox từ CLC OCR, trọng số tự chuẩn hóa bỏ qua thành phần hình học mà không bịa tọa độ giả.

## 10. Triển khai Character Alignment
- `compare_han_texts` dùng DP Levenshtein chuẩn (`sub=1, ins=1, del=1`) trên bản sao đã tách unit thông qua `tokenize_han_with_spans`, bảo toàn `[MASK]`, variation selectors và ký tự mở rộng CJK Ext B+, đồng thời ánh xạ ngược chính xác span `unicode_codepoint_original` (start-inclusive, end-exclusive) cho cả profile `strict` và `content`.

## 11. Phát hiện & Phân loại Bất đồng (Disagreement Detection)
- `extract_han_disagreements` sinh đầy đủ các trường Task 09 với đủ 16 mã lỗi (`CHARACTER_MISMATCH` .. `CROSS_CHECK_INCOMPLETE`) và phân cấp `CRITICAL`, `HIGH`, `MEDIUM`, `LOW`, phát hiện `DUPLICATE_REGION`, `READING_ORDER_MISMATCH`, `LOW_CONFIDENCE`, `RARE_CHARACTER_MISMATCH`, `NUMBER_MISMATCH`. Không bao giờ gán `APPROVED` cho `AGREED_UNVERIFIED`.

## 12. Chức năng Manual Fixing
- `reviewer.py` xuất `review_queue.csv`, `comparison.xlsx`, `unmatched_regions.xlsx`, `diff_report.html` (hiển thị nhãn `[SUB:...]`, `[INS:...]`, `[DEL:...]` cùng màu nền) và overlay PNG `render_region_overlay_png`.
- Hỗ trợ đủ 9 quyết định (`ACCEPT_PRIMARY`, `ACCEPT_SECONDARY`, `KEEP_BOTH_AGREED`, `MANUAL_EDIT`, `INSERT_MASK`, `FIX_READING_ORDER`, `REPROCESS`, `REQUEST_SOURCE_REVIEW`, `DEFER`), bảo vệ chống stale fingerprint, chống trùng lặp `item_id`, cấm ghi đè `paddle_ocr/`/`clc_ocr/` thô và cấm ghi đè bản đã `APPROVED`.

## 13. Cấu trúc thư mục đầu ra
- Tuân thủ 6 nhánh tách biệt dưới `02_ocr_tho/han/`: `paddle_ocr/`, `clc_ocr/`, `cross_check/`, `manual_review/`, `corrected/`, `evaluation/`.

## 14. Tương thích Text Cleaning (Stage 03)
- `export_cleaning_compatible_han_transcription` tạo thư mục `cleaning_projection/` chứa duy nhất bản chép đã duyệt theo đúng hợp đồng `<BookFolder>/02_ocr_tho/han/<work_stem>/phan*.txt` + `<work_stem>_ocr_tho.txt` + `.meta.json` + `ghep_theo_tac_pham.json`.
- Đã kiểm thử tích hợp thực tế bằng cách gọi thẳng `hanviet.cleaning.pipeline.read_sources`, `attach_review_pages` và `build_records` mà không sửa một dòng nào của code làm sạch.

## 15. Cải thiện Đa nền tảng (Cross-platform)
- Tất cả đường dẫn dùng `pathlib.Path` + `resolve_paths()` (hỗ trợ đường dẫn tiếng Việt, khoảng trắng, Windows, Linux, Kaggle, Colab); tự rơi về CPU khi cross-check/manual review; không tải model lúc import.

## 16. Kết quả Kiểm thử tự động
- Lệnh đã chạy: `.\.venv\Scripts\python.exe -m unittest discover -s tests -v` → **31 tests ran — 31 OK** (`9.829s`, 0 failures, 0 errors). Xem bảng phân tách chi tiết trong [REGRESSION_RESULTS.md](REGRESSION_RESULTS.md).

## 17. Kết quả Smoke Test
- Notebook `OCR_han.ipynb` & `OCR_viet.ipynb` đã kiểm tra cấu trúc JSON `nbformat 4.5`; CLI `scripts/run_ocr_cross_check.py --help` (hỗ trợ `--dp-line-match`) và các CLI khác được kiểm chứng thoát mã `0`.

## 18. Cách chạy từng Mode trong `OCR_han.ipynb`
Mở [OCR_han.ipynb](../../notebooks/02_ocr/OCR_han.ipynb), chỉnh `CORPUS_ID`, `MEMBER_ID`, `MAX_IMAGES`, đặt biến `MODE` và chạy các cell liên quan:
- `preprocess`: tạo ảnh đã tiền xử lý Bắc sứ tại `paddle_ocr/visualization/preprocessed/`.
- `paddle_ocr`: chạy suy luận PaddleOCR (cần `requirements/ocr.txt`) và lưu vào `paddle_ocr/`.
- `clc_ocr`: đọc cache CLC hoặc gọi API khi đặt `CALL_CLC_API = True` + có `CLC_OCR_API_KEY`.
- `import_clc`: nạp file JSON/TXT xuất từ công cụ CLC theo bảng `CLC_IMPORT_MAPPING`.
- `cross_check`: chạy khớp vùng + DP line matching + Levenshtein trên dữ liệu đã lưu và xuất `cross_check/`.
- `review`: tạo `manual_review/review_queue.csv` và hiển thị HTML/DataFrame.
- `apply_corrections`: đọc CSV đã hiệu đính, kiểm tra an toàn và xuất `corrected/` + `correction_log.jsonl`.
- `evaluate`: tính đồng thuận, coverage, manual metrics, CER (nếu có gold) và bảng `H01`–`H06`.
- `export`: xuất projection tương thích Stage 03 vào `corrected/cleaning_projection/` (yêu cầu `approved=True` hoặc bật xuất nháp).

## 19. Điểm nghẽn còn lại (Remaining Blockers)
- Môi trường `.venv` Windows cục bộ hiện chưa cài `paddleocr`, `paddlex`, `transformers`, `torch`, do đó **suy luận GPU PaddleOCR thật** trên `OCR_han.ipynb` cần chạy trên Kaggle/Colab hoặc máy có cài `requirements/ocr.txt`.
- Chưa thực hiện phiên gọi mạng trực tiếp tới server `kimhannom.fit.hcmus.edu.vn` từ bộ test tự động.

## 20. Giới hạn đã biết (Known Limitations)
- Xem chi tiết mục 15 trong [notebooks/02_ocr/README.md](../../notebooks/02_ocr/README.md): đồng thuận giữa hai OCR (`AGREED_UNVERIFIED`) không phải ground truth, CLC `image-ocr` không cung cấp confidence và đôi khi thiếu bbox chi tiết từng ký tự/dòng, nên Manual Fixing vẫn là bước bắt buộc.

## 21. Các quyết định cần xác nhận từ người dùng
1. Xác nhận giữ hai tên notebook chuẩn hóa là `notebooks/02_ocr/OCR_viet.ipynb` và `notebooks/02_ocr/OCR_han.ipynb` (thay cho `ocr_nlp.ipynb` và `02_dual_ocr_and_cross_check.ipynb`).
2. Khi chạy thực nghiệm `H01`–`H06`, cung cấp tập `gold_samples` chuẩn đã kiểm duyệt thủ công để tính `CER` và `False Agreement Rate` thực tế trên từng bộ sách (`CPO_09`, `CPO_11`, `CPO_12`).
