# Hướng dẫn OCR Hán — Kiểm tra chéo hai động cơ & Hiệu đính thủ công

Tài liệu dành riêng cho mô-đun OCR Hán (`OCR_han.ipynb` và `hanviet.extraction`) trong kho mã nguồn `han-viet-corpus-toolkit`. Notebook OCR tiếng Việt được tách riêng tại [OCR_viet.ipynb](OCR_viet.ipynb).

---

## 1. Overview

Văn bản Hán cổ (Hán văn, Hán Nôm, bản khắc gỗ/viết tay/bản scan nhiều cột hoặc nhiều dòng ngang) thường gặp các lỗi nhận dạng ký tự gần hình (`土/士`, `常/裳`, `未/末`), bỏ sót ký tự, nhầm thứ tự cột đọc hoặc nhiễu nền/dấu triện đỏ.

Mục tiêu của mô-đun OCR Hán là thực hiện phương pháp **Dual-engine Han OCR Cross-check with Human-in-the-loop Correction**:
- Sử dụng **PaddleOCR (`PP-OCRv6`)** làm engine chính và **Kim Hán Nôm (CLC OCR)** làm engine đối chiếu thứ cấp.
- Thực hiện kiểm tra chéo từ cấp vùng, kiểm tra thứ tự đọc, dóng dòng bằng Quy hoạch động (DP), dóng ký tự bằng khoảng cách Levenshtein và phân loại bất đồng.
- Trình bày trực quan cho thành viên kiểm tra trên ảnh gốc và thực hiện **Manual Fixing** trước khi bàn giao sang bước Làm sạch văn bản (Stage 03). Không bao giờ chọn kết quả thắng dựa trên confidence thô giữa hai engine.

---

## 2. Architecture

```text
Prepared Han Images (01_nguon/han/)
        |
Image Preprocessing (bac_su_preprocess: gray_scale / binary_otsu; bảo toàn tỉ lệ 1:1)
        |
        +------------------------------+
        |                              |
   PaddleOCR (Primary)            CLC OCR (Secondary / Manual Import)
        |                              |
  paddle_ocr/ (riêng biệt)       clc_ocr/ (riêng biệt)
        |                              |
        +--------------+---------------+
                       |
       OCR Result Normalization (strict & content profiles, giữ nguyên raw)
                       |
       Region Matching (Corpus -> Work -> Source -> PDF Page -> Region)
                       |
       Reading Order Validation (vertical_rtl / horizontal_ltr / top_to_bottom)
                       |
       Line Matching (DP 1-1, 1-n, n-1, skip với chi phí cấu hình)
                       |
       Character-level Levenshtein Alignment & Disagreement Classification
                       |
       Comparison Visualization (HTML / DataFrame / XLSX / Image BBox Overlay)
                       |
       Manual Fixing (review_queue.csv -> CorrectionApplier + correction_log.jsonl)
                       |
       Reviewed Transcription (corrected/) -> Tương thích Stage 03 Text Cleaning
```

---

## 3. Supported Documents

| Mã sách | Tài liệu | Đặc điểm nguồn & Yêu cầu xử lý |
|---|---|---|
| `CPO_09` | Bắc Sứ Thông Lục | PDF scan cổ, chủ yếu cột dọc phải→trái (`vertical_rtl`), có dấu triện đỏ, nhiễu nền và nhiều chữ Hán hiếm. Giữ nguyên tiền xử lý khử đỏ (`soft_gray` / `binary_otsu`), không xóa ký tự confidence thấp. |
| `CPO_11` | Văn Sách Thi Đình | PDF scan các bài văn dài, nhiều cột/vùng trên trang (`vertical_rtl`). Giữ chặt phạm vi từng bài, phát hiện vùng bị thiếu hoặc lặp. |
| `CPO_12` | Thơ Văn Lý–Trần | Nhiều tác phẩm nhỏ, thơ và văn xuôi hàng ngang (`horizontal_ltr`). Giữ nguyên `horizontal_han_rows`, ngoại lệ hình học `HAN_IMAGE_OVERRIDES`, ranh giới dòng thơ và thứ tự từng phần. |
| `CPO_10` | Hịch Tướng Sĩ | Nếu nguồn đã có lớp text PDF hoặc TXT thuần (`01_nguon`), dùng trích xuất text trực tiếp và **không** tạo request OCR không cần thiết. |

