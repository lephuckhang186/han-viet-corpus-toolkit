# Kiểm toán Kho mã nguồn (`han-viet-corpus-toolkit`)

## 1. Trạng thái Git & Công việc đang thực hiện của người dùng (Cơ sở trước tái cấu trúc)

- **Nhánh (Branch)**: `main` (đồng bộ với `origin/main` tại commit `8e4f53d52c003322205e101be130ce441e489681`).
- **Các file được theo dõi đang sửa dở (được giữ nguyên toàn vẹn)**:
  - `cong_cu/alignment_notebook.py`: Cập nhật `show_sources` để nối các file TXT nhiều phần bằng ký tự `\f`.
  - `cong_cu/dong_hang.py`: Cập nhật `clean_sources_by_work` và `load_work` để lập chỉ mục các file đã ghép và từng phần theo trang trong `data/LyTran/03_text_sach` (`phanXXXX_pdfpYYYY.txt`).
  - `notebooks/clean_text.ipynb`: Đang cấu hình cho `TV04`, `clean_v04_parts`, đọc từ `data/`.
  - `notebooks/dong_hang.ipynb`: Đang cấu hình cho `TV04`, gồm Bắc sứ, Thi Đình, Lý–Trần và các cell gộp dữ liệu.
  - `notebooks/ocr_nlp.ipynb`: Đang cấu hình cho `TV04` + bổ sung cell chạy OCR CLC LAB (`cong_cu.clc_ocr.run`).
- **Các file chưa theo dõi trong workspace (được giữ nguyên)**:
  - `cong_cu/clc_ocr.py`, `cong_cu/bac_su_notebook.py`, `cong_cu/thi_dinh_notebook.py`.
  - `TaiLieuAPI_HanNom_CLC.pdf` (tài liệu chính thức 14 trang về API Kim Hán Nôm).
  - `.env`, `.env.clc_ocr` (cấu hình bí mật cục bộ — không đọc giá trị vào log và không commit).
  - `data/BacSu/`, `data/LyTran/`, `data/ThiDinh/` (ảnh cắt nguồn TV04, OCR TXT, text sạch, bản nháp).
  - `san_pham/TV04/`, `san_pham/05_quan_ly/`.
  - `.vscode/settings.json`.

## 2. Nguồn tài liệu còn thiếu & Hạn chế ghi nhận

1. `Guideline.pdf` không có mặt trong workspace hiện tại (chỉ được tham chiếu trong `README.md` / `AGENTS.md` là tài liệu cục bộ).
2. Các file PDF sách gốc được khai báo trong `ten_file.py` (`Nguyễn Huệ Chi...pdf`, `Van_sach_thi_Dinh...pdf`, `HichTuongSi...pdf`, `BắcSứThôngLục_北使通錄(Q1_4).pdf`, `Bắc Sứ Thông Lục.pdf`) không nằm ở thư mục gốc `data/`; thư mục `data/` cục bộ hiện chứa các thư mục theo giai đoạn `BacSu/`, `LyTran/`, `ThiDinh/` (bao gồm `data/BacSu/01_nguon/han/Bắc Sứ Thông Lục_scan.pdf`).
3. `PHỤ LỤC A` và `PHỤ LỤC B` được nhắc tới trong yêu cầu ban đầu không có nội dung kèm theo; tuy nhiên ở bước hoàn thiện Task 04, hai prompt đầy đủ cho Hán văn và văn bản Việt đã được người dùng cung cấp nguyên văn và đưa trực tiếp vào tài liệu Text Cleaning.
4. `.gitignore` trước tái cấu trúc có bỏ qua `/tests` (commit `b7e3ea85` đã xóa `tests/` cũ và bỏ qua `/tests`).

## 3. Kiểm kê chức năng & Phân loại mức độ kiểm chứng

