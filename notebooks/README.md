# Hướng dẫn sử dụng Notebooks & Quy trình thực hành (`han-viet-corpus-toolkit`)

Tài liệu này tập hợp toàn bộ hướng dẫn vận hành notebook, quy trình cắt nguồn – OCR – làm sạch – dóng hàng, cũng như các prompt kiểm tra thủ công phục vụ thành viên thực hiện trực tiếp trên máy cá nhân, Kaggle và Google Colab.

> Nếu bạn đang tìm tài liệu **giới thiệu tổng quan codebase, kiến trúc module `src/hanviet/` và hướng dẫn cài đặt/CLI**, hãy xem [README.md ở thư mục gốc](../README.md).

## Mục lục

1. [Danh sách Notebooks theo giai đoạn](#danh-sách-notebooks-theo-giai-đoạn)
2. [Chuẩn bị và dóng hàng ngữ liệu Hán–Việt (Quy trình từ TXT đến tệp nộp)](#chuẩn-bị-và-dóng-hàng-ngữ-liệu-hánviệt)
3. [Hai prompt Codex cho dóng hàng & truy vết](#hai-prompt-codex)
4. [Cắt nguồn trên máy local (`01_source_preparation.ipynb`) & Bố cục dữ liệu](#chạy-ngay)
5. [OCR trên Kaggle / Google Colab (`02_ocr/OCR_viet.ipynb` & `OCR_han.ipynb`)](#ocr-trên-kaggle--google-colab)
6. [Làm sạch văn bản & Kiểm tra thủ công với LLM (`clean_text.ipynb` / `03_text_cleaning.ipynb`)](#làm-sạch-văn-bản-clean_textipynb--03_text_cleaningipynb-và-kiểm-tra-thủ-công-với-llm)
7. [Phụ lục: Các prompt tham khảo](#phụ-lục-các-prompt-tham-khảo)

---

## Danh sách Notebooks theo giai đoạn

| Giai đoạn | Notebook mô-đun mới | Notebook legacy / thực hành | Mục đích |
|---|---|---|---|
| 01. Chuẩn bị nguồn | [01_source_preparation.ipynb](01_source_preparation.ipynb) | Mỗi tác phẩm 1 cell, tự nhập số trang, chế độ GUI/CLI tích hợp | Kiểm tra phạm vi, hash nguồn, vùng cắt |
| 02. OCR & Đối chiếu chéo | [02_ocr/OCR_han.ipynb](02_ocr/OCR_han.ipynb) (xem [02_ocr/README.md](02_ocr/README.md)) | [02_ocr/OCR_viet.ipynb](02_ocr/OCR_viet.ipynb) | OCR Hán (PaddleOCR + CLC + Cross-check + Manual Fixing) và OCR Việt |
| 03. Làm sạch văn bản | [03_text_cleaning.ipynb](03_text_cleaning.ipynb) | [clean_text.ipynb](clean_text.ipynb) | Làm sạch rule-based, xuất `duyet_lam_sach.csv`, rà soát thủ công |
| 04. Tách đơn vị câu | [04_text_segmentation.ipynb](04_text_segmentation.ipynb) | [dong_hang.ipynb](dong_hang.ipynb) | Tách câu văn xuôi / dòng thơ & tính offset UTF-8 |
| 05. Dóng hàng & Xuất bảng | [05_text_alignment.ipynb](05_text_alignment.ipynb) | [dong_hang.ipynb](dong_hang.ipynb) | Lab DP, CLC API, Bertalign/Vecalign tùy chọn, xuất TSV/XLSX 4 cột |
| 06. Hậu kiểm dóng hàng LLM | [06_llm_alignment_review.ipynb](06_llm_alignment_review.ipynb) | Prompt Codex ở mục 3 | Kiểm tra & đề xuất sửa `draft.json` có kiểm chứng schema |
| 07. Đánh giá ngữ liệu | [07_evaluation.ipynb](07_evaluation.ipynb) | — | Thống kê chỉ số đánh giá & xuất báo cáo JSON/Markdown |

---

## Chuẩn bị và dóng hàng ngữ liệu Hán–Việt

Repo đi từ cắt nguồn, OCR và làm sạch TXT đến dóng hàng theo từng tác phẩm hoặc mục. Kết quả xuất giữ bốn cột **Hán – Dịch âm – Dịch nghĩa – Dịch thơ** theo yêu cầu trong [CONTEXT.md](../CONTEXT.md). Mỗi bản văn giữ nguyên nội dung theo nguồn đã đối chiếu.

- Có bảng Excel/TSV rồi → xem [Xuất tệp nộp](#xuất-tệp-nộp) để biết tệp nào cần dùng.
- Có TXT sạch → bắt đầu ở [Bước 6. Tách đơn vị và tạo bản nháp](#bước-6-tách-đơn-vị-và-tạo-bản-nháp).
- Có `poetry_prompt.json` hoặc CLC báo lệch → dùng [Prompt 1](#prompt-1-ghép-thơ-và-rà-lỗi-clc).
- Cần tra ảnh gốc, sửa TXT rồi chạy lại → dùng [Prompt 2](#prompt-2-truy-vết-sửa-txt-sạch-và-dóng-lại).
- Mới có PDF → bắt đầu ở [Bước 3. Cắt nguồn](#bước-3-cắt-nguồn).

### Sử dụng notebook từ TXT đến tệp nộp

| Bước | Notebook hoặc công cụ | Kết quả |
|---|---|---|
| 1. Xác nhận đề tài và phạm vi | `../phancong.md` và [ten_file.py](../ten_file.py) | Mã đề tài, mã sách, quyển/bài và khoảng trang được giao |
| 2. Kiểm kê nguồn | Bảng kiểm kê của nhóm và thư mục `data/` | Danh sách tài liệu, bản văn, dạng nguồn và phạm vi |
| 3. Cắt nguồn | [01_source_preparation.ipynb](01_source_preparation.ipynb) trên máy local | Ảnh vùng cắt hoặc TXT thô trong `01_nguon/` |
| 4. OCR PDF scan | [02_ocr/OCR_viet.ipynb](02_ocr/OCR_viet.ipynb) & [02_ocr/OCR_han.ipynb](02_ocr/OCR_han.ipynb) | TXT, JSON và metadata OCR theo từng ảnh trong `02_ocr_tho/` |
| 5. Làm sạch | [clean_text.ipynb](clean_text.ipynb) hoặc [03_text_cleaning.ipynb](03_text_cleaning.ipynb) trên máy local | TXT theo bài và bản văn trong `03_text_sach/`, kèm manifest truy vết |
| 6. Tách đơn vị | [dong_hang.ipynb](dong_hang.ipynb), chế độ `nhap` | Đơn vị Hán, âm, nghĩa và thơ trong `draft.json` |
| 7. Dóng hàng và duyệt | Cùng lượt `nhap` trong [dong_hang.ipynb](dong_hang.ipynb), sau đó dùng hai prompt Codex khi cần | Nháp dóng, đề xuất và bản duyệt trong `05_quan_ly/dong_hang/` |
| Xuất | `CHE_DO = "xuat"` trong notebook dóng hàng | TSV, XLSX và `notes.xlsx` trong `04_dong_hang/` |

Ví dụ bên dưới dùng Văn sách Thi Đình (`CPO_11`, bài 14–18) và Thơ văn Lý–Trần (`CPO_12`, bài 131–207). Prompt 1 quét theo đường dẫn được giao. Prompt 2 giới hạn ở hai sách này. Bắc sứ (`CPO_09`) có cell riêng. Mỗi mục Bắc sứ cần khoảng dòng Hán và Việt đã đối chiếu nội dung trong `KHOANG_DONG_THEO_MUC`. Khoảng dòng tính từ 1, bỏ dòng trống, tính cả hai đầu.

### Chuẩn bị môi trường local

1. Mở thư mục repo trong VS Code. Với các notebook chạy local, chọn kernel từ `.venv/Scripts/python.exe` (Windows) hoặc `.venv/bin/python` (Linux/macOS). Phần [Chạy ngay](#chạy-ngay) có lệnh tạo `.venv` nếu máy chưa có.
2. Kiểm tra các gói cho notebook và luồng dóng hàng. Nếu còn thiếu, cài vào cùng `.venv`:

```powershell
.\.venv\Scripts\python.exe -c "import ipykernel, pandas, requests, yaml, xlsxwriter; print('OK')"
.\.venv\Scripts\python.exe -m pip install -r ..\requirements\base.txt
```

### Bước 1. Xác nhận đề tài và phạm vi

Đọc bảng phân công local tại [phancong.md](../phancong.md) để xác định sách, bài và các mốc trang. Đối chiếu `MA_DE_TAI`, mã sách và đường dẫn nguồn trong [ten_file.py](../ten_file.py) hoặc trong `configs/corpora/*.yaml`. Bước này dùng bảng phân công và file cấu hình.

### Bước 2. Kiểm kê nguồn

Lập bảng ghi tên tài liệu, bản Hán hoặc bản Việt, dạng PDF scan hay PDF Text và phạm vi được giao. Đặt file gốc theo [hướng dẫn thư mục dữ liệu](../data/README.md). Dùng bước kiểm kê để chọn xử lý OCR cho bản scan hoặc trích chữ cho bản có lớp text.

### Bước 3. Cắt nguồn

Mở [01_source_preparation.ipynb](01_source_preparation.ipynb), chạy Cell 1 rồi chọn đúng cell của tác phẩm cần cắt (`Bắc sứ thông lục`, `Hịch tướng sĩ`, `Thơ văn Lý–Trần`, `Văn sách thi Đình`). Bạn có thể tự nhập khoảng trang qua `CUSTOM_PAGES` hoặc `PROMPT_INPUT_PAGES = True`, sau đó chọn `ACTION = "prepare"`, `"info"`, `"check"`, `"crop_page"` hoặc `"gui"` để [cắt bằng chuột](#cắt-bằng-chuột). Lưu từng vùng bằng mã bài, bản văn và phiên bản. Kiểm tra thứ tự các phần trong `01_nguon/` trước khi chuyển qua OCR.

### Bước 4. OCR hoặc trích TXT thô

Dùng [02_ocr/OCR_viet.ipynb](02_ocr/OCR_viet.ipynb) cho nhánh tiếng Việt / Kaggle–Colab và [02_ocr/OCR_han.ipynb](02_ocr/OCR_han.ipynb) để chạy OCR Hán kèm đối chiếu chéo PaddleOCR + CLC và hiệu đính thủ công.

1. Chọn nguồn và bản văn trong `SELECTED_JOBS`. Chạy thử một ảnh ở mục 10 để xem vùng nhận dạng và thứ tự các dòng. Xem [mục OCR bên dưới](#ocr-trên-kaggle--google-colab) cho từng loại ảnh.
2. Chạy mục 11 cho phạm vi đã chọn. Đưa TXT từng ảnh và metadata về đúng cây `02_ocr_tho/` trên máy local. Giữ tên thư mục bài, bản văn và tên `phanNNNN_pdfpNNNN` để truy ảnh.
3. Với Việt Bắc sứ, dùng hai TXT lớp chữ đã lưu trong `01_nguon/` làm đầu vào làm sạch.

### Bước 5. Làm sạch TXT

Dùng [clean_text.ipynb](clean_text.ipynb) hoặc [03_text_cleaning.ipynb](03_text_cleaning.ipynb) trên máy local.

1. Kiểm tra `PROJECT_ROOT`, `SELECTED_CODES` và `SELECTED_KINDS`. `INPUT_GRANULARITY = "parts"` đọc TXT từng ảnh. Đặt `WRITE_OUTPUTS = False` ở lượt xem trước.
2. Duyệt `duyet_lam_sach.csv` và đối chiếu ảnh cho các dòng bị đánh dấu (có thể dùng thêm [hai prompt làm sạch Hán/Việt](#làm-sạch-văn-bản-clean_textipynb--03_text_cleaningipynb-và-kiểm-tra-thủ-công-với-llm) để trợ giúp phát hiện lỗi trước khi bạn duyệt).
3. Đặt `WRITE_OUTPUTS = True` và chạy lại đến mục 5.2 để ghi TXT vào `03_text_sach/`. Notebook báo xung đột nếu tệp đích có nội dung khác. Nếu đã có TXT đúng bài và phiên bản, dùng bộ đó làm đầu vào bước 6.

Thư mục `san_pham/TV02/05_quan_ly/<RUN_NAME>/` (hoặc `TV04`) chứa `duyet_lam_sach.csv`, `work_manifest.json`, `changes.jsonl` và `summary.json`. Với thiết lập `parts`, tên lượt mặc định là `clean_v02_parts` / `clean_v04_parts`. Nếu TXT đã được rà soát lần sau, dùng manifest của lần rà soát tương ứng với SHA-256 hiện tại để lần về dòng OCR và ảnh.

### Bước 6. Tách đơn vị và tạo bản nháp

Dùng [dong_hang.ipynb](dong_hang.ipynb) (hoặc [04_text_segmentation.ipynb](04_text_segmentation.ipynb) & [05_text_alignment.ipynb](05_text_alignment.ipynb)) trên máy local. Chọn cell của sách cần chạy. Ví dụ tạo nháp cho bài 131 trong cell **Thơ văn Lý–Trần**:

```python
CHAY_HANG_LOAT = False
SO_BAI = 131
CHE_DO = "nhap"
```

| Cấu hình | Cách dùng |
|---|---|
| `CHE_DO = "nguon"` | Xem TXT có số dòng. `TU_KHOA` lọc các dòng chứa từ cần tìm. |
| `CHE_DO = "nhap"` | Tách đơn vị, dóng Hán–âm bằng code Lab và hai từ điển, xử lý Hán–nghĩa qua CLC, tạo prompt thơ nếu có bản thơ. |
| `CHAY_HANG_LOAT = True` | Điền `DANH_SACH_BAI`, ví dụ `[131, 140, 148]`. Với Thi Đình dùng số bài 14–18. |
| `THE_LOAI`, `THE_LOAI_THEO_BAI` | Chọn tách theo dòng thơ hoặc theo câu văn xuôi. |
| `TIEU_DE_THEO_BAI` | Số dòng đầu cần bỏ của từng bản. Chỉ thay khi đã xác định đúng ranh giới nội dung. |

`nhap` dùng `clc_response.json` khi `request_sha256` khớp nội dung yêu cầu hiện tại. Khi thiếu cache hoặc hash lệch, chế độ `nhap` thông thường sẽ thử gọi CLC nếu kernel có `CLC_API_KEY`. Nếu chủ động cần tạo phản hồi mới, dùng cell **Nạp token CLC** với ô nhập ẩn. Hai prompt bên dưới làm việc với phản hồi đã lưu. Khi cần chạy lại ngoại tuyến, dùng Prompt 2 để chặn nhánh gửi request mới trong lượt chạy.

Notebook in đường dẫn thư mục duyệt. Ví dụ với `bai0140`:

```text
san_pham/TV02/CV06_CPO_12/05_quan_ly/dong_hang/TV02/bai0140/
```

| Tệp | Dùng khi nào |
|---|---|
| `draft.json` | Tra `work`, `fingerprint`, cấu hình tách, `units`, TXT nguồn và các liên kết nháp. |
| `clc_request.json`, `clc_response.json` | Đối chiếu đầu vào và toàn bộ nhóm CLC đã lưu. |
| `clc_mismatch.json` | Xác định vị trí báo lệch. Đối chiếu `work`, `fingerprint` và `status.CLC` trong nháp trước khi dùng. |
| `poetry_prompt.json`, `poetry_result.json` | Đọc câu Hán và thơ theo ID, lưu nhóm đề xuất và `needs_review` nếu có. |
| `review_template.json`, `review.json` | Tạo và sửa bản duyệt. Chế độ xuất đọc `review.json`. |

### Bước 7. Dóng hàng, xem bảng và duyệt cặp

Dùng [dong_hang.ipynb](dong_hang.ipynb) và [hai prompt Codex](#hai-prompt-codex). Lượt `nhap` ở bước 6 cũng tạo liên kết Hán–âm và lấy nhóm Hán–nghĩa từ CLC khi có phản hồi phù hợp. Dùng kết quả đó để tiếp tục ghép thơ và rà từng bài.

1. Chạy [Prompt 1](#prompt-1-ghép-thơ-và-rà-lỗi-clc) để ghép thơ và rà mismatch CLC.
2. Dùng `review.json` để chốt `links.am`, `links.nghia` và `links.tho`. Với bài mới chỉ có đề xuất thơ, tạo bản duyệt từ `review_template.json`, đưa các nhóm thơ khớp fingerprint vào `links.tho` và tính lại `skipped` theo toàn bộ ba danh sách.
3. Trong mỗi cột, các ID trong một nhóm phải liền nhau. Các nhóm đi theo thứ tự nguồn và mỗi ID chỉ được dùng một lần trong cột đó. Một ID Hán có thể đi với cả âm, nghĩa và thơ. Ghi lý do vào `skipped` cho từng ID chưa dùng. Hán còn ghép ở ít nhất một trong ba cột thì không thêm vào `skipped`.
4. Với `needs_review`, tra ID trong `draft.json` để đọc đúng câu. Đọc thêm hai dòng kế cận, rồi dùng ảnh nguồn nếu cần xác nhận ký tự. [Prompt 2](#prompt-2-truy-vết-sửa-txt-sạch-và-dóng-lại) thực hiện truy vết, sửa lỗi có bằng chứng và dóng lại sau khi TXT thay đổi.

Để xem nhanh một **bản duyệt có sẵn** theo bốn cột, chạy cell sau trong notebook local (ví dụ với `bai0140`):

```python
from pathlib import Path
import sys

import pandas as pd
from IPython.display import display

root = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

from cong_cu.dong_hang import HEADERS, make_rows, read_json, verify_identity

book, work = "CPO_12", "bai0140"
folder = root / "san_pham" / "TV02" / f"CV06_{book}" / "05_quan_ly" / "dong_hang" / "TV02" / work
draft = read_json(folder / "draft.json")
review = read_json(folder / "review.json")
verify_identity(review, draft["work"], draft["fingerprint"])
rows = make_rows(draft["units"], review["links"])
display(pd.DataFrame([row["cells"] for row in rows], columns=HEADERS))
```

`work` nhận diện sách, bài, thành viên và mục nếu có. `fingerprint` nhận diện phiên bản nguồn và cách tách đơn vị. Trong `units`, `start` và `end` là chỉ số ký tự trong TXT đã giải mã UTF-8. `text[start:end]` lấy từ `start` đến ngay trước `end`. `part` chỉ phần ngăn bởi `\f` trong TXT. Dùng manifest để xác định trang PDF thực tế. Sau khi sửa TXT, dùng Prompt 2 để dựng lại đơn vị và ánh xạ ID.

### Xuất tệp nộp

Dùng [dong_hang.ipynb](dong_hang.ipynb) (hoặc [05_text_alignment.ipynb](05_text_alignment.ipynb)) với chế độ `xuat`.

1. Chốt các cặp trong `review.json`, kiểm tra lý do `skipped` rồi lưu `"approved": true`.
2. Trong cell đúng sách của `dong_hang.ipynb`, chọn bài đã duyệt. Ví dụ:

   ```python
   CHAY_HANG_LOAT = False
   SO_BAI = 140
   CHE_DO = "xuat"
   ```

   Để xuất nhiều bài, đặt `CHAY_HANG_LOAT = True` và điền `DANH_SACH_BAI` bằng số các bài đã duyệt. `xuat` dùng cấu hình từ `draft.json` và kiểm tra fingerprint với TXT hiện tại.
3. Lấy `*_parallel.xlsx` và `*_parallel.tsv` trong thư mục từng bài. Ví dụ:

   ```text
   san_pham/TV02/CV06_CPO_12/04_dong_hang/bai0140/
   ├── CPO_12_bai0140_parallel.xlsx
   ├── CPO_12_bai0140_parallel.tsv
   └── notes.xlsx
   ```

4. Mở sheet `DONG_HANG` để kiểm tra bốn cột **Hán – Dịch âm – Dịch nghĩa – Dịch thơ**. TSV lưu cùng dữ liệu UTF-8, với mỗi hàng gồm bốn ô ngăn bằng tab và không có hàng tiêu đề. `notes.xlsx` ghi các đơn vị bỏ lại, ghi chú links và chẩn đoán Lab. Ô trống có thể là bản văn thiếu trong nguồn hoặc chưa có liên kết. Kiểm tra `notes.xlsx` và `draft.json` để xác định lý do trước khi tính số cặp hợp lệ.

Bộ xuất TV02 ngày 21/11/2026 đã ghi **5 bài Thi Đình và 77 bài Lý–Trần**, tổng **1.273 hàng**. Phiên đó kiểm tra Excel khớp TSV. **32 bài có TXT nghĩa nhưng chưa có nhóm nghĩa trong bảng**. Nếu đang dùng bộ xuất này, mở `04_dong_hang/` của từng sách. Báo cáo phiên rà soát nằm tại `san_pham/TV02/05_quan_ly/ra_soat_dong_hang_2026-11-21/BAO_CAO.md`.

### Lỗi thường gặp khi dóng hoặc xuất

| Hiện tượng | Cách xử lý |
|---|---|
| `approved=false` | Mở `review.json` của đúng bài và chốt cặp trước khi cho phép xuất. |
| Lệch `work` hoặc `fingerprint` | Mở đúng thư mục bài. Nếu nguồn hoặc cách tách đã thay đổi, chạy quy trình ánh xạ lại ở Prompt 2. |
| CLC có cache nhưng cột nghĩa chưa lên | Đọc `status.CLC` trong `draft.json`. Với lỗi lệch văn bản còn hiệu lực, dùng Prompt 1. Với request đổi, dùng quy trình offline ở Prompt 2 và ghi phần nghĩa còn thiếu. |
| Thơ đã có JSON nhưng bảng xuất còn trống | Xem `links.tho` của `review.json`. Đưa nhóm thơ khớp fingerprint vào bản duyệt và tính lại `skipped`. |
| Tệp đích đã có nội dung khác | Bảo toàn bản xuất cũ và lưu riêng sau khi bạn quyết định dùng bản mới. Pipeline chặn ghi đè xung đột. |
| Ông/bà, tên riêng hoặc chữ Hán khác giữa hai bản | Đối chiếu ảnh của từng bản rồi đánh giá theo nghĩa. Chỉ hiệu đính TXT khi có lỗi được nguồn xác nhận. |

---

## Hai prompt Codex

Phần này chứa hai prompt Codex dùng để hậu kiểm và truy vết dóng hàng. Nội dung đầy đủ của hai prompt nằm ở [Phụ lục cuối tài liệu](#phụ-lục-các-prompt-tham-khảo).

- **[Prompt 1 — Ghép thơ và rà lỗi CLC](#prompt-1-ghép-thơ-và-rà-lỗi-clc):** dùng sau khi tạo nháp cho các bài cần xử lý. Ghép Hán–thơ, rà mismatch CLC và lưu bản chờ duyệt.
- **[Prompt 2 — Truy vết, sửa TXT sạch và dóng lại](#prompt-2-truy-vết-sửa-txt-sạch-và-dóng-lại):** dùng khi cho phép Agent sửa TXT sạch và chạy lại lô bài với kiểm tra offline.

---

## Chạy ngay

Mở [01_source_preparation.ipynb](01_source_preparation.ipynb), chạy Cell 1 để nạp môi trường rồi thực thi cell của từng tác phẩm (`CPO_09` Bắc sứ, `CPO_10` Hịch tướng sĩ, `CPO_12` Lý–Trần, `CPO_11` Văn sách Thi Đình) với số trang bạn tự nhập (`CUSTOM_PAGES` hoặc `PROMPT_INPUT_PAGES = True`) và `ACTION = "info" | "prepare" | "check" | "summary" | "crop_page" | "text_lines" | "gui"`.

Môi trường `.venv` nếu chưa có cần tạo với Python 3.11 trở lên có Tkinter:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Repo GitHub chỉ chứa mã nguồn, hướng dẫn và tests. PDF nguồn, `Guideline.pdf`, sản phẩm cắt, lịch sử thao tác và `.venv` được giữ ở máy, không đưa vào Git. Sau khi clone, đặt các PDF vào `data/` theo [hướng dẫn dữ liệu](../data/README.md) hoặc sửa `TEN_NGUON` trong [ten_file.py](../ten_file.py). Các tests tích hợp cần những PDF này; thiếu dữ liệu sẽ được ghi nhận là bỏ qua, không được tính là đã kiểm tra thành công.

**`MA_DE_TAI` trong [ten_file.py](../ten_file.py) phải khớp mã đăng ký của nhóm.** Giữ cấu hình bạn đã đặt; chỉ đổi khi cần sửa mã đăng ký. Đổi mã sẽ đổi thư mục đầu ra của các lần chạy sau; tool không tự di chuyển sản phẩm cũ.

### Cắt bằng chuột

1. Mở đúng script của sách. Tool kiểm tra bản sao gốc rồi hiển thị PDF.
2. Nhập **mã tác phẩm**, ví dụ `bai0131`. Đây là mã bài, không phải trang PDF.
3. Chọn **Hán / Dịch âm / Dịch nghĩa / Dịch thơ**.
4. Kéo chuột khoanh đúng vùng của bản văn đó, bấm **Lưu vùng vào tác phẩm** hoặc `Ctrl+S`.
5. Nếu bản văn còn tiếp ở trang sau, mở trang tiếp theo, **giữ nguyên mã tác phẩm, loại bản và phiên bản**, rồi chọn/lưu tiếp. Tool lưu các PNG vào cùng thư mục tác phẩm/bản văn.
6. Làm tương tự cho các bản còn lại. Nút **Xem đủ/thiếu bản văn** giúp kiểm tra phần đã cắt.

Thứ tự bạn bấm lưu là thứ tự các phần trong mỗi bản văn. Không suy ra thứ tự chỉ từ số trang: đôi khi phải quay lại phần trước. Lưu lại đúng vùng với cùng cấu hình thì tool bỏ qua bản trùng. Vùng gần trùng sẽ có cảnh báo trước khi lưu thêm.

### Xem, sửa và hoàn tác

- Danh sách bên phải hiển thị các vùng của bài/phiên bản đang chọn. Bấm một dòng để xem ảnh hoặc đoạn TXT. Khung xanh trên trang là vùng đã lưu; khung xám là vùng của bài khác trên cùng trang.
- **Chỉnh vùng đã chọn**: mở lại đúng trang và khung cũ. Khoanh lại rồi bấm **Lưu thay khung vùng đã chọn**. Giữ nguyên mã bài, bản văn, phiên bản và số phần. Có thể đổi trang để sửa phần đã lấy nhầm trang. Với vùng TXT, chọn lại đoạn chữ.
- **Bỏ vùng đã chọn**: bỏ vùng khỏi sản phẩm đang dùng; TXT ghép được cập nhật theo các phần còn lại. Các phần khác giữ số thứ tự cũ để không mất mã tham chiếu.
- **Hoàn tác thao tác gần nhất**: khôi phục trạng thái trước lần lưu, thay, bỏ vùng hoặc xác nhận tiến độ. Có thể hoàn tác nhiều lần, kể cả sau khi mở lại tool.
- Dữ liệu vùng lưu từ bản tool cũ vẫn xem/sửa/bỏ được. Hoàn tác chỉ áp dụng cho các thao tác được thực hiện từ bản nâng cấp có lịch sử.
- Chỉnh vùng giữ nguyên loại bản văn. Nếu lưu sai loại Hán/dịch nghĩa, bỏ vùng cũ rồi chọn đúng loại và lưu lại; có thể hoàn tác thao tác bỏ nếu cần.

Các bản trước/sau được lưu trong `05_quan_ly/lich_su/`. Không xóa thư mục này nếu còn cần hoàn tác. Lịch sử sử dụng thêm dung lượng theo số thao tác; metadata được nén để giảm dung lượng. File đã sửa bên ngoài tool sẽ được giữ và báo xung đột. Nếu lần ghi bị ngắt, lần mở tiếp theo phục hồi trạng thái trước thao tác chưa hoàn tất.

### Mặc định nguồn, nhớ vị trí và tiến độ

- Nguồn riêng bản Việt của Bắc sứ mặc định **Dịch nghĩa**; nguồn riêng Hán mặc định **Hán**. Với PDF chứa nhiều bản văn, bạn vẫn chọn đúng loại vùng cần lấy. Nếu chọn loại khác ngôn ngữ của nguồn riêng, tool cảnh báo trước khi lưu.
- Tool nhớ trang gần nhất của từng nguồn, bài, loại bản văn, phiên bản và mức phóng trong `05_quan_ly/phien_lam_viec.json`; mở lại để tiếp tục từ phiên đã lưu.
- **Tiến độ bốn bản văn** hiển thị Hán, dịch âm, dịch nghĩa, dịch thơ theo từng bài. Chỉ bấm **Đã kiểm tra đủ / bỏ xác nhận** sau khi bạn đã đối chiếu trọn bản văn. Thêm, sửa hoặc bỏ vùng sẽ đưa bản văn đó về trạng thái đang làm.
- Trạng thái đủ vùng do bạn xác nhận, không chứng minh câu đã dóng hàng đúng hoặc đã đạt chỉ tiêu cặp. Ghi nhận không có bản văn chỉ dùng khi nguồn thực sự không có.

Nguồn và bản sao được kiểm tra hash khi mở/chuẩn bị. Các lần lưu tiếp trong cùng phiên tái sử dụng kết quả khi đường dẫn, dung lượng và thời gian file không đổi. Nếu thông tin file thay đổi, tool kiểm tra lại; `--check` luôn đọc và kiểm tra đầy đủ.

Nếu sách thực sự không có một bản dịch, ghi lý do ở ô ghi chú rồi bấm **Ghi nhận không có bản này**. Không dùng chức năng này để bỏ qua phần chưa đọc. Tool không tạo bản dịch hoặc file TXT rỗng thay phần thiếu.

**Chú thích:** ở bước 3 ảnh còn giữ nguyên các chỉ dấu trong thân bài. Khoanh phần nội dung chính, để khối khảo đính/chú thích riêng ngoài vùng. Việc loại chú thích không thuộc nội dung Hán và làm sạch ký tự là bước 5, không phải sửa ảnh nguồn.

### Cắt TXT và PDF Text

- **TXT UTF-8 có sẵn:** bấm **Mở TXT để chọn chữ**, bôi đen đúng phần cần lấy rồi lưu. Mã tác phẩm, loại bản và phiên bản lấy từ cửa sổ chính. File nguồn được sao lưu.
- **PDF có lớp chữ:** khoanh vùng như bình thường, bật **Lấy thêm lớp chữ PDF**. Tool xuất PNG và TXT thô của vùng. Đây là tùy chọn trích xuất ở bước 4; không tự OCR hoặc coi text là đã sạch. PDF Text xoay chưa hỗ trợ trích chữ vùng.
- **PDF scan:** chỉ xuất PNG. Nếu bật lấy chữ nhưng vùng không có text, tool báo lỗi và không tạo TXT rỗng. Nếu chữ nguồn bị lỗi font thì TXT vẫn cần sửa.
- **Một phiên bản của một bản văn dùng một chế độ:** ảnh PDF, PDF có trích text, hoặc TXT. Muốn đổi chế độ, dùng phiên bản mới để tránh ghép TXT thiếu một nửa.

Lệnh cắt TXT theo dòng (thay đường dẫn bằng TXT thật):

```powershell
.\.venv\Scripts\python.exe .\cat_ly_tran.py --text-file "duong_dan_text.txt" --lines 10 20 --work bai0131 --kind dich_nghia
```

TXT ghép có đuôi `_trich_xuat_tho.txt`, chưa phải `han.txt`/`viet.txt` sạch. Công cụ chỉ giữ đoạn được chọn, không dịch, không cắt câu hoặc suy đoán Hán/Việt theo ký tự.

### Kiểm tra / chuẩn bị lại

Các cờ dùng được cho cả bốn script:

```powershell
.\.venv\Scripts\python.exe .\cat_ly_tran.py --prepare
.\.venv\Scripts\python.exe .\cat_ly_tran.py --info
.\.venv\Scripts\python.exe .\cat_ly_tran.py --check
.\.venv\Scripts\python.exe .\cat_ly_tran.py --summary --work bai0131
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

`--check` so SHA-256 nguồn, bản sao và sản phẩm, phát hiện file thiếu/bị sửa. Nó không kiểm tra nghĩa, thiếu câu hay đủ ranh giới tác phẩm. Hai cửa sổ có thể đọc cùng sách nhưng không được ghi cùng lúc: khóa ghi giúp tránh mất manifest.

# OCR trên Kaggle / Google Colab

Notebook: [ocr_nlp.ipynb](ocr_nlp.ipynb)

## Hai nhánh nhận dạng

| Nguồn | Pipeline |
|---|---|
| Hán Thi Đình, Bắc sứ | PaddleOCR detection cột dọc + recognition v6; đọc cột phải→trái |
| Hán Lý–Trần | Tách hàng ngang từ ảnh nguồn → recognition v6; trái→phải, trên→dưới |
| Ảnh dịch âm, dịch nghĩa, dịch thơ | Paddle TextDetection → nắn/cắt từng dòng trong bộ nhớ → VietOCR |
| TXT Bắc sứ Việt | Sao chép nguyên byte, không OCR |

Chọn nhánh bằng `JOBS[job]["kind"]`, không dựa vào nhận diện ngôn ngữ hay tên ảnh.
Detector Việt là instance riêng dùng checkpoint detection hiện có.
Chỉ nạp các nhánh có nguồn ảnh trong danh sách kiểm kê đã chọn.
`RUN_NAME` có nền `paddle_v6b1_layout_v03` và tự thêm `_bac_gray_scale` hoặc `_bac_binary`.
Nhánh Hán giữ `PP-OCRv6_medium_rec`, `HAN_REC_BATCH_SIZE=1`.
`HAN_LAYOUTS` khai báo riêng từng nguồn; không áp dụng một chiều đọc chung cho cả ba sách.

VietOCR mặc định `vgg_transformer`; đổi sang `vgg_seq2seq` ở cell 1 nếu muốn thử.
Chỉnh `VIETOCR_WEIGHTS` khi có checkpoint riêng; để rỗng dùng checkpoint chính thức.
Config lấy từ commit cố định của repository VietOCR; metadata ghi hash config và checkpoint.
`VIETOCR_MAX_WIDTH`, `VIETOCR_MAX_LENGTH`, `VIET_CROP_PADDING` điều chỉnh ảnh dòng và giới hạn giải mã.
Mặc định `VIETOCR_MAX_WIDTH=512` theo mẫu đã kiểm tra: chiều cao input là 32, chiều rộng tối đa 512.
Dòng ngắn giữ chiều rộng theo tỉ lệ, không bị ép thành 512. Model Hán giữ cấu hình hiện có.
Các dòng bị ép chiều rộng, có khả năng chạm giới hạn giải mã, rỗng hoặc không có điểm tin cậy được đánh dấu trong JSON.
`VIET_READING_ORDER="top_to_bottom"` dành cho vùng một cột; cần xem thử trang nhiều cột.
`REC_SCORE_THRESHOLD` áp dụng cho nhánh Paddle cột dọc; Hán hàng ngang và Việt giữ cả dòng điểm thấp để rà soát.

## Tách hàng ngang Hán Lý–Trần

Các chữ thơ cách đều thành ô vẫn đọc theo hàng ngang. Chỉ sắp lại box đứng sẽ ghép sai câu.
Helper `han_row_helpers` tìm khoảng trắng giữa các hàng bằng ảnh xám thu nhỏ/lọc nhiễu,
nhưng ảnh đưa vào recognition là crop RGB giữ nguyên pixel nguồn, không phải ảnh đã lọc.
Mỗi hàng được nhận dạng riêng bằng v6 + batch 1, gồm cả tiêu đề/dòng phụ và dấu câu cuối hàng.
Tọa độ `rec_polys` và `line_details.crop_box` theo pixel của ảnh nguồn, không phải ảnh preview.

`HAN_ROW_SETTINGS` điều chỉnh ngưỡng mực, nối khe nhỏ và lề của hàng.
`HAN_IMAGE_OVERRIDES` đã có ngoại lệ hình học cho các trang nhiễu/đề mục ngắn trong bộ TV02.
Khóa là `job/relative_path`, ví dụ:

```python
HAN_IMAGE_OVERRIDES["ly_tran_han/CPO_12_TV02_bai0131_han_v01/phan0001_pdfp0187.png"] = {
    "row_settings": {"min_ink_fraction": 0.02},
}
```

Khi cần cắt tay, dùng `row_boxes=[[x1,y1,x2,y2], ...]` theo ảnh nguồn; không cần sửa ảnh gốc.
`order_indices` chỉ thay thứ tự các vùng đã nhận ra và phải chứa đủ mọi ID đúng một lần.
Trang có khối riêng/chữ nhỏ vẫn cần xem preview; không dùng số cảnh báo bằng 0 làm chứng nhận đủ chữ.
Preview/metadata ghi ID các vùng ngắn/nhỏ và các cặp vùng dọc tách rời để kiểm tra thứ tự khối.
Đổi nguồn ảnh thì phải rà lại các ngoại lệ; không sao chép tọa độ giữa hai bản scan khác nhau.

## Bắc sứ Hán: hai mode trong luồng chính

Cell 1:

```python
BAC_PREPROCESS_MODE = "gray_scale"  # Hoặc "binary".
```

`gray_scale` dùng bản xám đã khử đỏ, cân nền và chỉnh tone (`soft_gray` của phép thử).
`binary` dùng cùng các bước đó rồi nhị phân Otsu (`binary_otsu`). Cả hai là RGB 3 kênh,
giữ nguyên kích thước và tọa độ; tham số chính ở `BAC_MAIN_PREPROCESS_PARAMS`.
Các tham số thử `BAC_PREPROCESS_PARAMS` ở 10e được giữ độc lập, không âm thầm đổi luồng chính.

Helper tiền xử lý lõi và cache nằm **trước `ocr_helpers` trong mục 9**. Cell 10b và 11 tự áp dụng
cho `bac_su_han`; Thi Đình, Lý–Trần và Bắc sứ Việt TXT giữ luồng tương ứng.
Preview 10b dùng đúng ảnh đã xử lý để vẽ khung và cắt crop. Khi chạy cell 11, ảnh này được lưu
cạnh kết quả với tên `<tên_ảnh>.input.png`, cùng TXT, JSON Paddle và metadata có mode/tham số/hash.
Cache chỉ dùng lại khi nguồn, tham số và hash ảnh khớp; cache/kết quả sửa ngoài notebook được giữ và báo lỗi.

Thứ tự Bắc sứ: nhóm vùng theo cột → trên xuống dưới trong cột → cột phải sang trái.
Metadata ghi `column_groups` và ID gán cột chưa rõ; các số/chữ nhỏ vẫn được giữ để rà soát.
Trang nhiều khối phức tạp có thể cần `HAN_IMAGE_OVERRIDES[...]["order_indices"]`.
`BAC_COLUMN_CENTER_RATIO` điều chỉnh dung sai nhóm cột; đây là heuristic, không chứng nhận đúng toàn trang.

Đổi mode rồi chạy lại cell 1 và helper mục 7/9; thư mục phiên tự tách theo mode.
Nếu chỉnh tham số trong cùng mode, đổi thêm nền `RUN_NAME`. Không tái sử dụng thư mục kết quả cũ với cấu hình mới.
10e/10f bỏ qua bước tiền xử lý chính khi OCR ảnh thử đã lưu, tránh xử lý hai lần.

Toàn bộ cấu hình và xử lý chính được sửa trực tiếp trong `ocr_nlp.ipynb`.

Mục 10a xem riêng detection Việt; mục 10b mặc định xem ảnh Hán và crop của Paddle.
Trong 10b đặt `TEST_JOB="thi_dinh_han"`, `"ly_tran_han"` hoặc `"bac_su_han"`, đổi `TEST_INDEX` để chọn ảnh.
Job phải có trong `SELECTED_JOBS` và kiểm kê; nếu mới thêm job Hán thì chạy lại mục 6–9 để nạp nhánh Hán.
`PADDLE_CROP_IDS` chọn ID vùng cụ thể, hoặc để `None` lấy tối đa `PADDLE_CROP_COUNT=3` vùng đầu.
Thi Đình/Bắc sứ dùng `CropByPolys` của PaddleX 3.7, có thể nắn/xoay chữ dọc sang ngang.
Lý–Trần hiển thị đúng crop hàng ngang đã đưa vào recognition, không dùng toán tử xoay cột.
Bảng `source_w/source_h` và `crop_w/crop_h` cho biết kích thước trước/sau crop; `source_h_w/crop_h_w` là tỉ lệ cao/rộng.
Các crop ở 10b chưa phải tensor sau preprocessing của Paddle recognition, không áp dụng width 512 của VietOCR.
Preview hiển thị JPEG để tránh nhánh mã hóa PNG của Pillow/IPython, không thay đổi ảnh nguồn.
Số xanh ở 10a/10b là số dòng TXT từ 1; bảng theo cùng thứ tự, giữ `index_model` từ 0 và tọa độ để truy vết.
Các vùng trong diagnostic 10c/10d vẫn được chọn bằng ID gốc.
JSON Việt chứa kết quả detector gốc, dự đoán VietOCR, tọa độ và vùng crop; JSON Hán cột dọc giữ Paddle gốc.
JSON Hán hàng ngang chứa vùng hàng, tham số tách và kết quả recognition gốc của từng crop.
`.meta.json` lưu `review.reading_map`: dòng TXT ↔ index_model ↔ polygon nguồn, cùng cấu hình/hash.
Không sinh thêm PDF hoặc lưu các dòng crop vào bộ nguồn. Chưa làm sạch hoặc dóng hàng.

## Mục 10c: kiểm tra đầu vào và recognition Việt

Chạy helper và nạp lại model ở mục 8 để có `prepare_input`/`predict_prepared`, rồi mục 9 và 10c.
Không cần chạy OCR hàng loạt để làm bài kiểm tra này. Cell 10c dùng lại các model đang trong bộ nhớ.

| Thành phần | Nội dung xem được |
|---|---|
| Detection | Trang có khung và ID vùng gốc |
| Crop | Ảnh dòng sau cắt/nắn, trước preprocessing |
| Input thực | Ảnh khôi phục từ chính tensor NCHW đưa vào VietOCR, shape, dtype và min/max |
| Recognition | Toàn bộ chuỗi dự đoán, số token, điểm tin cậy, dừng vì EOS hay giới hạn độ dài |
| Đối chiếu | CER, số ký tự thay/xóa/chèn khi bạn nhập nguyên dòng chuẩn |

Chỉnh các biến ngay trong cell 10c:

```python
DEBUG_JOB = "thi_dinh_dich_am"
DEBUG_IMAGE_INDEX = 0
DEBUG_LINE_IDS = [17, 16]  # ID xanh trên detection; đổi theo ảnh đang xem.
DEBUG_WIDTHS = [512, 1024]
DEBUG_DECODE_LIMITS = [128, 256]
DEBUG_REFERENCES = {}     # Nhập {17: "nguyên văn đầy đủ dòng 17 trong ảnh"} để đo lỗi.
DEBUG_SAVE = False
```

Mặc định lấy tối đa ba dòng đầu theo thứ tự đọc và dùng giới hạn chiều rộng 512.
Đặt `DEBUG_WIDTHS=[512, 1024]` nếu muốn so sánh lại.
Các thử nghiệm không thay `VIETOCR_MAX_WIDTH`/`VIETOCR_MAX_LENGTH` của luồng hàng loạt.
`EOS` là kết thúc chuỗi model, không phải xác nhận đã đọc trọn câu hoặc trọn dòng.
Không có dòng chuẩn thì CER để trống; confidence cao và số cảnh báo bằng 0 không chứng minh đọc đủ.
CER so ký tự thô, kể cả dấu/khoảng trắng; không tự chuẩn hóa hoặc sửa dự đoán.

`DEBUG_SAVE=True` xuất JSON/CSV và PNG không nén của crop/input vào thư mục mới
`05_quan_ly/kiem_tra_vietocr/<timestamp_uuid>/`, không ghi đè kết quả OCR.
Ảnh hiển thị trong cell dùng JPEG; ảnh input PNG xuất ra giữ nguyên pixel RGB để đối chiếu.
Đặt `DEBUG_RUN=False` để bỏ qua phần diagnostic khi chỉ muốn chạy các bước khác.

## Mục 10d: thử model Hán để giảm lỗi nhận dạng

Batch 1 đã giúp vùng chữ nhỏ; các lỗi thay chữ còn lại cần kiểm tra recognition.
Mục 10d so `PP-OCRv6_medium_rec` với `PP-OCRv5_server_rec` trên cùng crop PNG,
cùng batch 1. V5 hỗ trợ phồn thể, chữ dọc và viết tay theo tài liệu chính thức;
đây là ứng viên thử nghiệm, chưa có kết luận hơn v6 trên sách của bạn.

Sau mục 6–9, chạy helper 10b và helper 10c (hàm CER), rồi hai cell 10d:

```python
HAN_COMPARE_RUN = True
HAN_COMPARE_JOB = "thi_dinh_han"  # Hoặc "ly_tran_han".
HAN_COMPARE_IMAGE_INDEX = 0
HAN_COMPARE_IDS = [11, 6, 10, 12]  # Chỉ là ví dụ ID trên mẫu Thi Đình đã xem.
HAN_COMPARE_REFERENCES = {}       # {ID: "đầy đủ chữ chuẩn của toàn vùng"}.
HAN_COMPARE_SAVE = True
```

Chọn lại ID theo ảnh trong 10b. Không có dòng chuẩn thì CER để trống; không chọn model bằng confidence.
CER tổng là tổng lỗi chia tổng ký tự chuẩn, chỉ tính các vùng đã cung cấp bản chuẩn.
Nên kiểm tra ít nhất vài trang có cột ngắn/dài, chữ rõ/mờ ở từng sách để tránh chọn theo một tiêu đề.
Báo cáo JSON/CSV tùy chọn lưu vào thư mục mới `05_quan_ly/so_sanh_recognition/`.
Model thử nạp lần lượt rồi đóng; không thay instance `ocr` hoặc kết quả hàng loạt.
Sau khi có kết quả tốt hơn, đổi `RECOGNITION_MODEL` và `RUN_NAME`, chạy lại mục 6–9 rồi thử 10b.
Nếu cả hai model vẫn sai nhiều, cần dữ liệu chữ chuẩn để đánh giá hướng fine-tune; tăng DPI không phục hồi nét đã mất.

Nguồn: [Paddle recognition](https://www.paddleocr.ai/latest/en/version3.x/module_usage/text_recognition.html),
[checkpoint v5 chính thức](https://huggingface.co/PaddlePaddle/PP-OCRv5_server_rec_safetensors).

## Mục 10e: thử tiền xử lý Bắc sứ Hán

10e là phép thử độc lập; OCR hàng loạt dùng cấu hình chính ở cell 1. Cần mục 1–7,
helper `bac_preprocess_core` trong mục 9 và helper 10e để xem ảnh;
không cần GPU/model hoặc cài thêm gói xử lý ảnh. Bật và chỉnh ngay trong cell chạy 10e:

```python
BAC_PREPROCESS_RUN = True
BAC_PREPROCESS_INDICES = [0]      # Chỉ số trong kiểm kê bac_su_han, không phải số trang PDF.
BAC_PREPROCESS_ZOOM_BOX = None    # [x1,y1,x2,y2] trên ảnh nguồn; dùng khi chọn một ảnh.
BAC_PREPROCESS_SAVE = True
BAC_PREPROCESS_OCR = False
```

Ảnh gốc và mặt nạ đỏ được so với ba biến thể: xám thông thường, xám cân nền/tăng tương phản,
đen–trắng Otsu. Màu hồng trong `red_overlay` chỉ vùng bị khử; vùng tối dưới ngưỡng bảo vệ được giữ.
Khử đỏ lấy HSV từ RGB; bù nền ước lượng rồi chuẩn hóa nền giấy. Tone chỉ điều chỉnh cường độ,
không resize, xoay hoặc làm dày nét. Đầu ra OCR vẫn RGB 3 kênh, cùng kích thước ảnh nguồn.

Các tham số cần thử:

| Biến | Ý nghĩa |
|---|---|
| `red_hue_width`, `red_min_saturation` | Khoảng màu đỏ; thang HSV Pillow 0–255 |
| `red_min_r_minus_g` | Mức trội kênh đỏ so với xanh lá |
| `red_protect_max_below` | Bảo vệ vùng rất tối; tăng có thể giữ lại đỏ sẫm |
| `background_filter_size`, `background_blur` | Ước lượng nền trên ảnh thu nhỏ; không blur chữ nguồn |
| `black_point` | Ngưỡng làm đen nét tối |
| `white_point` | Giảm để xóa mờ mạnh hơn, đồng thời có thể mất nét chính nhạt |
| `tone_gamma` | Độ đậm của các mức xám trung gian |
| `binary_threshold` | `None` dùng Otsu, hoặc nhập ngưỡng 0–255 |

Lưu PNG đủ độ phân giải, bảng so sánh JPEG, tham số/hash vào một thư mục mới trong
`05_quan_ly/thu_tien_xu_ly_bac_su/`. Không ghi vào `02_ocr_tho` hoặc sửa ảnh nguồn.
Không cần chạy cell 11. Đổi tham số rồi chạy lại cell 10e sẽ tạo phép thử khác.

Nếu muốn so OCR, nạp nhánh Bắc sứ ở mục 8–9 rồi đặt `BAC_PREPROCESS_OCR=True`.
Cell chạy cùng v6/batch 1 trên ảnh gốc và ba biến thể, lưu TXT/JSON vào thư mục phép thử.
Detection có thể thay đổi; số vùng/số chữ/confidence không phải accuracy và không tự chọn model/ảnh thắng.
Kiểm tra nét mảnh, dấu câu và vùng chồng đỏ/đen trước khi quyết định bật vào pipeline chính.

## Mục 10f: xem OCR một ảnh tiền xử lý như 10b

Dùng cell 10f đã có trong notebook. Khi cập nhật Kaggle, copy nội dung cell này
vào cell tương ứng sau 10e.

Chạy 10e với `BAC_PREPROCESS_SAVE=True`, nạp v6/batch 1 ở mục 8 và helper mục 9/10b, rồi chỉnh:

```python
BAC_OCR_RUN = True
BAC_OCR_VARIANT = "soft_gray"      # Hoặc "binary_otsu", "gray_only", "original".
BAC_OCR_TRIAL_FOLDER = None        # Dùng thư mục vừa lưu ở 10e.
```

Cell hiển thị detection trên đúng PNG tiền xử lý, bảng chữ/confidence/tọa độ theo thứ tự TXT,
toàn bộ text và một số crop trước recognition. Số xanh là dòng TXT từ 1;
`BAC_OCR_CROP_IDS` dùng `index_model` từ 0 trong bảng.

Không tiền xử lý lại, không chạy cả bốn biến thể. Đổi `BAC_OCR_VARIANT` rồi chạy lại cell để thử bản khác.
Để chọn ảnh khác, đổi chỉ số và lưu lại ở 10e; hoặc nhập rõ đường dẫn phép thử cũ vào `BAC_OCR_TRIAL_FOLDER`.
Cell kiểm tra hash nguồn/ảnh dẫn xuất; nếu tham số 10e đổi mà chưa lưu thì báo lỗi, không dùng nhầm ảnh cũ.

`BAC_OCR_SAVE=True` lưu `result.txt`, `result.json` và `result.meta.json` trong thư mục con mới
`preview_ocr_<variant>_<timestamp_uuid>/` của phép thử. Metadata giữ tham số tiền xử lý, hash,
thứ tự TXT và tọa độ theo ảnh nguồn. Không ghi đè `02_ocr_tho` hoặc kết quả thử trước.

## Cài VietOCR trên Kaggle

VietOCR 0.3.13 trên PyPI ghim Pillow 10.2.0 và một số phụ thuộc training cũ.
Notebook cài wheel với `--no-deps`, rồi cài riêng phụ thuộc inference (`einops`, `gdown`, PyYAML,
requests, Pillow, NumPy và Torch/torchvision có sẵn). Cách này dành cho inference, không cấu hình training.
`pip check` có thể báo thiếu các gói training/pin Pillow của metadata VietOCR; không tự cài lại các pin này.
Cell cài đặt kiểm tra import thật của nhánh inference. Không cài, nâng hoặc hạ Torch/torchvision/CUDA/NCCL.
Checkpoint được nạp với `torch.load(..., weights_only=True)`; không vô hiệu hóa cơ chế nạp an toàn của Torch.

- **Kaggle:** Import notebook, bật Settings → Accelerator → GPU và Internet.
  Đọc Drive bằng OAuth trong Kaggle Secrets; xem phần 4 của notebook và helper
  [tao_quyen_drive.py](tao_quyen_drive.py) để đăng nhập Google một lần trên máy bạn.
- **Colab:** File → Upload notebook, bật GPU trong Runtime → Change runtime type; đăng nhập Drive như trước.
- Không cần clone PaddleOCR. Model được tải khi chạy cell nạp model.
- Notebook dùng `engine="transformers"` để chạy PP-OCRv6 bằng PyTorch có sẵn; không cài Paddle GPU.
- Ghim `transformers==5.23.0`. Bản 5.8.1 thiếu kiến trúc PP-OCRv6 medium.
  Cell cài đặt và nạp model kiểm tra registry của cả detection/recognition trước khi tải trọng số.
  Nếu phiên đang dùng bản notebook Transformers 5.8.1, cập nhật gói rồi restart kernel và chạy từ đầu;
  giữ cache model và Secret Drive. Không cần tạo lại quyền Google.
- Nếu đã chạy bộ cài cũ: lưu output, **Stop Session rồi tạo phiên Kaggle mới**, bật GPU và Internet,
  import notebook mới và chạy từ đầu. Restart kernel không phục hồi CUDA/NCCL đã bị hạ phiên bản.
  Dùng lại Secret `GOOGLE_DRIVE_CREDENTIALS` và bật quyền truy cập cho notebook.
- Cell cài đặt thử phép tính Torch, khóa bộ GPU hiện có và kiểm tra kế hoạch pip trước khi cài SDK.
  Cell 8 yêu cầu chạy kiểm kê trước để có `selected_items`. Không chạy riêng cell 8 sau khi reset kernel.

## Những chỗ cần chỉnh

| Cell | Cấu hình | Công dụng |
|---|---|---|
| 1. Cấu hình chung | `RUNTIME`, `DEVICE` | Tự nhận Kaggle/Colab và chọn GPU/CPU |
| 1. Cấu hình chung | `DRIVE_AUTH_MODE`, `DRIVE_SECRET_NAME` | Cách xác thực Drive trong Kaggle |
| 1. Cấu hình chung | `OUTPUT_ROOT`, `RUN_NAME` | Thư mục và phiên bản kết quả trên Drive |
| 1. Cấu hình chung | `ONLY_WORKS`, `MAX_IMAGES_PER_JOB` | Chọn bài hoặc giới hạn ảnh để thử |
| 1. Cấu hình chung | `READING_ORDER`, `DETECTION_MAX_SIDE` | Thứ tự chữ và độ phân giải detection |
| 2. Chọn tác phẩm | `SELECTED_JOBS` | Chạy một/nhiều tác phẩm, phiên bản |
| 2. Chọn tác phẩm | `folder_id` | Đổi nguồn Drive |
| 2. Chọn tác phẩm | `local_folder` và `INPUT_MODE="local"` | Đọc ảnh đã tải hoặc mount |
| 2. Chọn tác phẩm | `member`, `work_range`, `page_range`, `exclude_pages` | Điều chỉnh đúng phạm vi nếu thay nguồn |
| 10. Thử một ảnh | `TEST_JOB`, `TEST_INDEX` | Xem thử một ảnh trước khi chạy hàng loạt |

Ví dụ chạy riêng Bắc sứ Hán:

```python
SELECTED_JOBS = ["bac_su_han"]
```

Ví dụ chỉ thử bài 14 Thi Đình, bản Hán và dịch nghĩa:

```python
SELECTED_JOBS = ["thi_dinh_han", "thi_dinh_dich_nghia"]
ONLY_WORKS = {"CPO_11": ["bai0014"]}
MAX_IMAGES_PER_JOB = 3
```

Đặt `MAX_IMAGES_PER_JOB = None` khi chạy toàn bộ. Sau khi đổi cấu hình, chạy lại từ cell kiểm kê;
nếu đổi model, độ phân giải detection hoặc thứ tự chữ thì đổi `RUN_NAME` và nạp lại model.
Không chạy riêng cell hàng loạt với danh sách kiểm kê còn thuộc cấu hình cũ.

## Phần TV02 đã xác định trên Drive ngày 12/11/2026

| Nguồn | Bài/phạm vi | Thư mục Drive đã đọc |
|---|---|---|
| Thi Đình Hán | Bài 14–18, PDF 188–365 | [188–365](https://drive.google.com/drive/folders/1hps7wU_3W9zKuMIS8sODOELqIvl9q9Nj) |
| Thi Đình dịch âm | Cùng phạm vi | [188–365](https://drive.google.com/drive/folders/1fsilAL2E6RxMbGwbr1Os5u1VuU8NbkGo) |
| Thi Đình dịch nghĩa | Cùng phạm vi | [188–365](https://drive.google.com/drive/folders/1ECML6kWa1HNNrzygZxV-r5jmh7HEYFMA) |
| Lý–Trần Hán | Bài 131–207, PDF 187–366 | [131–207](https://drive.google.com/drive/folders/1gO2-KPt2WYeJlht5o2-4K_oASiSrtmY5) |
| Lý–Trần dịch âm | Cùng phạm vi | [131–207](https://drive.google.com/drive/folders/1pThBo58orAvzNMNIhkt_uxkVUTSBfXWv) |
| Lý–Trần dịch nghĩa | Cùng phạm vi | [131–207](https://drive.google.com/drive/folders/1_NUL5agMtARjNEXnUdRMrxofqJNo-YYj) |
| Lý–Trần dịch thơ | Các bài có bản dịch thơ trong phần 131–207 | [131–207](https://drive.google.com/drive/folders/1a40Oq7480dtI605NT6m-ylcnvT0Vus07) |
| Bắc sứ Hán | PDF 49–101, 43 ảnh sau khi bỏ 10 trang đã yêu cầu | [49–101](https://drive.google.com/drive/folders/1ceUCwOV3WvqwuAtSpsiEstteYLTBd6xO) |
| Bắc sứ Việt | Hai TXT nguồn thô, PDF 32–61 đúng mốc phân công | [32–61](https://drive.google.com/drive/folders/1PQZHzHXyUfsvpTyYfe3rhSeZpwjw-wyy) |

Đã đọc cây thư mục và kiểm tra các mốc TV02, các cặp thư mục trùng, mẫu ảnh và 43 tên ảnh Bắc sứ.
Không khẳng định đã kiểm tra nội dung từng ảnh trên Drive. Notebook sẽ kiểm kê đầy đủ trước khi OCR.
Lý–Trần dịch nghĩa có 10 cặp thư mục trùng tên (bài 176–185): một bên rỗng khi kiểm tra.
Notebook bỏ qua thư mục rỗng; nếu gặp hai file cùng đường dẫn và khác byte thì báo xung đột.

Bắc sứ Việt có sẵn TXT: giữ `mode="text"`, sao chép nguyên byte, không OCR hoặc làm sạch.
Hịch tướng sĩ là phần mẫu chung do TV1 chuẩn bị, không nằm trong các job OCR riêng của TV02.

## Đầu ra và chạy tiếp

- Mỗi ảnh: TXT UTF-8 dự đoán, JSON gốc có tọa độ/điểm tin cậy, metadata chứa hash nguồn/cấu hình.
- Mỗi bài/phiên bản đủ ảnh: một `_ocr_tho.txt`, ngăn ảnh bằng `U+000C`, giữ các file theo ảnh.
- Giữ riêng Hán, dịch âm, dịch nghĩa, dịch thơ; không ghép thành cặp dịch hay sửa ký tự.
- Kết quả lưu sau mỗi ảnh. Chỉ bỏ qua khi nguồn, cấu hình và hash kết quả còn khớp.
  Colab lưu trên Drive; Kaggle lưu tại `/kaggle/working`. Dùng Save Version hoặc tải ZIP để giữ kết quả qua phiên mới.
- TXT bị sửa tay được giữ nguyên và báo xung đột. Dùng `RUN_NAME` mới nếu muốn tạo kết quả OCR khác.
- Mọi file lỗi và ảnh không nhận ra chữ đều thể hiện trong báo cáo; chưa chứng nhận quota/chất lượng corpus.

## Kiểm tra đã thực hiện

Định dạng notebook, cú pháp từng cell và các tình huống kiểm kê, phân trang Drive, lọc TV/bài/trang,
giữ byte TXT, tiếp tục sau ngắt, bảo vệ file sửa tay, ghép đúng bài/phiên bản được kiểm tra bằng model/Drive mô phỏng.
**Chưa chạy model/GPU thật trong Kaggle/Colab hoặc thực hiện đăng nhập Google thay bạn.**
Cell thử ảnh dùng để kiểm tra tương thích runtime và chất lượng trên dữ liệu thật.

Chạy kiểm tra logic tại project, không cài Paddle hoặc tải model:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_colab_ocr_notebook.py -v
```

Tài liệu: [PaddleOCR API](https://www.paddleocr.ai/latest/en/version3.x/pipeline_usage/OCR.html),
[Engine Transformers](https://www.paddleocr.ai/latest/en/version3.x/inference_deployment/local_inference/inference_engine.html),
[Drive API](https://developers.google.com/workspace/drive/api/reference/rest/v3/files/list),
[Colab và Drive](https://research.google.com/colaboratory/faq.html).

---

# Làm sạch văn bản (`clean_text.ipynb` / `03_text_cleaning.ipynb`) và Kiểm tra thủ công với LLM

Phần này hướng dẫn sử dụng rule-based cleaning (`clean_han()`, `clean_viet()`, `build_records()`, `apply_decisions()`, `assemble_works()` — **không thay đổi thuật toán**) kết hợp kiểm tra thủ công bằng LLM Prompt (không cần API key hay gọi LLM tự động trong notebook). Xem bản hướng dẫn đầy đủ 16 mục tại [src/hanviet/cleaning/README.md](../src/hanviet/cleaning/README.md).

## Quy trình cho thành viên

1. Mở [clean_text.ipynb](clean_text.ipynb) (hoặc [03_text_cleaning.ipynb](03_text_cleaning.ipynb)), đặt `EXPORT_REVIEW = True`, `APPLY_REVIEW = False`, `WRITE_OUTPUTS = False` để chạy rule-based cleaning và xuất `duyet_lam_sach.csv`.
2. Đọc `raw`, `clean`, `automatic_rules`, `reasons`, `context_before`/`context_after` và ảnh đối chiếu (nếu có) theo từng bài/đoạn nhỏ.
3. Sao chép **Prompt Hán văn** hoặc **Prompt Việt** trực tiếp bên dưới gửi cho ChatGPT, Gemini, Claude hoặc Coding Agent.
4. Nhận bảng đề xuất hiệu chỉnh; tự đối chiếu từng đề xuất với ảnh nguồn (`REVIEW_PDF_PAGE`, `SHOW_FULL_PDF = True` ở mục 4.3).
5. Cập nhật quyết định vào đúng 3 cột của `duyet_lam_sach.csv`: `action` (`""`, `keep`, `replace`, `delete`, `join_next`), `replacement` (1 dòng duy nhất khi `action=replace`, không chứa TAB/xuống dòng), và `note`. Tuyệt đối không sửa 5 cột đối chiếu (`source_sha256`, `relative_path`, `clean`, `page`, `line`) và không ghi đè dòng đã được thành viên duyệt trước đó.
6. Đặt `APPLY_REVIEW = True`, kiểm tra số dòng chưa duyệt bằng `0`, rồi đặt `WRITE_OUTPUTS = True` để xuất TXT sạch ra `03_text_sach/`.

## Prompt hoàn chỉnh để làm sạch Hán văn

```markdown
Bạn là chuyên gia nghiên cứu Hán văn cổ, Hán Nôm, văn học trung đại Việt Nam, hiệu đính văn bản lịch sử và xử lý ngôn ngữ tự nhiên (NLP).

Tôi đang xây dựng bộ ngữ liệu song ngữ Hán–Việt phục vụ đồ án dóng hàng ở cấp câu hoặc đoạn. Văn bản Hán dưới đây đã trải qua quá trình OCR hoặc trích xuất trực tiếp, hiệu đính OCR và xử lý bằng thuật toán làm sạch văn bản. Hãy hỗ trợ tôi kiểm tra, phát hiện lỗi còn sót và đề xuất hiệu chỉnh trước khi tôi thực hiện kiểm tra thủ công.

**1. Kiểm tra độ trung thực với nguồn**

- Đối chiếu văn bản sau khi làm sạch với văn bản thô, kết quả PaddleOCR, CLC OCR và ảnh nguồn nếu được cung cấp.
- Phát hiện ký tự bị nhận dạng sai, thiếu, thừa hoặc bị lặp.
- Kiểm tra xem thuật toán làm sạch có vô tình loại bỏ nội dung chính hay không.
- Chỉ khôi phục nội dung khi có bằng chứng từ nguồn.
- Không tự sáng tác, phục dựng hoặc bổ sung chữ chỉ dựa trên suy đoán ngữ nghĩa.
- Không tuyên bố đã đối chiếu ảnh nếu tôi chưa cung cấp ảnh.

**2. Kiểm tra lỗi nhận dạng chữ Hán**

Chú ý các ký tự có hình dạng gần giống nhau như 土/士, 未/末, 己/已/巳, 日/曰, 王/玉, 千/干; các chữ có bộ thủ gần giống; chữ bị mất nét; ký tự bị dính; ký tự bị tách; ký tự xuất hiện bất thường; và các vị trí PaddleOCR và CLC OCR cho kết quả khác nhau.

Không sử dụng những cặp chữ trên như quy tắc thay thế tự động. Phải xét văn bản nguồn và ngữ cảnh của từng trường hợp.

**3. Bảo toàn đặc điểm Hán văn cổ**

- Giữ nguyên chữ Hán phồn thể, dị thể tự và ký tự Hán hiếm.
- Không chuyển chữ phồn thể sang giản thể.
- Không thay thế chữ hiếm bằng chữ phổ biến hơn khi chưa có căn cứ.
- Không hiện đại hóa văn ngôn thành tiếng Trung hiện đại.
- Không sửa cấu trúc ngữ pháp cổ để câu dễ hiểu hơn.
- Không tự thêm hoặc bỏ chữ để câu đúng niêm luật, số chữ hoặc cấu trúc đối ngẫu.
- Không thay đổi văn bản Hán để ép khớp với bản dịch tiếng Việt.

**4. Kiểm tra nội dung cần loại bỏ**

Phát hiện đầu trang, chân trang, số trang, ký hiệu thư viện, tiêu đề lặp, chỉ mục chú thích, chú thích nằm ngoài nội dung chính, ký tự rác do OCR, dòng bị lặp do nhận dạng cùng một vùng và các nội dung không thuộc phạm vi tác phẩm.

Phân biệt chú thích của người biên tập với nội dung thực sự thuộc nguyên tác. Không xóa trích dẫn kinh điển, lời đối thoại, lời tựa, đề từ, thư từ hoặc các đoạn lặp có chủ đích nếu chúng thuộc phạm vi tác phẩm.

Nếu chưa đủ căn cứ xác định một đoạn có phải chú thích hay không, hãy giữ nguyên và đánh dấu cần kiểm tra.

**5. Kiểm tra Unicode, dấu câu và khoảng trắng**

- Phát hiện ký tự điều khiển, ký tự lỗi bảng mã và Unicode bất thường.
- Đề xuất chuẩn hóa Unicode NFC khi phù hợp.
- Kiểm tra khoảng trắng sai, khoảng trắng thừa và dấu câu bị nhận dạng lặp.
- Không sử dụng NFKC hoặc phép chuẩn hóa làm mất thông tin ký tự nếu chưa có quy tắc được xác nhận.
- Không tự thêm dấu câu vào toàn bộ văn bản Hán cổ.
- Không tự thực hiện sentence segmentation ở bước này.

**6. Bảo toàn thông tin lịch sử**

Tuyệt đối chú ý tên riêng, địa danh, chức danh, niên hiệu, can chi, ngày tháng, số lượng và đơn vị đo.

Không tự thay đổi thông tin lịch sử dựa trên kiến thức của bạn. Ví dụ, không được đổi 景興十九年 thành 景興十八年 chỉ vì bạn cho rằng một mốc thời gian khác hợp lý hơn.

**7. Kiểm tra bố cục và thứ tự văn bản**

Phát hiện các dòng bị đảo thứ tự, cột chữ Hán bị đọc sai chiều, câu bị ngắt do chuyển trang, dòng bị ghép nhầm và vùng văn bản bị OCR nhiều lần.

Chỉ đề xuất ghép các dòng khi chúng thực sự thuộc cùng một phần nội dung. Đối với thơ, cần giữ nguyên ranh giới và thứ tự dòng thơ.

**8. Xử lý ký tự không đọc được**

Giữ nguyên mọi ký hiệu [MASK] đã được xác nhận.

Không tự suy đoán hoặc điền chữ vào vị trí [MASK]. Nếu nghi ngờ có thể xác định chữ đó, hãy cung cấp nhận xét và yêu cầu tôi kiểm tra ảnh nguồn.

**9. Phân loại lỗi**

Sử dụng các loại lỗi phù hợp:

- OCR_CHARACTER_ERROR
- MISSING_CHARACTER
- EXTRA_CHARACTER
- DUPLICATE_REGION
- INVALID_UNICODE
- WHITESPACE_ERROR
- PUNCTUATION_ERROR
- HEADER_FOOTER
- FOOTNOTE
- REFERENCE_MARKER
- READING_ORDER
- BROKEN_LINE
- HISTORICAL_ENTITY_ERROR
- NUMBER_ERROR
- CONTENT_LOSS
- UNREADABLE_CHARACTER
- NEEDS_MANUAL_REVIEW

**10. Yêu cầu đầu ra**

Trước tiên, trình bày bảng các lỗi và đề xuất hiệu chỉnh:

| ID hoặc dòng | Văn bản hiện tại | Đề xuất sửa | Loại lỗi | Bằng chứng và lý do | Cần đối chiếu nguồn |
|---|---|---|---|---|---|

Giữ nguyên ID và số dòng được cung cấp. Không tự tạo ID nếu dữ liệu đầu vào không có.

Phân biệt rõ ba nhóm:

- Lỗi có đủ bằng chứng để đề xuất sửa.
- Lỗi nghi vấn chưa đủ bằng chứng.
- Nội dung đã kiểm tra nhưng không cần thay đổi.

Sau đó, nếu được yêu cầu, cung cấp bản văn bản Hán sạch đề xuất dưới dạng plain text, giữ nguyên thứ tự nội dung. Những vị trí chưa đủ căn cứ sửa phải được giữ nguyên.

Không trộn nhận xét, chú thích do bạn tạo ra hoặc nhãn phân loại lỗi vào văn bản sạch.

Cuối cùng, thống kê số dòng được kiểm tra, số vị trí đề xuất sửa, số vị trí nghi vấn, số vị trí [MASK] và các vấn đề cần tôi kiểm tra thủ công. Chỉ thống kê những dữ liệu thực sự được cung cấp.

Nếu bạn đang hoạt động như một Coding Agent trong repository, hãy đọc README và schema của bảng review hiện tại trước khi đề xuất cập nhật. Không thay đổi thuật toán làm sạch, không ghi đè văn bản nguồn, không chỉnh sửa quyết định đã duyệt và không xuất bản kết quả cuối khi chưa có sự xác nhận của tôi.

Nguyên tắc quan trọng nhất: bảo toàn nguyên văn và tính trung thực của ngữ liệu quan trọng hơn việc tạo ra một văn bản có vẻ đúng ngữ pháp hoặc dễ hiểu. Khi không chắc chắn, hãy giữ nguyên nội dung và yêu cầu kiểm tra thủ công.

---

**Dữ liệu đầu vào:**

- Tên tác phẩm:
- Mã tác phẩm:
- Khoảng trang hoặc phạm vi:
- Thể loại: thơ / văn xuôi / văn sách / văn bản lịch sử
- Văn bản OCR hoặc văn bản nguồn:
- Văn bản sau rule-based cleaning:
- Kết quả OCR đối chứng (nếu có):
- Danh sách cảnh báo từ notebook (nếu có):
- Ảnh nguồn hoặc tài liệu đối chiếu (nếu có):
```

## Prompt hoàn chỉnh để làm sạch văn bản Việt

```markdown
Bạn là chuyên gia xử lý ngôn ngữ tiếng Việt, hiệu đính văn bản lịch sử, phiên âm Hán–Việt, văn học trung đại và xây dựng ngữ liệu song ngữ phục vụ NLP.

Tôi đang xây dựng bộ ngữ liệu song ngữ Hán–Việt phục vụ đồ án dóng hàng ở cấp câu hoặc đoạn. Văn bản Việt dưới đây có thể là bản dịch âm, dịch nghĩa hoặc dịch thơ, đã trải qua quá trình OCR hoặc trích xuất PDF Text, hiệu đính OCR và xử lý bằng thuật toán làm sạch văn bản.

Hãy kiểm tra, phát hiện lỗi còn sót và đề xuất hiệu chỉnh trước khi tôi thực hiện kiểm tra thủ công.

**1. Kiểm tra độ trung thực với nguồn**

- Đối chiếu văn bản sau khi làm sạch với văn bản nguồn, kết quả Tesseract OCR, VietOCR và ảnh PDF nếu được cung cấp.
- Phát hiện ký tự bị sai, từ bị thiếu, từ bị thừa, dòng bị mất hoặc nội dung bị lặp.
- Kiểm tra xem thuật toán làm sạch có vô tình xóa nội dung quan trọng hay không.
- Chỉ khôi phục nội dung tồn tại trong tài liệu nguồn.
- Không tự tạo nội dung để hoàn thiện câu bị thiếu.
- Không tuyên bố đã đối chiếu ảnh nếu không nhận được ảnh nguồn.

**2. Kiểm tra lỗi OCR tiếng Việt**

Chú ý:

- Lỗi dấu sắc, huyền, hỏi, ngã, nặng.
- Lỗi dấu mũ, dấu râu và dấu trăng.
- Nhầm chữ l với số 1, chữ O với số 0, chữ I với chữ l, cụm rn với chữ m.
- Từ bị mất ký tự hoặc thừa ký tự.
- Từ bị dính như nhàvua, triềuđình, đấtnước.
- Từ bị ngắt bất thường do OCR hoặc chuyển dòng.
- Số chỉ mục chú thích bị dính vào cuối từ.
- Dấu câu bị nhận dạng sai.
- Nội dung bị lặp do cùng một vùng ảnh được OCR nhiều lần.

Không tự thay thế từ chỉ vì một cách viết khác phổ biến hơn. Đối với các trường hợp Tesseract và VietOCR bất đồng, phải đánh giá bằng chứng nguồn trước khi đề xuất sửa.

**3. Kiểm tra Unicode và lỗi bảng mã**

Phát hiện các ký tự Unicode bất thường, dấu tổ hợp bị tách, ký tự điều khiển, lỗi font và encoding.

Đặc biệt chú ý các lỗi xuất hiện trong PDF Text lịch sử, chẳng hạn:

- đƣợc → được
- ngƣời → người
- chƣa → chưa
- thƣ → thư

Chỉ áp dụng khi xác định được đây là lỗi bảng mã hoặc lỗi trích xuất, không phải ký tự thực sự thuộc nguồn.

Đề xuất chuẩn hóa Unicode NFC khi phù hợp. Không thực hiện phép chuẩn hóa làm mất dấu hoặc làm mất thông tin.

**4. Kiểm tra nội dung cần loại bỏ**

Phát hiện các nội dung không thuộc bản văn chính:

- Đầu trang và chân trang.
- Tên sách hoặc tên chương bị lặp.
- Số trang.
- Ký hiệu thư viện.
- Chú thích chân trang.
- Chỉ mục chú thích như [1], (1) hoặc số superscript.
- Ký tự rác do OCR.
- Dòng bị lặp do nhận dạng cùng một vùng.

Không xóa tất cả nội dung trong dấu ngoặc bằng một quy tắc chung.

Phải phân biệt chỉ mục chú thích với niên đại, số lượng, đơn vị đo, số thứ tự và các nội dung có ý nghĩa.

Ví dụ, [1758] có thể là niên đại cần giữ lại, trong khi [53b] có thể là mã tờ của bản Hán cần chuyển sang metadata truy vết.

Không loại bỏ nội dung diễn giải của dịch giả nếu nội dung đó thuộc phần bản dịch chính.

**5. Kiểm tra thông tin lịch sử**

Giữ nguyên tên người, địa danh, chức danh, niên hiệu, can chi, ngày tháng, số lượng và đơn vị đo cổ theo văn bản nguồn.

Không:

- Đổi tên người sang cách viết phổ biến hơn.
- Thay địa danh lịch sử bằng tên hiện đại.
- Thay chức danh cổ bằng chức danh hiện đại.
- Quy đổi đơn vị đo.
- Thay đổi niên đại dựa trên kiến thức lịch sử của bạn.
- Xóa con số vì cho rằng nó không quan trọng.

Nếu phát hiện thông tin có vẻ bất thường, chỉ tạo cảnh báo để tôi đối chiếu nguồn.

**6. Áp dụng quy tắc riêng theo phiên bản văn bản**

### Đối với dịch âm

Dịch âm là phiên âm Hán–Việt, không phải bản dịch nghĩa hoặc văn bản tiếng Việt hiện đại.

- Giữ nguyên âm tiết và thứ tự phiên âm.
- Giữ các từ Hán–Việt cổ, thuật ngữ ít phổ biến và tên riêng.
- Không sửa câu để tự nhiên hoặc dễ hiểu hơn.
- Không thay một từ Hán–Việt bằng từ thuần Việt.
- Không bổ sung chủ ngữ, đại từ, liên từ hoặc từ nối.
- Không bỏ âm tiết chỉ vì không hiểu nghĩa.
- Không dịch lại từ nguyên văn Hán.
- Không xem một âm tiết không có trong từ điển là lỗi mặc định.

Ví dụ, không được thay “Dư thường văn chi” bằng “Ta thường nghe rằng”, vì như vậy đã chuyển dịch âm thành dịch nghĩa.

### Đối với dịch nghĩa

- Bảo toàn cách diễn đạt của dịch giả.
- Giữ nguyên từ ngữ lịch sử và văn phong của bản dịch.
- Không viết lại cho trôi chảy hơn.
- Không paraphrase, tóm tắt hoặc rút gọn.
- Không thêm lời giải thích.
- Không dịch lại từ bản Hán.
- Không sửa bản dịch để ép khớp với văn bản Hán.

Nếu phát hiện bản dịch có vẻ khác nghĩa với bản Hán, hãy ghi chú cho giai đoạn kiểm tra dóng hàng, không tự sửa ở bước Text Cleaning.

### Đối với dịch thơ

- Giữ nguyên câu thơ, dòng thơ, khổ thơ và thứ tự xuất hiện.
- Giữ từ ngữ, hình ảnh nghệ thuật và cách diễn đạt của dịch giả.
- Không thay từ bằng từ đồng nghĩa.
- Không sửa thơ cho đúng vần, niêm luật hoặc số chữ.
- Không tự ghép các dòng thơ thành đoạn văn.
- Không bổ sung hoặc sáng tác câu thơ bị thiếu.

Nếu nghi ngờ một dòng thơ bị OCR thiếu chữ, hãy đánh dấu vị trí cần kiểm tra.

**7. Kiểm tra bố cục và ngắt dòng**

Phát hiện câu bị ngắt do xuống dòng, chuyển trang, lỗi đọc thứ tự hoặc lỗi OCR.

Chỉ đề xuất ghép các dòng khi có bằng chứng chúng thực sự thuộc cùng một câu hoặc đoạn.

Không gộp các đoạn văn độc lập, không loại bỏ các câu lặp có chủ đích trong văn hịch, văn sách hoặc thơ.

Không tự thực hiện sentence segmentation trong bước Text Cleaning.

**8. Kiểm tra kết quả rule-based cleaning**

So sánh văn bản nguồn với văn bản đã được thuật toán làm sạch để phát hiện:

- Nội dung bị xóa nhầm.
- Niên đại bị loại bỏ.
- Tên riêng bị thay đổi.
- Số lượng hoặc đơn vị đo bị mất.
- Dấu tiếng Việt bị mất.
- Nội dung trong ngoặc bị xóa sai.
- Câu hoặc dòng bị ghép nhầm.
- Chú thích ngoài nội dung chưa được loại bỏ.
- Ký tự lỗi bảng mã còn sót.
- Mã đoạn cần thiết cho việc truy vết hoặc dóng hàng bị mất.

Khi phát hiện lỗi, đề xuất sửa dữ liệu cụ thể, không tự sửa thuật toán rule-based cleaning hiện tại.

**9. Phân loại lỗi**

Sử dụng các loại lỗi phù hợp:

- OCR_CHARACTER_ERROR
- DIACRITIC_ERROR
- LEGACY_FONT_ENCODING
- INVALID_UNICODE
- MISSING_CHARACTER
- EXTRA_CHARACTER
- MISSING_WORD
- EXTRA_WORD
- WORD_BOUNDARY_ERROR
- WHITESPACE_ERROR
- PUNCTUATION_ERROR
- BROKEN_LINE
- DUPLICATE_REGION
- HEADER_FOOTER
- FOOTNOTE
- REFERENCE_MARKER
- HISTORICAL_FOLIO
- HISTORICAL_ENTITY_ERROR
- NUMBER_ERROR
- CONTENT_LOSS
- PHONETIC_TRANSCRIPTION_ERROR
- POETRY_LINE_ERROR
- NEEDS_MANUAL_REVIEW

**10. Yêu cầu đầu ra**

Trước tiên, trình bày bảng lỗi và đề xuất hiệu chỉnh:

| ID hoặc dòng | Văn bản hiện tại | Đề xuất sửa | Loại lỗi | Bằng chứng và lý do | Cần đối chiếu nguồn |
|---|---|---|---|---|---|

Giữ nguyên ID và số dòng được cung cấp.

Phân biệt rõ:

- Lỗi có đủ bằng chứng.
- Lỗi nghi vấn cần đối chiếu.
- Nội dung không cần chỉnh sửa.

Sau đó, nếu được yêu cầu, cung cấp bản văn bản Việt sạch đề xuất dưới dạng plain text.

Bản văn bản sạch phải:

- Giữ nguyên thứ tự nội dung.
- Không chứa nhận xét hoặc giải thích do bạn tạo ra.
- Không tự sửa các vị trí chưa đủ bằng chứng.
- Không chuyển đổi giữa dịch âm, dịch nghĩa và dịch thơ.
- Không bổ sung bản dịch mới.

Cuối cùng, thống kê số dòng được kiểm tra, số lỗi phát hiện, số đề xuất hiệu chỉnh, số lỗi Unicode hoặc bảng mã, số lỗi OCR và số vị trí cần tôi kiểm tra thủ công. Chỉ sử dụng số liệu thực tế từ dữ liệu được cung cấp.

Nếu bạn đang hoạt động như một Coding Agent trong repository, hãy kiểm tra README và schema của bảng review hiện tại trước khi đề xuất cập nhật. Không tự thay đổi source code, thuật toán cleaning, văn bản nguồn hoặc các quyết định đã được duyệt.

Nguyên tắc quan trọng nhất: mục tiêu là hiệu đính và làm sạch bản văn hiện có, không phải tạo ra một bản dịch hay hơn. Khi không đủ bằng chứng, hãy giữ nguyên nội dung và đánh dấu để tôi kiểm tra thủ công.

---

**Dữ liệu đầu vào:**

- Tên tác phẩm:
- Mã tác phẩm:
- Khoảng trang hoặc phạm vi:
- Phiên bản: dịch âm / dịch nghĩa / dịch thơ
- Thể loại:
- Nguồn: PDF Scan / PDF Text / TXT
- Văn bản OCR hoặc văn bản nguồn:
- Văn bản sau rule-based cleaning:
- Kết quả Tesseract và VietOCR (nếu có):
- Danh sách cảnh báo từ notebook (nếu có):
- Ảnh nguồn hoặc tài liệu đối chiếu (nếu có):
```