---

## 4. Environment Setup

Hỗ trợ Windows, Linux, Kaggle và Google Colab thông qua `hanviet.common.paths` (`resolve_paths`, `detect_runtime`, `resolve_device`).

- **Môi trường cơ bản (chạy cross-check, manual fixing, evaluation bằng CPU)**:
  ```powershell
  .\.venv\Scripts\python.exe -m pip install -r requirements\base.txt
  ```
- **Môi trường suy luận GPU / OCR thực tế (PaddleOCR, Transformers, PyTesseract, VietOCR)**:
  ```powershell
  .\.venv\Scripts\python.exe -m pip install -r requirements\ocr.txt
  ```
- **Chẩn đoán & kiểm tra trên CPU**: Các bước `cross_check`, `review`, `apply_corrections`, `evaluate` và `export` chạy hoàn toàn trên CPU và **không** tải model khi chỉ import module `hanviet`.

---

## 5. Configuration

Trong [OCR_han.ipynb](OCR_han.ipynb) (mục `03. Configuration`), chỉnh các biến:
- `CORPUS_ID`: `"CPO_09"`, `"CPO_10"`, `"CPO_11"`, hoặc `"CPO_12"`.
- `MEMBER_ID`: `"TV02"` hoặc `"TV04"`.
- `SELECTED_WORKS`, `SELECTED_PAGES`: giới hạn bài/trang cần xử lý (rỗng `[]` = lấy toàn bộ).
- `DEVICE`: `"auto"`, `"cpu"`, `"gpu:0"`.
- `INPUT_ROOT`, `OUTPUT_ROOT`: đặt `None` để tự phân giải đa nền tảng qua `configs/project.yaml` và biến `.env` (`HANVIET_DATA_ROOT`, `HANVIET_OUTPUT_ROOT`).
- `MAX_IMAGES`: mặc định `3` để kiểm tra an toàn; đặt `None` khi chạy hàng loạt.
- `CALL_CLC_API`: mặc định `False` để tránh gửi request ngoài ý muốn khi `Run All`.
- `EXPORT_APPROVED`: mặc định `False` (chỉ cho phép xuất chính thức khi đã duyệt).
- **9 `MODE` chạy độc lập**: `preprocess`, `paddle_ocr`, `clc_ocr`, `import_clc`, `cross_check`, `review`, `apply_corrections`, `evaluate`, `export`.

---

## 6. PaddleOCR

Adapter tại `hanviet.extraction.engines.paddle_han.PaddleHanEngine` bảo toàn cấu hình và xử lý hiện tại:
- Mô hình mặc định: `PP-OCRv6_medium_det` + `PP-OCRv6_medium_rec` (`engine="transformers"`, `batch_size=1`, `rec_score_threshold=0.0`).
- Hỗ trợ tiền xử lý Bắc sứ (`bac_su_preprocess`: `gray_only`, `soft_gray`, `binary_otsu`) với hệ tọa độ giữ nguyên 1:1.
- Hỗ trợ tách hàng ngang `horizontal_han_rows` cho Lý–Trần và `HAN_IMAGE_OVERRIDES` (`order_indices`, `row_settings`, `manual_boxes`, `column_center_ratio`).
- Lưu kết quả thô độc lập vào `paddle_ocr/{text,metadata,visualization,manifest.json}` và giữ SHA-256 của cả ảnh gốc lẫn ảnh đã tiền xử lý.

---

## 7. CLC OCR