| Nhóm chức năng | Trạng thái trước refactor | Hành vi đã kiểm chứng | Phân loại mã |
|---|---|---|---|
| Chuẩn bị nguồn (`ten_file.py`, `cat_*.py`, `cong_cu/models,pdf_ops,text_ops,storage,history,workspace,region_actions,ui,text_ui,cli`) | Đã triển khai & đang hoạt động | Cắt vùng PDF, xuất PNG, chọn TXT UTF-8, ghi nguyên tử, khóa workspace, nhật ký hoàn tác | Thuật toán + Lưu trữ/UI/Cấu hình |
| OCR (`notebooks/ocr_nlp.ipynb`, `cong_cu/clc_ocr.py`) | Đã triển khai trong notebook + script rời | PaddleOCR (`transformers` PP-OCRv6) Hán dọc/ngang, VietOCR + Paddle TextDetection Việt, CLC web OCR (`image-upload` + `image-ocr`). Trước tái cấu trúc chưa có đối chiếu chéo hai OCR (Dual-OCR) hay Tesseract Việt. | Thuật toán + Notebook + API adapter |
| Làm sạch văn bản (`notebooks/clean_text.ipynb`) | Mới triển khai trong notebook | `clean_han`, `clean_viet`, `normalize_latin`, `build_records`, duyệt/áp dụng CSV, `assemble_works`. Chưa tách thành module Python độc lập và chưa có hướng dẫn/prompt review thủ công có hệ thống. | Thuật toán + Notebook |
| Tách câu & Dóng hàng (`cong_cu/dong_hang.py`, `alignment_backends.py`, `alignment_notebook.py`, `bac_su_notebook.py`, `thi_dinh_notebook.py`) | Đã triển khai & đang hoạt động (Lab + CLC đã kiểm chứng trên `TV04`); Bertalign/Vecalign đã viết nhưng tùy chọn/chưa cấu hình mặc định | `segment`, `split_prose`, `phonetic_links`, `run_lab`, `align_clc`, `make_rows`, `export_reviewed`. Bertalign/Vecalign cần git checkout ngoài + ONNX/transformers. | Thuật toán + Backends + Xuất bảng |
| Kiểm tra & sửa lỗi dóng hàng bằng LLM | Mới có ở mức mô tả / thao tác thủ công | Trước đó dùng prompt Codex copy-paste thủ công (`poetry_prompt.json` -> `poetry_result.json`; prompt CSV). Chưa có client/schema kiểm tra đầu ra LLM cho dóng hàng. | Yêu cầu mới (Giai đoạn 06) |

## 4. Phụ thuộc giữa các file gốc

- `cat_*.py` -> `ten_file`, `cong_cu.models`, `cong_cu.cli`
- `cong_cu.cli` -> `ten_file`, `cong_cu.models`, `cong_cu.workspace`, `cong_cu.pdf_ops`, `cong_cu.ui`
- `cong_cu.workspace` -> `ten_file`, `cong_cu.models`, `cong_cu.history`, `cong_cu.pdf_ops`, `cong_cu.text_ops`, `cong_cu.region_actions`, `cong_cu.storage`
- `cong_cu.dong_hang` -> `cong_cu.alignment_backends` (`align_clc`, `clc_request`, `run_lab`, `CLCTextMismatch`)
- `cong_cu.alignment_backends` -> `cong_cu.storage`, `yaml`, `requests`, `sqlite3`, tùy chọn `huggingface_hub`, `sentence_transformers`, `bertalign`, `vecalign`
- `cong_cu.alignment_notebook`, `bac_su_notebook`, `thi_dinh_notebook`, `clc_ocr` -> `cong_cu.dong_hang`, `cong_cu.alignment_backends`, `ten_file`

## 5. Đường dẫn gán cứng (Hard-coded Paths) & Phụ thuộc môi trường phát hiện

