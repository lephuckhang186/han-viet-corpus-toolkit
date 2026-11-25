# han-viet-corpus-toolkit

Bộ công cụ và thư viện Python mô-đun hóa (`hanviet`) phục vụ xây dựng ngữ liệu song ngữ **Hán–Việt** theo 4 tầng bản văn (**Hán – Dịch âm – Dịch nghĩa – Dịch thơ**) cho đồ án NLP.

Hệ thống tổ chức quy trình xử lý thành 7 giai đoạn rõ ràng, bảo toàn tuyệt đối nguyên văn nguồn, hỗ trợ truy vết qua hash/manifest, đối chiếu chéo hai động cơ OCR, làm sạch văn bản dựa trên luật kết hợp duyệt thủ công, tách đơn vị câu/thơ, dóng hàng đa phương pháp và kiểm định chất lượng có thể tái lập.

> **Lưu ý khi làm việc với Notebook:** Toàn bộ hướng dẫn chạy từng cell trên máy local, Kaggle/Colab, quy trình cắt nguồn bằng chuột, phạm vi sách và các prompt kiểm tra thủ công đã được chuyển sang [notebooks/README.md](notebooks/README.md).

---

## 1. Giới thiệu quy trình xử lý (7 giai đoạn)

| Giai đoạn | Tên giai đoạn | Chức năng chính | Đầu vào → Đầu ra chính |
|---|---|---|---|
| **01** | Chuẩn bị nguồn (`source_preparation`) | Cắt vùng PDF ra PNG, trích đoạn TXT UTF-8/PDF Text theo tác phẩm, sao lưu nguyên bản, khóa ghi và hoàn tác | `data/*.pdf\|*.txt` → `01_nguon/`, `vung_cat.json`, `nguon.json` |
| **02** | Trích xuất & Dual-OCR (`extraction`) | OCR Hán (PaddleOCR + CLC OCR), OCR Việt (Tesseract `vie` + VietOCR), trích text PDF gốc, đối chiếu chéo Levenshtein & xuất bảng Manual Fixing | `01_nguon/` → `02_ocr_tho/`, `cross_check/` |
| **03** | Làm sạch văn bản (`cleaning`) | Làm sạch Hán/Việt dựa trên luật (`clean_han`, `clean_viet`), xuất `duyet_lam_sach.csv` (22 cột), áp dụng quyết định duyệt & ghép tác phẩm | `02_ocr_tho/` (hoặc TXT gốc) → `duyet_lam_sach.csv` → `03_text_sach/` |
| **04** | Tách đơn vị (`segmentation`) | Tách câu văn xuôi (`han`, `viet`) và dòng thơ kèm offset UTF-8 (`start`, `end`, `part` theo `\f`) | `03_text_sach/` → `units` trong `draft.json` |
| **05** | Dóng hàng & Xuất bảng (`alignment`, `exporters`) | Dóng Hán–âm (Lab DP + từ điển âm), Hán–nghĩa (CLC API có cache & rate limit), tùy chọn Bertalign/Vecalign, xuất TSV/XLSX 4 cột | `units`, `dict/` → `draft.json`, `review.json`, `04_dong_hang/*_parallel.{tsv,xlsx}` |
| **06** | Hậu kiểm dóng hàng LLM (`alignment.llm_review`) | Kiểm tra & đề xuất sửa liên kết (tùy chọn; mặc định chạy offline an toàn `LLM_NOT_RUN`), kiểm định JSON Schema trước khi áp dụng | `draft.json` → `06_llm_hau_kiem/` → `review.json` |
| **07** | Đánh giá & Báo cáo (`evaluation`) | Tính chỉ số đánh giá (OCR CER/WER khi có chuẩn, tỷ lệ bất đồng, tỷ lệ liên kết/duyệt) và sinh báo cáo | Hiện vật các giai đoạn → `07_danh_gia/` (`*.json`, `*.md`) |

---

## 2. Cấu trúc thư mục & Mã nguồn