Adapter tại `hanviet.extraction.engines.clc_han.CLCOCRAdapter`:
- **API Endpoint đã xác minh** từ `TaiLieuAPI_HanNom_CLC.pdf`:
  - Upload ảnh: `POST https://kimhannom.fit.hcmus.edu.vn/api/web/clc-sinonom/image-upload`
  - Nhận dạng Hán/Nôm: `POST https://kimhannom.fit.hcmus.edu.vn/api/web/clc-sinonom/image-ocr`
  - Khác hoàn toàn endpoint dóng hàng `/sentence-alignment` (adapter chủ động chặn nếu URL chứa `sentence-alignment`).
- **Biến môi trường**: `CLC_OCR_API_KEY` (từ `.env` hoặc `.env.clc_ocr`), `CLC_OCR_API_URL`, `CLC_OCR_TIMEOUT`, `CLC_OCR_MAX_RETRIES`.
- **Xử lý lỗi & Cache**: Tôn trọng `Retry-After` với HTTP `429`, exponential backoff với timeout/`5xx`, fail-fast với HTTP `401`/`403`, rate limit log vào SQLite, cache không chứa token gắn chặt theo `sha256 + service + options + model_version + parser_version`.
- **Import thủ công offline (`MODE = "import_clc"`)**: Hàm `import_clc_ocr_json` và `import_clc_ocr_text` yêu cầu truyền tường minh `source_id`, `work_id`, `pdf_page` (không ghép bừa theo tên file), gán trạng thái `IMPORTED` / `MANUAL_IMPORT`. Nếu thiếu token, adapter trả `API_NOT_CONFIGURED`.

---

## 8. Cross-check Methodology

1. **Normalization (`normalization.py`)**: Thực hiện **chỉ trên bản sao so sánh**, giữ nguyên `raw` và bảo toàn chữ phồn thể / Extension B+ / dị thể tự / `[MASK]` / variation selectors (`U+FE00..U+FE0F`, `U+E0100..U+E01EF`). Hỗ trợ hai profile:
   - `strict`: chuẩn hóa NFC + xuống dòng, giữ dấu câu và khoảng trắng.
   - `content`: chuẩn hóa NFC + gộp khoảng trắng kỹ thuật + quy đổi dấu câu tương đương nếu cấu hình.