1. `README.md`, `CONTEXT.md`, `phancong.md`: tham chiếu cục bộ `D:\code\CS\NLP`.
2. `ten_file.py`: gán cứng `THANH_VIEN = 2`, `MA_DE_TAI = "CV06"`, `OUTPUT_ROOT = ROOT / "san_pham" / f"TV{THANH_VIEN:02d}"` và tên các file PDF cụ thể.
3. `cong_cu/alignment_backends.py` dòng 39: gán cứng `CLC_REQUEST_LOG = Path(__file__).resolve().parents[1] / "san_pham" / "05_quan_ly" / "clc_requests.sqlite3"`.
4. `cong_cu/dong_hang.py` dòng 106: gán cứng `book_root.parents[2] / "data" / "LyTran" / "03_text_sach" / folder` trong `clean_sources_by_work`.
5. `cong_cu/dong_hang.py` dòng 364 & 391: gán cứng `san_pham/<member>/05_quan_ly/alignment_tools` và `project / "dict"`.
6. `cong_cu/bac_su_notebook.py` dòng 61: gán cứng `project / "data/BacSu/03_text_sach"` và `"san_pham/TV04"`.
7. `cong_cu/thi_dinh_notebook.py` dòng 16: gán cứng `project / "data" / "ThiDinh" / "03_text_sach"`.
8. `cong_cu/clc_ocr.py` dòng 16, 30, 34: gán cứng `STEM = "CPO_11_TV04_bai0024_han_v03"`, `len(images) != 20`, `"san_pham/TV04"`.
9. `notebooks/clean_text.ipynb`: gán cứng `OUTPUT_ROOT = PROJECT_ROOT / "san_pham" / "TV04"` và `members != {4}` trong `describe_source`.
10. `notebooks/ocr_nlp.ipynb`: gán cứng đường dẫn Kaggle/Colab (`/kaggle/working/NLP_OCR_TV04`, `/content/drive/MyDrive/NLP_OCR_TV04`), Google Drive folder ID trong `JOBS` và `DEVICE = "gpu:0"`.

## 6. Thư viện phụ thuộc chưa khai báo đầy đủ

`requirements.txt` trước đó chỉ khai báo `pypdfium2==5.14.0` và `Pillow==13.0.0`, bỏ sót nhiều gói thực tế đã dùng:
- **Đang dùng & đã cài trong `.venv`**: `PyYAML` (`6.0.4`), `requests` (`2.34.2`), `XlsxWriter` (`3.3.3`), `pandas` (`3.1.1`), `numpy` (`2.5.5`), `ipykernel` (`7.4.0`).
- **Dùng trong notebook / bộ dóng tùy chọn (chưa cài trong `.venv` cục bộ)**: `paddleocr`, `paddlex`, `transformers`, `torch`, `torchvision`, `vietocr`, `einops`, `gdown`, `tqdm`, `google-api-python-client`, `google-auth`, `google-auth-oauthlib`, `huggingface_hub`, `sentence-transformers`, `bertalign`, `vecalign`, `pytesseract` (bổ sung cho Dual-OCR Việt).

## 7. Hợp đồng API & Đầu ra các giai đoạn

- **CLC Web API (`TaiLieuAPI_HanNom_CLC.pdf`)**:
  - Tên miền gốc: `https://kimhannom.fit.hcmus.edu.vn/api/web/clc-sinonom/`
  - Xác thực: `Authorization: Bearer <token>`, `User-Agent` khác mặc định `python-requests`.
  - Giới hạn tần suất: 25/phút, 50/giờ, 200/ngày, 600/tuần; khoảng nghỉ >= 3 giây.
  - Các endpoint được tài liệu xác nhận: `image-upload`, `image-ocr`, `sentence-alignment`, `viet-ocr`, `sinonom-transliteration`, `sinonom-verse-translation`, `sinonom-fair-seg`, `separate-sentences`.
- **Hợp đồng dữ liệu giữa các giai đoạn**:
  - Giai đoạn 1 -> 2: `01_nguon/<han|viet/...>/<work_stem>/phanXXXX_pdfpYYYY.png`, `05_quan_ly/vung_cat.json`, `nguon.json`.
  - Giai đoạn 2 -> 3: `02_ocr_tho/<han|viet/...>/<work_stem>/phanXXXX_pdfpYYYY.{txt,json,meta.json}` + `*_ocr_tho.txt`.
  - Giai đoạn 3 -> 4/5: `03_text_sach/<han|viet/...>/<stem>.txt` + `work_manifest.json`, `changes.jsonl`, `summary.json`, và `duyet_lam_sach.csv` (22 cột).
  - Giai đoạn 5 -> 6/Xuất bảng: `draft.json` (`work`, `fingerprint`, `units`, `sources`, `links`, `unmatched`, `lab_diagnostics`), `review_template.json`, `review.json` (`approved: true`), `04_dong_hang/<work>/<book>_<work>_parallel.{tsv,xlsx}` (4 cột: `Hán`, `Dịch âm`, `Dịch nghĩa`, `Dịch thơ`) + `notes.xlsx`.
