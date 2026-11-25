# Kết quả Kiểm thử Hồi quy (Regression Test Results)

## Môi trường kiểm thử
- Hệ điều hành: Windows
- Trình thông dịch: `.venv\Scripts\python.exe`
- Phạm vi: Đối chiếu với bộ fixture chuẩn (`tests/fixtures/baseline/{alignment_baseline,cleaning_baseline,source_prep_baseline}.json`) sau khi tái cấu trúc toàn bộ module vào `src/hanviet/`, giữ các lớp tương thích `cong_cu/` và cập nhật quy trình làm sạch văn bản dùng prompt thủ công (Task 04).

## Lệnh đã chạy & Kết quả ghi nhận
Lệnh kiểm thử:
```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```
Kết quả: **26 test chạy — 26 OK (0 failures, 0 errors)** trong `3.780s`, gồm 8 kiểm thử hồi quy logic bảo vệ:
1. `test_segmentation_matches_baseline` — khớp tuyệt đối cho văn xuôi Hán, thơ Hán, Hán `keep_lines=True`, dịch âm văn xuôi, dịch nghĩa văn xuôi, dịch thơ.
2. `test_phonetic_dp_and_lab_text_match_baseline` — khớp tuyệt đối cho `phonetic_links` (quy hoạch động) và chuẩn hóa `lab_text`.
3. `test_clc_request_and_make_rows_match_baseline` — khớp tuyệt đối cho `clc_request`, `make_rows` và `unmatched_ids`.
4. `test_export_reviewed_4col_structure` — xác minh cấu trúc xuất 4 cột (`*_parallel.tsv`, `*_parallel.xlsx`) và `notes.xlsx`.
5. `test_clean_han_and_viet_match_baseline` — khớp tuyệt đối cho `clean_han`, `clean_viet` (chế độ OCR và PDF Text `native_pdf=True`) và `suffix_digit_suggestion`.
6. `test_build_apply_assemble_match_baseline` — khớp tuyệt đối cho `build_records`, `apply_decisions`, `audit_log` và `assemble_works`.
7. `test_review_csv_22_columns_and_allowed_actions` — xác minh `duyet_lam_sach.csv` gồm đúng 22 cột, chấp nhận 5 giá trị `action` hợp lệ (`""`, `"keep"`, `"replace"`, `"delete"`, `"join_next"`), đồng thời từ chối action lạ hoặc `replacement` nhiều dòng.
8. `test_source_prep_matches_baseline` — khớp tuyệt đối cho `Box`, `Workspace.prepare`, `save_text_region`, `mark_reviewed`, `summary` và `region_fingerprint`.

Ngoài ra, tất cả các điểm chạy CLI đều trả mã thoát 0 với `--help`:
- `.\.venv\Scripts\python.exe cat_ly_tran.py --help`
- `.\.venv\Scripts\python.exe scripts/run_cleaning_stage.py --help`
- `.\.venv\Scripts\python.exe scripts/run_ocr_cross_check.py --help`
- `.\.venv\Scripts\python.exe scripts/run_llm_alignment_review.py --help`
- `.\.venv\Scripts\python.exe scripts/run_evaluation_report.py --help`

## Ghi chú tích hợp
- Kiểm thử tích hợp với PDF sách gốc đầy đủ và chạy OCR GPU / gọi API ngoài thực tế chưa chạy trong sandbox cục bộ (vì thiếu PDF gốc và các thư viện OCR GPU trong `.venv`); các adapter OCR và client LLM (Giai đoạn 06) được kiểm chứng offline qua unit/mock/cached fixture trong `tests/test_ocr_cross_check.py`, `tests/test_llm_alignment.py`, `tests/test_portability.py` và `tests/test_stage_outputs.py`.