```text
han-viet-corpus-toolkit/
├── ten_file.py                  # Tên nguồn đầu vào, mã đề tài/sách/thành viên và quy ước đặt tên
├── pyproject.toml               # Khai báo package `hanviet` và dependencies tùy chọn theo giai đoạn
├── .env.example                 # Mẫu biến môi trường (đường dẫn, Tesseract, CLC API, LLM API)
│
├── configs/                     # Cấu hình YAML tập trung, chạy đa môi trường (Windows/Linux/Kaggle/Colab)
│   ├── project.yaml             # Cấu hình gốc dự án & phân giải đường dẫn
│   ├── corpora/                 # Cấu hình 4 bộ sách (CPO_09..CPO_12)
│   ├── members/                 # Cấu hình thành viên (TV02.yaml, TV04.yaml)
│   └── methods/                 # Tham số ocr, cleaning, segmentation, alignment, llm
│
├── src/hanviet/                 # Package Python cốt lõi đã mô-đun hóa
│   ├── common/                  # paths, config, io nguyên tử/hash, manifests, llm_client (Giai đoạn 06)
│   ├── source_preparation/      # Mô hình dữ liệu, thao tác PDF/TXT, lịch sử hoàn tác, UI/CLI
│   ├── extraction/              # Tiền xử lý, adapters (Paddle, CLC, Tesseract, VietOCR), cross-check & manual review
│   ├── cleaning/                # clean_han, clean_viet, pipeline 22 cột + README 16 mục
│   ├── segmentation/            # Bộ tách câu/thơ và tính vị trí UTF-8
│   ├── alignment/               # Runner, validation, backends (Lab, CLC, Bertalign/Vecalign), llm_review
│   ├── exporters/               # Xuất Excel (.xlsx), TSV 4 cột và notes.xlsx
│   └── evaluation/              # Tính metrics và xuất báo cáo JSON/Markdown
│
├── cong_cu/                     # Lớp tương thích ngược (shims/adapters) giữ các import legacy hoạt động bình thường
├── scripts/                     # CLI độc lập cho từng giai đoạn xử lý
├── notebooks/                   # Notebooks theo 7 giai đoạn & notebooks thực hành (kèm notebooks/README.md)
├── prompts/                     # Tập prompt tách biệt theo giai đoạn (cleaning/ và alignment/)
├── schemas/                     # JSON Schema cho ocr_record, alignment_repair, stage_manifest
├── dict/                        # Từ điển hỗ trợ phiên âm / kiểm tra âm tiết Việt
├── data/                        # Thư mục đầu vào cục bộ (không đưa PDF/ảnh lớn vào Git; xem data/README.md)
├── requirements/                # Tách dependencies theo từng giai đoạn (base, ocr, alignment, llm, dev)
├── docs/                        # Tài liệu kiến trúc, dữ liệu, phương pháp luận, đánh giá & tái cấu trúc (Tiếng Việt)
└── tests/                       # Bộ kiểm thử hồi quy logic bảo vệ, Dual-OCR, LLM guard, portability & outputs
```

---

## 3. Yêu cầu hệ thống & Cài đặt

### Yêu cầu tối thiểu
- **Python >= 3.11** (khuyến nghị cài kèm Tkinter nếu dùng giao diện cắt PDF/TXT từ `notebooks/01_source_preparation.ipynb`).
- Hệ điều hành: Windows, Linux hoặc môi trường Kaggle / Google Colab.

### Cài đặt nhanh môi trường cục bộ

```powershell
# 1. Tạo môi trường ảo và kích hoạt/cài đặt gói cơ bản
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements\base.txt

# 2. (Tùy chọn) Cài package hanviet ở chế độ editable nếu muốn import trực tiếp ở mọi thư mục
.\.venv\Scripts\python.exe -m pip install -e .
```

Các nhóm thư viện bổ sung tùy theo giai đoạn bạn cần chạy:

| Nhu cầu sử dụng | Lệnh cài đặt |
|---|---|
| Chỉ chạy cắt nguồn (`notebooks/01_source_preparation.ipynb`) | `.\.venv\Scripts\python.exe -m pip install -r requirements.txt` |
| Xử lý dữ liệu, cleaning, dóng hàng, xuất Excel | `.\.venv\Scripts\python.exe -m pip install -r requirements\base.txt` |
| OCR (PaddleOCR, PaddleX, Transformers, VietOCR, PyTesseract) | `.\.venv\Scripts\python.exe -m pip install -r requirements\ocr.txt` |
| Dóng hàng nhúng tùy chọn (Bertalign / Vecalign / HF) | `.\.venv\Scripts\python.exe -m pip install -r requirements\alignment.txt` |
| Kiểm tra schema JSON / hậu kiểm dóng hàng LLM | `.\.venv\Scripts\python.exe -m pip install -r requirements\llm.txt` |
| Kiểm thử & phát triển notebook | `.\.venv\Scripts\python.exe -m pip install -r requirements\dev.txt` |

