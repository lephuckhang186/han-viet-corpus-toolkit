# Đặc tả Logic được Bảo vệ (Protected Logic Specification)

Các thuật toán, quy tắc, ngưỡng, biểu thức chính quy (regex) và logic nghiệp vụ dưới đây **phải giữ nguyên tuyệt đối hành vi**. Mọi hạng mục đều có bộ dữ liệu chuẩn (golden regression fixtures) trong `tests/fixtures/baseline/` và được kiểm chứng tự động tại `tests/test_regression_protected_logic.py`.

## 1. Chuẩn bị nguồn (Source Preparation)
- `models.py`: `Source.contains`, `Book.source`, `Box.__post_init__`, `validate_work`, `validate_assignment`.
- `pdf_ops.py`: `render_page`, `crop_png` (quy đổi khung pixel bằng floor/ceil tại mặc định 300 DPI), `extract_text` (kiểm tra trang xoay, `get_text_bounded` với `1 - box.y1`, `1 - box.y0`, chuẩn hóa xuống dòng).
- `text_ops.py`: `select_lines`, `select_characters`, `join_parts` (`"\n".join(parts)`).
- `storage.py`: `sha256`, `atomic_bytes`, `immutable_bytes`, `backup`, `workspace_lock`.
- `history.py`: `commit`, `undo`, `recover` (bảo vệ `ban_goc`, kiểm tra hash trạng thái).
- `workspace.py` & `region_actions.py`: `Workspace.prepare`, `save_pdf_region`, `save_text_region`, `region_fingerprint`, `mark_absent`, `summary`, `check`, `RegionActions.overlaps` (IoU >= 0.8), `replace_pdf`, `replace_text`, `remove`, `mark_reviewed`.

## 2. Làm sạch văn bản dựa trên luật (Rule-Based Text Cleaning)
- `clean_shared`: `normalize_spaces`, `EMPTY_BRACKETS = r"\(\s*\)|\[\s*\]|（\s*）|【\s*】"`, bảo vệ `[MASK]` quanh `PUNCTUATION_REPLACEMENTS`.
- `common_flags`: `NOTE_MARK`, kiểm tra ngoặc mất cân đối, `standalone_number`, `letters_attached_to_digits`, `unexpected_symbol`.
- `clean_han`: giữ nguyên các ký tự CJK hiếm / Extension B+ / PUA, gắn cờ `latin_in_han`, `[%％○]`.
- `clean_viet`: `normalize_latin` (chuẩn hóa NFC theo từng đoạn Latin gồm dấu tổ hợp), `str.maketrans("Ƣƣ", "Ưư")` khi `native_pdf=True`, `re.sub(r"\[\d{1,3}[ab]\]", "", ...)` khi `native_pdf=True`, loại bỏ nhãn đứng riêng `VIET_LABELS`, phát hiện `possible_note_section`.
- `suffix_digit_suggestion`: chỉ bỏ chữ số ở cuối các token bắt đầu bằng chữ cái và không chứa chữ số bên trong.
- `build_records`, `review_csv_rows`, `validate_review_action`, `read_decisions`, `apply_decisions`, `assemble_works`: bảng duyệt `duyet_lam_sach.csv` gồm đúng 22 cột; chỉ chấp nhận `action` thuộc `{"", "keep", "replace", "delete", "join_next"}`; ghép trang bằng `\f`, và `join_next` nối không dấu cách đối với Hán, có `" "` đối với Việt.

## 3. Tách câu và Dóng hàng (Segmentation & Alignment)
- `content_line_spans`: khớp các đoạn khác khoảng trắng theo `[^\r\n\f]+`.
- `split_prose`: regex ngắt câu cho `"han"` (`[。！？；]+[」』”’]*`) và `"viet"` (kèm heuristic xử lý dấu chấm dính và ngoại lệ viết tắt `TS|GS|PGS|ThS|TP|Q|tr|vd`).
- `segment`: cắt theo `line_range`, bỏ qua `titles`, xử lý `keep_lines` / `poetry` / fallback Hán không dấu câu, `clean_spacing`, offset UTF-8 `start`/`end` và `part` theo `\f`.
- `lab_text` & `phonetic_links`: giữ nguyên `[MASK]`, bỏ dấu câu Unicode nhóm `P`/`S`, chi phí quy hoạch động `(1,1)`, `(1,2)`, `(2,1)`, `(1,0)` (0.7), `(0,1)` (0.7), phạt lệch `0.1`.
- `run_lab`: sinh đúng định dạng `config.yaml`, kiểm tra SHA-256 so với `LAB_SCRIPT_SHA256`, chạy subprocess và phân tích TSV/thống kê đầu ra.
- `clc_request`, `clc_span`, `clc_result`, `clc_response`, `align_clc`, `reserve_clc_request`: giữ nguyên request hash (`sha256([url, body])`), khôi phục span duy nhất, giới hạn tần suất (`25/phút, 50/giờ, 200/ngày, 600/tuần`), độ trễ 3 giây.
- `align_bert`, `align_vecalign`: giữ nguyên vẹn trong mã nguồn và KHÔNG kích hoạt mặc định.
- `validate_links`, `make_rows`, `unmatched_ids`, `verify_identity`, `write_protected`, `xlsx_bytes`, `export_reviewed`: bảo toàn chỉ số đơn điệu nghiêm ngặt không chồng chéo, xuất đúng 4 cột (`Hán`, `Dịch âm`, `Dịch nghĩa`, `Dịch thơ`) + `notes.xlsx`.