2. **Region Matching (`matcher.py`, `aligner.py`)**: Khớp phân cấp theo đúng `(corpus_id, work_id, source_id, pdf_page)` dùng `bbox_iou`, `bbox_overlap_ratio` và khoảng cách tâm; không để vùng khác tác phẩm/trang ghép chéo nhau.
3. **Reading Order Validation**: Phát hiện đảo thứ tự đọc (`READING_ORDER_MISMATCH`) và cảnh báo mà không âm thầm đảo chuỗi ký tự.
4. **DP Line / Grouped-Line Matching (`match_lines_dp`)**: Hỗ trợ `1-1`, `1-n`, `n-1` và bỏ qua với hàm chi phí `alpha * text_distance + beta * geometry_distance + gamma * length_difference + delta * grouping_penalty` (chỉ tính `geometry_distance` khi cả hai engine đều có bbox cùng hệ tọa độ).
5. **Character-level Levenshtein Alignment**: Truy vết từng phép toán `equal`, `substitution`, `insertion`, `deletion` kèm span code-point gốc chính xác.
6. **Disagreement Detection**: Phân loại đủ 16 nhãn lỗi (`CHARACTER_MISMATCH`, `CHARACTER_INSERTION`, `CHARACTER_DELETION`, `MISSING_LINE`, `EXTRA_LINE`, `MISSING_REGION`, `DUPLICATE_REGION`, `READING_ORDER_MISMATCH`, `PUNCTUATION_MISMATCH`, `WHITESPACE_MISMATCH`, `NUMBER_MISMATCH`, `RARE_CHARACTER_MISMATCH`, `UNREADABLE_CHARACTER`, `AMBIGUOUS_MATCH`, `LOW_CONFIDENCE`, `CROSS_CHECK_INCOMPLETE`) và mức ưu tiên (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`).

---

## 9. Manual Fixing

1. Mở `cross_check/comparison.xlsx`, `cross_check/diff_report.html` và ảnh gốc/overlay trong `paddle_ocr/visualization/`.
2. Chỉnh `manual_review/review_queue.csv` (hoặc lưu thành `review_decisions.csv`), chọn `decision`:
   - `ACCEPT_PRIMARY`, `ACCEPT_SECONDARY`, `KEEP_BOTH_AGREED`, `MANUAL_EDIT`, `INSERT_MASK`, `FIX_READING_ORDER`, `REPROCESS`, `REQUEST_SOURCE_REVIEW`, `DEFER`.
3. **Quy tắc `[MASK]`**: Chỉ sử dụng `[MASK]` khi thành viên tự đối chiếu ảnh và xác nhận `INSERT_MASK` / `MANUAL_EDIT`; công cụ **không bao giờ** tự chèn `[MASK]` khi hai engine bất đồng hay confidence thấp.
4. Chạy `MODE = "apply_corrections"` để kiểm tra fingerprint, không trùng lặp/chồng lấn, ghi `correction_log.jsonl`, và từ chối ghi đè dữ liệu OCR thô hay bản đã `APPROVED`.

---

## 10. Output Data

Cấu trúc chuẩn dưới `san_pham/<MEMBER>/<TOPIC>_<CORPUS>/02_ocr_tho/han/`:
- `paddle_ocr/{text,metadata,visualization,manifest.json}`: đầu ra PaddleOCR tách biệt.
- `clc_ocr/{text,metadata,requests,responses,manifest.json}`: đầu ra/cache CLC OCR tách biệt.
- `cross_check/{region_matches.jsonl,line_matches.jsonl,character_alignment.jsonl,disagreements.jsonl,comparison.xlsx,unmatched_regions.xlsx,diff_report.html,statistics.json}`.
- `manual_review/{review_queue.csv,review_decisions.csv,correction_log.jsonl,*_reviewed.json}`.
- `corrected/{parts,merged,cleaning_projection,manifest.json}`: bản chép đã hiệu đính.
- `evaluation/{gold_samples,metrics.json,figures}`.

---

## 11. Evaluation Metrics

`hanviet.evaluation.metrics.compute_han_ocr_evaluation` phân tách rõ:
- **Micro & Macro CER/WER**: Chỉ tính khi có `gold_references` do con người xác nhận; khi thiếu trả về `CER_NOT_AVAILABLE`.
- **Agreement Rate (`strict_mean` & `content_mean`)**: Đo độ nhất quán giữa PaddleOCR và CLC OCR, **không phải** độ chính xác OCR.
- **Coverage**: Số trang, số vùng từng engine, số vùng bất đồng/thiếu/chưa hoàn chỉnh.
- **Detection Precision / Recall & False Agreement Rate**: Đo tỷ lệ phát hiện đúng bất đồng và tỷ lệ `PaddleOCR == CLC OCR != gold` theo đơn vị vùng.
- **Manual Fixing Summary**: Thống kê theo từng loại quyết định, số `[MASK]`, tỷ lệ hoàn thành và thời gian duyệt.

---

## 12. Experimental Protocol

Khung 6 thực nghiệm chuẩn `H01`–`H06` (`experiment_matrix_template()`):
- `H01`: PaddleOCR trên ảnh gốc.
- `H02`: PaddleOCR kết hợp tiền xử lý (`soft_gray` / `binary_otsu`).
- `H03`: CLC OCR trên ảnh gốc.
- `H04`: CLC OCR trên ảnh tiền xử lý (nếu dịch vụ phù hợp).
- `H05`: Kiểm tra chéo PaddleOCR + CLC OCR.
- `H06`: Hiệu đính thủ công có hỗ trợ Cross-check.

Xây dựng tập gold sample độc lập trong `evaluation/gold_samples/` trước khi điền bảng kết quả báo cáo đồ án; không bao giờ tạo số liệu giả.

---

## 13. Text Cleaning Handoff

Khi đặt `MODE = "export"` (với `approved=True`), hàm `export_cleaning_compatible_han_transcription` tạo projection sạch tại `corrected/cleaning_projection/<BookFolder>/02_ocr_tho/han/<work_stem>/`:
- Chứa **duy nhất** bản văn đã hiệu đính (`phan*.txt`, `<work_stem>_ocr_tho.txt`, `.meta.json` và `05_quan_ly/ghep_theo_tac_pham.json`).
- **Không** đưa thư mục `paddle_ocr/` hay `clc_ocr/` thô vào projection để Stage 03 (`clean_text.ipynb` / `scripts/run_cleaning_stage.py`) không bao giờ đọc nhầm bản chưa duyệt.
- Chuyển tiếp sang Stage 03 chạy **thủ công** theo hướng dẫn tại [src/hanviet/cleaning/README.md](../../src/hanviet/cleaning/README.md).

---

## 14. Troubleshooting

| Vấn đề | Nguyên nhân & Cách xử lý |
|---|---|
| PaddleOCR không chạy | Chưa cài `requirements/ocr.txt` (`transformers==5.23.0`, `paddleocr`, `paddlex`) trên môi trường hiện tại. |
| CUDA lỗi / hết VRAM | Đổi `DEVICE = "cpu"` cho các bước cross-check/review hoặc giảm kích thước `detection_max_side` / khởi động lại phiên GPU sạch. |
| Thiếu model checkpoint | Bật kết nối Internet ở bước nạp model đầu tiên để HuggingFace/PaddleX tải vào cache. |
| CLC API timeout / HTTP 429 | Adapter tự thử lại theo `CLC_OCR_MAX_RETRIES` và `Retry-After`; nếu mạng chập chờn có thể giảm batch và dùng cache/import. |
| CLC authentication lỗi (HTTP 401/403) | Kiểm tra `CLC_OCR_API_KEY` trong `.env` / `.env.clc_ocr`; adapter dừng ngay không gửi lặp request lỗi. |
| Không match được region | Kiểm tra lại `work_id`, `source_id`, `pdf_page` có khớp cùng phạm vi hay đang lệch độ phân giải tọa độ. |
| Sai reading order | Xem cảnh báo `reading_order_mismatch`, dùng `order_indices` trong `HAN_IMAGE_OVERRIDES` hoặc sửa `reading_order_override` trong Manual Fixing. |
| OCR text rỗng | Kiểm tra ảnh crop đầu vào trong `01_nguon/` xem có bị cắt trượt hoặc ảnh quá mờ. |
| Unicode lỗi / mất dấu tổ hợp | Đảm bảo mở/lưu bằng UTF-8 (`utf-8-sig` cho CSV Excel) và giữ normalization `strict`/`content` của pipeline. |
| Output không tương thích Text Cleaning | Dùng hàm `export_cleaning_compatible_han_transcription` với `MODE = "export"` và trỏ `INPUT_PATH` về `corrected/cleaning_projection/`. |

---

## 15. Limitations

1. **Hai engine đồng thuận vẫn có thể cùng sai**: Các vùng `AGREED_UNVERIFIED` không tự động trở thành `APPROVED` mà vẫn cần kiểm tra chọn mẫu hoặc đối chiếu.
2. **Văn bản Hán cổ chứa nhiều chữ hiếm & dị thể tự**: Mô hình OCR hiện đại có thể nhận nhầm sang chữ phổ biến gần nét; tuyệt đối giữ nguyên chữ hiếm nếu model nhận ra đúng hoặc người duyệt sửa lại.
3. **Confidence không thể so sánh trực tiếp**: CLC OCR `image-ocr` không trả confidence và confidence của PaddleOCR không được hiệu chuẩn theo xác suất tuyệt đối.
4. **CLC có thể thiếu bounding box / metadata tọa độ**: Khi thiếu bbox, cross-check chuyển sang khớp theo vùng/thứ tự/DP text và ghi nhận đúng độ chi tiết, không vẽ box giả trên ảnh.
5. **Cross-check chỉ hỗ trợ định vị bất đồng**: Không thay thế chuyên gia đọc Hán Nôm.
6. **Manual Fixing là bước bắt buộc**: Bản văn sạch chỉ được xác nhận sau khi thành viên hoàn tất hiệu đính phạm vi được giao.