### Cấu hình biến môi trường (`.env`)

Sao chép `.env.example` thành `.env` khi cần ghi đè đường dẫn hoặc khai báo API ngoài:

```powershell
Copy-Item .env.example .env
```

- `HANVIET_PROJECT_ROOT`, `HANVIET_DATA_ROOT`, `HANVIET_OUTPUT_ROOT`, `HANVIET_ENV`: ghi đè đường dẫn đa máy (mặc định tự nhận theo `configs/project.yaml`).
- `TESSERACT_CMD`, `TESSDATA_PREFIX`: trỏ tới Tesseract binary & dữ liệu ngôn ngữ `vie` (khi chạy OCR Việt Dual-OCR).
- `CLC_API_KEY`, `CLC_OCR_API_KEY`: token cho Kim Hán Nôm (CLC) API (tách riêng hai dịch vụ Alignment và OCR).
- `LLM_PROVIDER`, `LLM_MODEL`, `LLM_API_KEY`, `LLM_BASE_URL`: chỉ dùng cho Giai đoạn 06 (hậu kiểm dóng hàng); nếu để trống, hệ thống chạy hoàn toàn offline với trạng thái `LLM_NOT_RUN`. **Giai đoạn 03 (Text Cleaning) không dùng LLM API key.**

---

## 4. Hướng dẫn sử dụng nhanh

### Giai đoạn 01 — Cắt nguồn theo tác phẩm (`notebooks/01_source_preparation.ipynb`)

Bốn công cụ cắt sách (`CPO_09` Bắc sứ, `CPO_10` Hịch tướng sĩ, `CPO_12` Lý–Trần, `CPO_11` Văn sách Thi Đình) đã được gộp vào một notebook duy nhất [notebooks/01_source_preparation.ipynb](notebooks/01_source_preparation.ipynb): mỗi tác phẩm nằm ở một cell riêng, hỗ trợ người dùng tự nhập số trang / khoảng trang và chọn `ACTION` (`info`, `prepare`, `check`, `summary`, `crop_page`, `text_lines`, `gui`).

### Giai đoạn 02 — OCR & Đối chiếu chéo Dual-OCR

- Chạy OCR Việt/Kaggle-Colab bằng [notebooks/02_ocr/OCR_viet.ipynb](notebooks/02_ocr/OCR_viet.ipynb) hoặc quy trình OCR Hán + Cross-check + Manual Fixing bằng [notebooks/02_ocr/OCR_han.ipynb](notebooks/02_ocr/OCR_han.ipynb) (xem hướng dẫn chi tiết 15 mục tại [notebooks/02_ocr/README.md](notebooks/02_ocr/README.md) và báo cáo triển khai tại [docs/refactoring/HAN_OCR_IMPLEMENTATION.md](docs/refactoring/HAN_OCR_IMPLEMENTATION.md)).
- Đối chiếu chéo trực tiếp hai file JSON OCR chính/phụ qua CLI:

```powershell
.\.venv\Scripts\python.exe scripts\run_ocr_cross_check.py `
  --primary path\to\paddle_han.json `
  --secondary path\to\clc_han.json `
  --variant han `
  --dp-line-match `
  --output-dir san_pham\TV04\CV06_CPO_11\02_ocr_tho\cross_check
```

### Giai đoạn 03 — Làm sạch văn bản & Rà soát thủ công

Chạy rule-based cleaning và xuất bảng duyệt 22 cột (`duyet_lam_sach.csv`):

```powershell
.\.venv\Scripts\python.exe scripts\run_cleaning_stage.py `
  --output-dir san_pham\TV04\05_quan_ly\clean_v04_parts `
  --member 4 `
  --codes CPO_09 CPO_11 CPO_12
```

Hoặc thao tác tương tác qua [notebooks/clean_text.ipynb](notebooks/clean_text.ipynb) / [notebooks/03_text_cleaning.ipynb](notebooks/03_text_cleaning.ipynb).

- **Hướng dẫn đầy đủ 16 mục cho Text Cleaning (gồm quy trình không cần API key, cấu trúc 22 cột của `duyet_lam_sach.csv`, 4 hành động hợp lệ `keep` / `replace` / `delete` / `join_next`, cùng 2 prompt sao chép trực tiếp cho Hán văn và văn bản Việt)**: xem [src/hanviet/cleaning/README.md](src/hanviet/cleaning/README.md) hoặc [notebooks/README.md](notebooks/README.md).
- Hai prompt gốc được lưu riêng tại [prompts/cleaning/han_cleaning.md](prompts/cleaning/han_cleaning.md) và [prompts/cleaning/viet_cleaning.md](prompts/cleaning/viet_cleaning.md).

