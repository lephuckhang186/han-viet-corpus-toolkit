# Từ điển Dữ liệu & Chuẩn Schema

## 1. Bản ghi OCR dùng chung (`schemas/ocr_record.schema.json`)
| Trường | Kiểu | Null | Mô tả |
|---|---|---|---|
| `record_id` | string | Không | Mã định danh SHA-256[:24] theo `(source_id, engine, region_id, reading_order)` |
| `source_id` | string | Không | Mã nguồn ảnh hoặc vùng cắt |
| `region_id` | string/int | Không | Chỉ số vùng/dòng của engine (tính từ 0) |
| `work_id`, `corpus_id`, `member_id` | string | Không | Ví dụ: `bai0024`, `CPO_11`, `TV04` |
| `variant` | enum | Không | `han`, `dich_am`, `dich_nghia`, `dich_tho` |
| `pdf_page`, `reading_order` | int | Có | Số trang PDF (từ 1) và thứ tự đọc |
| `engine`, `model_version` | string | Không | `paddleocr`, `clc_ocr`, `tesseract`, `vietocr` |
| `text` | string | Không | Văn bản thô chưa chuẩn hóa từ engine |
| `bbox` | array | Có | Tọa độ theo `coordinate_space` (`null` nếu engine không cung cấp) |
| `confidence` | number | Có | Điểm tin cậy thô (`null` nếu không có; không cùng thang đo giữa các engine) |
| `image_reference`, `input_sha256` | string | Không | Tham chiếu ảnh nguồn và SHA-256 tệp đầu vào |
| `status` | enum | Không | `OK`, `FAILED`, `UNPROCESSED`, `IMPORTED`, `NEEDS_REVIEW`, `EMPTY` |

## 2. Bảng duyệt Làm sạch Văn bản (`duyet_lam_sach.csv` — 22 cột)
- **Cột bất biến (kiểm tra hash khi nạp lại)**: `row_id`, `relative_path`, `source_sha256`, `page`, `line`, `clean`.
- **Metadata & chẩn đoán**: `code`, `kind`, `work`, `raw`, `pdf_page`, `source_image`, `polygon`, `automatic_rules`, `reasons`, `suggested`, `context_before`, `context_after`, `oov_tokens`.
- **Cột quyết định của thành viên**: `action` (`""`, `keep`, `replace`, `delete`, `join_next`), `replacement` (1 dòng duy nhất), `note`.

## 3. Hậu kiểm & Sửa lỗi Dóng hàng (`schemas/alignment_repair.schema.json`)
- Cấu trúc gốc: `work`, `fingerprint`, `findings`, `proposals`.
- Lỗi chính thức: `NONE`, `OMISSION`, `ADDITION`, `MISSING`.
- Nhãn chẩn đoán: `WRONG_ALIGNMENT`, `BOUNDARY_ERROR`, `OCR_ERROR`, `ENTITY_MISMATCH`, `NUMBER_MISMATCH`, `DUPLICATION`, `ORDER_ERROR`.
- Thao tác đề xuất: `KEEP`, `MERGE`, `SPLIT`, `RELINK`, `ADD_LINK`, `REMOVE_LINK`, `FLAG_OCR`, `FLAG_CLEANING`, `REQUEST_REVIEW`.

## 4. Manifest từng Giai đoạn (`schemas/stage_manifest.schema.json`)
- Gồm: `schema` (`hanviet.stage_manifest.v1`), `stage`, `version`, `created_at_utc`, `input_fingerprint`, `output_fingerprint`, `review_status`, `config_snapshot`, `input_manifest`, `output_manifest`, `statistics`, `error_log`.

## 5. Bảng Song ngữ Nộp bài (`san_pham/TVxx/<MA_DE_TAI>_<MA_SACH>/04_dong_hang/`)
- Giữ nguyên chuẩn **4 cột**: `Hán`, `Dịch âm`, `Dịch nghĩa`, `Dịch thơ`.
- Sổ tay kiểm tra `notes.xlsx`: `Tên tác phẩm`, `Câu Hán`, `Câu Việt`, `Lỗi`, `Chỉnh sửa`.