### Giai đoạn 04 & 05 — Tách đơn vị, Dóng hàng và Xuất bảng

- Chạy qua notebook [notebooks/dong_hang.ipynb](notebooks/dong_hang.ipynb) (chế độ `nguon`, `nhap`, `xuat`) hoặc các notebook mô-đun [notebooks/04_text_segmentation.ipynb](notebooks/04_text_segmentation.ipynb) & [notebooks/05_text_alignment.ipynb](notebooks/05_text_alignment.ipynb).
- Đầu ra hợp lệ sau khi duyệt `"approved": true` trong `review.json` là bộ 3 file: `*_parallel.tsv`, `*_parallel.xlsx` (4 cột `Hán`, `Dịch âm`, `Dịch nghĩa`, `Dịch thơ`) và `notes.xlsx`.

### Giai đoạn 06 & 07 — Hậu kiểm LLM cho dóng hàng & Đánh giá

```powershell
# Kiểm định & đề xuất sửa trên draft.json (an toàn offline khi chưa cấu hình LLM)
.\.venv\Scripts\python.exe scripts\run_llm_alignment_review.py `
  --draft san_pham\TV04\CV06_CPO_12\05_quan_ly\dong_hang\TV04\bai0140\draft.json `
  --stage-dir san_pham\TV04\CV06_CPO_12\06_llm_hau_kiem\bai0140

# Sinh báo cáo đánh giá JSON + Markdown
.\.venv\Scripts\python.exe scripts\run_evaluation_report.py `
  --draft san_pham\TV04\CV06_CPO_12\05_quan_ly\dong_hang\TV04\bai0140\draft.json `
  --output-dir san_pham\TV04\CV06_CPO_12\07_danh_gia
```

---

## 5. Kiểm thử tự động (Tests)

Chạy toàn bộ bộ kiểm thử (regression logic được bảo vệ, Dual-OCR cross-check, kiểm tra patch dóng hàng LLM, tính khả chuyển đa nền tảng và hợp đồng đầu ra):

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

---

## 6. Hệ thống tài liệu chuyên sâu

- **Hướng dẫn thực hành Notebook, cắt nguồn & Prompts:** [notebooks/README.md](notebooks/README.md)
- **Hướng dẫn Text Cleaning & Prompts Hán/Việt:** [src/hanviet/cleaning/README.md](src/hanviet/cleaning/README.md)
- **Kiến trúc & Dữ liệu:**
  - [Kiến trúc hệ thống (architecture.md)](docs/architecture.md)
  - [Từ điển dữ liệu (data_dictionary.md)](docs/data_dictionary.md)
  - [Nguồn gốc mô hình & Công cụ (model_provenance.md)](docs/model_provenance.md)
  - [Quy trình đánh giá (evaluation_protocol.md)](docs/evaluation_protocol.md)
  - [Khả năng tái lập (reproducibility.md)](docs/reproducibility.md)
- **Phương pháp luận nghiên cứu (`docs/methodology/`):**
  - [OCR_METHOD.md](docs/methodology/OCR_METHOD.md) | [OCR_CROSS_CHECK.md](docs/methodology/OCR_CROSS_CHECK.md)
  - [TEXT_CLEANING.md](docs/methodology/TEXT_CLEANING.md) | [LLM_CLEANING_REVIEW.md](docs/methodology/LLM_CLEANING_REVIEW.md)
  - [ALIGNMENT_METHOD.md](docs/methodology/ALIGNMENT_METHOD.md) | [LLM_ALIGNMENT_REVIEW.md](docs/methodology/LLM_ALIGNMENT_REVIEW.md)
- **Báo cáo tái cấu trúc (`docs/refactoring/`):**
  - [REPOSITORY_AUDIT.md](docs/refactoring/REPOSITORY_AUDIT.md) | [MIGRATION_MAP.md](docs/refactoring/MIGRATION_MAP.md) | [PROTECTED_LOGIC.md](docs/refactoring/PROTECTED_LOGIC.md)
  - [KNOWN_ISSUES.md](docs/refactoring/KNOWN_ISSUES.md) | [REGRESSION_RESULTS.md](docs/refactoring/REGRESSION_RESULTS.md) | [IMPLEMENTATION_REPORT.md](docs/refactoring/IMPLEMENTATION_REPORT.md)
