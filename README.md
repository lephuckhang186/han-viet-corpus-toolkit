# Chuẩn bị và dóng hàng ngữ liệu Hán–Việt cho TV02

Repo đi từ cắt nguồn, OCR và làm sạch TXT đến dóng hàng theo từng tác phẩm hoặc mục.
Kết quả xuất giữ bốn cột **Hán – Dịch âm – Dịch nghĩa – Dịch thơ** theo yêu cầu
trong [CONTEXT.md](CONTEXT.md). Mỗi bản văn giữ nguyên nội dung theo nguồn đã đối chiếu.

- Có bảng Excel/TSV rồi → xem [Xuất tệp nộp](#xuất-tệp-nộp) để biết tệp nào cần dùng.
- Có TXT sạch → bắt đầu ở [Bước 6. Tách đơn vị và tạo bản nháp](#bước-6-tách-đơn-vị-và-tạo-bản-nháp).
- Có `poetry_prompt.json` hoặc CLC báo lệch → dùng [Prompt 1](#prompt-1-ghép-thơ-và-rà-lỗi-clc).
- Cần tra ảnh gốc, sửa TXT rồi chạy lại → dùng [Prompt 2](#prompt-2-truy-vết-sửa-txt-sạch-và-dóng-lại).
- Mới có PDF → bắt đầu ở [Bước 3. Cắt nguồn](#bước-3-cắt-nguồn).

## Sử dụng notebook từ TXT đến tệp nộp

| Bước | Notebook hoặc công cụ | Kết quả |
|---|---|---|
| 1. Xác nhận đề tài và phạm vi | `guideline/phancong.md` và `ten_file.py` | Mã đề tài, mã sách, quyển/bài và khoảng trang TV02 |
| 2. Kiểm kê nguồn | Bảng kiểm kê của nhóm và thư mục `data/` | Danh sách tài liệu, bản văn, dạng nguồn và phạm vi |
| 3. Cắt nguồn | Các script `cat_*.py` chạy trên máy local | Ảnh vùng cắt hoặc TXT thô trong `01_nguon/` |
| 4. OCR PDF scan | [ocr_nlp.ipynb](notebooks/ocr_nlp.ipynb) trên Kaggle/Colab | TXT, JSON và metadata OCR theo từng ảnh trong `02_ocr_tho/` |
| 5. Làm sạch | [clean_text.ipynb](notebooks/clean_text.ipynb) trên máy local | TXT theo bài và bản văn trong `03_text_sach/`, kèm manifest truy vết |
| 6. Tách đơn vị | [dong_hang.ipynb](notebooks/dong_hang.ipynb), chế độ `nhap` | Đơn vị Hán, âm, nghĩa và thơ trong `draft.json` |
| 7. Dóng hàng và duyệt | Cùng lượt `nhap` trong [dong_hang.ipynb](notebooks/dong_hang.ipynb), sau đó dùng hai prompt Codex khi cần | Nháp dóng, đề xuất và bản duyệt trong `05_quan_ly/dong_hang/TV02/` |
| Xuất | `CHE_DO = "xuat"` trong notebook dóng hàng | TSV, XLSX và `notes.xlsx` trong `04_dong_hang/` |

Ví dụ bên dưới dùng Văn sách Thi Đình (`CPO_11`, bài 14–18) và Thơ văn Lý–Trần
(`CPO_12`, bài 131–207). Prompt 1 quét theo đường dẫn được giao. Prompt 2 giới hạn ở hai sách này.
Bắc sứ (`CPO_09`) có cell riêng. Mỗi mục Bắc sứ cần khoảng dòng
Hán và Việt đã đối chiếu nội dung trong `KHOANG_DONG_THEO_MUC`. Khoảng dòng tính từ 1,
bỏ dòng trống, tính cả hai đầu.

### Chuẩn bị môi trường local

1. Mở thư mục repo trong VS Code. Với hai notebook chạy local, chọn kernel từ
   `.venv/Scripts/python.exe`. Phần [Chạy ngay](#chạy-ngay) có lệnh tạo `.venv` nếu máy chưa có.
2. Kiểm tra các gói cho notebook và luồng dóng hàng. Nếu còn thiếu, cài vào cùng `.venv`.

   ```powershell
   .\.venv\Scripts\python.exe -c "import ipykernel, pandas, requests, yaml, xlsxwriter; print('OK')"
   .\.venv\Scripts\python.exe -m pip install ipykernel pandas requests PyYAML XlsxWriter
   ```

### Bước 1. Xác nhận đề tài và phạm vi

Đọc bảng phân công local tại `guideline/phancong.md` để xác định sách, bài và các mốc trang.
Đối chiếu `MA_DE_TAI`, mã sách và đường dẫn nguồn trong [ten_file.py](ten_file.py).
Bước này dùng bảng phân công và file cấu hình.

### Bước 2. Kiểm kê nguồn

Lập bảng ghi tên tài liệu, bản Hán hoặc bản Việt, dạng PDF scan hay PDF Text và phạm vi
được giao. Đặt file gốc theo [hướng dẫn thư mục dữ liệu](data/README.md). Dùng bước kiểm kê
để chọn xử lý OCR cho bản scan hoặc trích chữ cho bản có lớp text.

### Bước 3. Cắt nguồn

Chạy script `cat_*.py` của sách tương ứng. Đặt PDF vào `data/`, mở công cụ theo
phần [Chạy ngay](#chạy-ngay) rồi [cắt bằng chuột](#cắt-bằng-chuột). Lưu từng vùng bằng
mã bài, bản văn và phiên bản. Kiểm tra thứ tự các phần trong `01_nguon/` trước khi chuyển qua OCR.

### Bước 4. OCR hoặc trích TXT thô

Dùng [ocr_nlp.ipynb](notebooks/ocr_nlp.ipynb) trên Kaggle hoặc Colab.

1. Chọn nguồn và bản văn trong `SELECTED_JOBS`. Chạy thử một ảnh ở mục 10 để xem vùng
   nhận dạng và thứ tự các dòng. Xem [hướng dẫn OCR](notebooks/README.md) cho từng loại ảnh.
2. Chạy mục 11 cho phạm vi đã chọn. Đưa TXT từng ảnh và metadata về đúng cây `02_ocr_tho/`
   trên máy local. Giữ tên thư mục bài, bản văn và tên `phanNNNN_pdfpNNNN` để truy ảnh.
3. Với Việt Bắc sứ, dùng hai TXT lớp chữ đã lưu trong `01_nguon/` làm đầu vào làm sạch.

### Bước 5. Làm sạch TXT

Dùng [clean_text.ipynb](notebooks/clean_text.ipynb) trên máy local.

1. Kiểm tra `PROJECT_ROOT`, `SELECTED_CODES` và `SELECTED_KINDS`.
   `INPUT_GRANULARITY = "parts"` đọc TXT từng ảnh. Đặt `WRITE_OUTPUTS = False` ở lượt xem trước.
2. Duyệt `duyet_lam_sach.csv` và đối chiếu ảnh cho các dòng bị đánh dấu.
3. Đặt `WRITE_OUTPUTS = True` và chạy lại đến mục 5.2 để ghi TXT vào `03_text_sach/`.
   Notebook báo xung đột nếu tệp đích có nội dung khác. Nếu đã có TXT đúng bài và phiên bản,
   dùng bộ đó làm đầu vào bước 6.

Thư mục `san_pham/TV02/05_quan_ly/<RUN_NAME>/` chứa `duyet_lam_sach.csv`,
`work_manifest.json`, `changes.jsonl` và `summary.json`. Với thiết lập `parts`, tên lượt
mặc định là `clean_v02_parts`. Nếu TXT đã được rà soát lần sau, dùng manifest của lần rà
soát tương ứng với SHA-256 hiện tại để lần về dòng OCR và ảnh.

### Bước 6. Tách đơn vị và tạo bản nháp

Dùng [dong_hang.ipynb](notebooks/dong_hang.ipynb) trên máy local.
Chọn cell của sách cần chạy. Ví dụ tạo nháp cho bài 131 trong cell **Thơ văn Lý–Trần**:

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

`nhap` dùng `clc_response.json` khi `request_sha256` khớp nội dung yêu cầu hiện tại.
Khi thiếu cache hoặc hash lệch, chế độ `nhap` thông thường sẽ thử gọi CLC nếu kernel
có `CLC_API_KEY`. Nếu chủ động cần tạo phản hồi mới, dùng cell **Nạp token CLC** với ô
nhập ẩn. Hai prompt bên dưới làm việc với phản hồi đã lưu. Khi cần chạy lại ngoại tuyến,
dùng Prompt 2 để chặn nhánh gửi request mới trong lượt chạy.

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

Dùng [dong_hang.ipynb](notebooks/dong_hang.ipynb) và [hai prompt Codex](#hai-prompt-codex).
Lượt `nhap` ở bước 6 cũng tạo liên kết Hán–âm và lấy nhóm Hán–nghĩa từ CLC khi có phản hồi
phù hợp. Dùng kết quả đó để tiếp tục ghép thơ và rà từng bài.

1. Chạy [Prompt 1](#prompt-1-ghép-thơ-và-rà-lỗi-clc) để ghép thơ và rà mismatch CLC.
2. Dùng `review.json` để chốt `links.am`, `links.nghia` và `links.tho`. Với bài mới chỉ
   có đề xuất thơ, tạo bản duyệt từ `review_template.json`, đưa các nhóm thơ khớp fingerprint
   vào `links.tho` và tính lại `skipped` theo toàn bộ ba danh sách.
3. Trong mỗi cột, các ID trong một nhóm phải liền nhau. Các nhóm đi theo thứ tự nguồn và
   mỗi ID chỉ được dùng một lần trong cột đó. Một ID Hán có thể đi với cả âm, nghĩa và thơ.
   Ghi lý do vào `skipped` cho từng ID chưa dùng. Hán còn ghép ở ít nhất một trong ba cột
   thì không thêm vào `skipped`.
4. Với `needs_review`, tra ID trong `draft.json` để đọc đúng câu. Đọc thêm hai dòng kế cận,
   rồi dùng ảnh nguồn nếu cần xác nhận ký tự. [Prompt 2](#prompt-2-truy-vết-sửa-txt-sạch-và-dóng-lại)
   thực hiện truy vết, sửa lỗi có bằng chứng và dóng lại sau khi TXT thay đổi.

Để xem nhanh một **bản duyệt có sẵn** theo bốn cột, chạy cell sau trong notebook local.
Ví dụ dùng dữ liệu của `bai0140` trên máy hiện tại:

```python
from pathlib import Path
import sys

import pandas as pd
from IPython.display import display

root = Path(r"D:\code\CS\NLP")
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

`work` nhận diện sách, bài, thành viên và mục nếu có. `fingerprint` nhận diện phiên bản nguồn và
cách tách đơn vị. Trong `units`, `start` và `end` là chỉ số ký tự trong TXT đã giải mã UTF-8.
`text[start:end]` lấy từ `start` đến ngay trước `end`. `part` chỉ phần ngăn bởi `\f` trong TXT.
Dùng manifest để xác định trang PDF thực tế. Sau khi sửa TXT, dùng Prompt 2 để dựng lại đơn vị
và ánh xạ ID.

### Xuất tệp nộp

Dùng [dong_hang.ipynb](notebooks/dong_hang.ipynb) với chế độ `xuat`.

1. Chốt các cặp trong `review.json`, kiểm tra lý do `skipped` rồi lưu `"approved": true`.
2. Trong cell đúng sách của `dong_hang.ipynb`, chọn bài đã duyệt. Ví dụ:

   ```python
   CHAY_HANG_LOAT = False
   SO_BAI = 140
   CHE_DO = "xuat"
   ```

   Để xuất nhiều bài, đặt `CHAY_HANG_LOAT = True` và điền `DANH_SACH_BAI` bằng số các bài
   đã duyệt. `xuat` dùng cấu hình từ `draft.json` và kiểm tra fingerprint với TXT hiện tại.
3. Lấy `*_parallel.xlsx` và `*_parallel.tsv` trong thư mục từng bài. Ví dụ:

   ```text
   san_pham/TV02/CV06_CPO_12/04_dong_hang/bai0140/
   ├── CPO_12_bai0140_parallel.xlsx
   ├── CPO_12_bai0140_parallel.tsv
   └── notes.xlsx
   ```

4. Mở sheet `DONG_HANG` để kiểm tra bốn cột **Hán – Dịch âm – Dịch nghĩa – Dịch thơ**.
   TSV lưu cùng dữ liệu UTF-8, với mỗi hàng gồm bốn ô ngăn bằng tab và không có hàng tiêu đề.
   `notes.xlsx` ghi các đơn vị bỏ lại, ghi chú links và chẩn đoán Lab. Ô trống có thể là
   bản văn thiếu trong nguồn hoặc chưa có liên kết. Kiểm tra `notes.xlsx` và `draft.json`
   để xác định lý do trước khi tính số cặp hợp lệ.

Bộ xuất TV02 ngày 21/11/2026 đã ghi **5 bài Thi Đình và 77 bài Lý–Trần**, tổng **1.273 hàng**.
Phiên đó kiểm tra Excel khớp TSV. **32 bài có TXT nghĩa nhưng chưa có nhóm nghĩa trong bảng**.
Nếu đang dùng bộ xuất này, mở `04_dong_hang/` của từng sách. Báo cáo phiên rà soát nằm tại
`san_pham/TV02/05_quan_ly/ra_soat_dong_hang_2026-11-21/BAO_CAO.md`.

### Lỗi thường gặp khi dóng hoặc xuất

| Hiện tượng | Cách xử lý |
|---|---|
| `approved=false` | Mở `review.json` của đúng bài và chốt cặp trước khi cho phép xuất. |
| Lệch `work` hoặc `fingerprint` | Mở đúng thư mục bài. Nếu nguồn hoặc cách tách đã thay đổi, chạy quy trình ánh xạ lại ở Prompt 2. |
| CLC có cache nhưng cột nghĩa chưa lên | Đọc `status.CLC` trong `draft.json`. Với lỗi lệch văn bản còn hiệu lực, dùng Prompt 1. Với request đổi, dùng quy trình offline ở Prompt 2 và ghi phần nghĩa còn thiếu. |
| Thơ đã có JSON nhưng bảng xuất còn trống | Xem `links.tho` của `review.json`. Đưa nhóm thơ khớp fingerprint vào bản duyệt và tính lại `skipped`. |
| Tệp đích đã có nội dung khác | Bảo toàn bản xuất cũ và lưu riêng sau khi bạn quyết định dùng bản mới. Pipeline chặn ghi đè xung đột. |
| Ông/bà, tên riêng hoặc chữ Hán khác giữa hai bản | Đối chiếu ảnh của từng bản rồi đánh giá theo nghĩa. Chỉ hiệu đính TXT khi có lỗi được nguồn xác nhận. |

## Hai prompt Codex

### Prompt 1. Ghép thơ và rà lỗi CLC

Sao chép nguyên khối dưới đây sau khi tạo nháp cho các bài cần xử lý.

```text
Trong repo D:\code\CS\NLP, rà các thư mục bài/mục tại
san_pham/TV02/CV06_CPO_*/05_quan_ly/dong_hang/TV02/*.
Đọc file trực tiếp từ repo và xử lý riêng từng bài theo work và fingerprint.

1. Hán – dịch thơ
- Với bài có poetry_prompt.json và chưa có poetry_result.json, ghép Hán với bản dịch thơ có sẵn theo nghĩa.
- Có thể ghép nhiều câu liền nhau khi cùng diễn đạt một ý. Giữ thứ tự, mỗi ID dùng tối đa một lần trong cột thơ.
- Lưu poetry_result.json cạnh prompt, gồm work, fingerprint và links. Mỗi link có han_ids, tho_ids và note.
- Ghi needs_review theo ID Hán đầu nhóm và lý do nếu cặp đề xuất còn điểm cần kiểm tra. Với những câu chưa đủ căn cứ để ghép, ghi ID và lý do trong skipped.

2. Hán – dịch nghĩa và lỗi CLC
- Với bài có clc_mismatch.json khớp work, fingerprint và draft.json còn báo lỗi CLC, đọc clc_request.json, toàn bộ clc_response.json và units trong draft.json.
- Dùng mismatch để định vị chỗ nghi vấn, rồi rà các nhóm còn lại trong bài.
- Nếu lệch chỉ số, tìm đoạn nguồn khớp duy nhất theo nội dung và thứ tự.
- Nếu CLC tách một câu, chỉ gộp nhóm liền nhau khi phủ trọn đơn vị nguồn.
- Nếu CLC thiếu hoặc đổi chữ, đối chiếu hai bản nguồn và ngữ cảnh. Chỉ đề xuất khi đủ căn cứ và lấy nguyên văn nguồn theo ID. Ghi rõ ID và lý do cho các cặp còn mơ hồ.

3. Lưu bản chờ duyệt
- Với bài đã rà mismatch và chưa có review.json, tạo từ review_template.json. Giữ links.am theo bản nháp. Điền links.nghia bằng các đề xuất đã rà và lấy links.tho từ poetry_result.json khi khớp fingerprint.
- Kiểm tra ID tồn tại, liền nhau, đúng thứ tự và không trùng trong từng cột. Tính lại skipped, ghi lý do cho từng ID chưa ghép và đặt approved=false.
- Nếu đã có review.json, giữ nguyên tệp và báo các đề xuất để tôi duyệt.

Chỉ ghi poetry_result.json mới và review.json mới. Dùng phản hồi CLC đã lưu, giữ nguyên TXT, log và các bản duyệt hiện có. Báo theo mã bài số nhóm thơ, số nhóm nghĩa đề xuất và ID cần tôi xem.
```

### Prompt 2. Truy vết, sửa TXT sạch và dóng lại

Sao chép nguyên khối này khi bạn cho phép Codex sửa TXT sạch và chạy lại lô bài.

```text
Trong repo D:\code\CS\NLP, rà và chạy lại các bài TV02 của Văn sách Thi Đình (CPO_11) và Thơ văn Lý–Trần (CPO_12). Tìm các bài trong san_pham/TV02/CV06_CPO_*/05_quan_ly/dong_hang/TV02/*, giới hạn đúng hai mã sách trên.

1. Rà các ID cần kiểm tra
- Đọc needs_review, skipped và note trong poetry_result.json, cùng ghi chú liên quan trong review.json. Xử lý riêng từng bài theo work và fingerprint.
- Tra ID trong draft.json → units để lấy bản văn, text, start, end và part. Mở TXT theo draft.sources[kind].file, kiểm tra SHA-256 rồi đọc text[start:end] và các dòng liền kề. Nếu hash lệch, tìm lại vị trí theo nội dung và ngữ cảnh.
- Dùng work_manifest.json và metadata nguồn để truy tới dòng OCR, ảnh cắt hoặc trang PDF gốc. Ghi vị trí đã xác minh. Nếu chưa đủ bằng chứng, giữ TXT như hiện tại và báo mã bài, ID và vị trí cần tôi xem.

2. Sửa TXT sạch
- Tôi cho phép sửa trực tiếp các TXT liên quan trong 03_text_sach của hai sách. Lưu bản trước sửa. Ghi đường dẫn, dòng hoặc trang nguồn, chữ trước/sau và lý do. Cập nhật truy vết cho phiên bản đã sửa.
- Đọc clean_text.ipynb và manifest để hiểu nguồn gốc TXT. Chỉ sửa lỗi OCR, ký tự rác hoặc ngắt dòng khi nguồn xác nhận. Giữ nguyên PDF, ảnh và TXT OCR đầu vào.
- Giữ khác biệt vốn có giữa các bản văn. Ví dụ nếu ảnh Hán ghi 矛 và ảnh bản thơ in «cờ», giữ cả hai và đánh giá liên kết theo ngữ cảnh. Nếu lỗi nằm ở cặp dóng, sửa đề xuất links.

3. Chạy dóng lại toàn bộ
- Dùng cấu hình từng bài trong draft.json và pipeline của notebooks/dong_hang.ipynb. Chạy từng bài trong hai sách, kể cả bài giữ nguyên TXT. Ghi bài nào thành công hoặc lỗi.
- Với bài đổi fingerprint, dựng lại units và tra lại ID theo nội dung, bản văn và thứ tự. Chỉ chuyển cặp cũ khi ánh xạ duy nhất. Rà các cặp chạm vùng sửa và các ánh xạ mơ hồ.
- Giữ bản duyệt cũ để đối chiếu. Lưu bản chờ duyệt mới với approved=false.
- Chạy ngoại tuyến. Dùng phản hồi CLC đã lưu khi request hash còn khớp. Chặn nhánh gửi request CLC mới trong lượt chạy. Nếu cache thiếu hoặc hết hiệu lực, ghi bài cần đối chiếu thủ công hoặc có phản hồi mới sau.
- Kiểm tra work, fingerprint, ID tồn tại, tính liền nhau, thứ tự, trùng lặp trong từng cột và lý do skipped. Đọc lại kết quả sau khi lưu.

Cuối cùng, báo số bài đã chạy và kết quả theo mã bài. Liệt kê TXT đã sửa, vị trí nguồn, số nhóm âm/nghĩa/thơ và ID còn cần tôi xem. Dẫn đường dẫn đến bản chờ duyệt mới.
```

## Chạy ngay

Mở PowerShell tại thư mục repo (máy hiện tại là `D:\code\CS\NLP`), chạy một trong bốn file:

```powershell
.\.venv\Scripts\python.exe .\cat_ly_tran.py
.\.venv\Scripts\python.exe .\cat_van_sach.py
.\.venv\Scripts\python.exe .\cat_bac_su.py
.\.venv\Scripts\python.exe .\cat_hich_tuong_si.py
```

Môi trường `.venv` trên máy hiện tại đã được tạo. Công cụ cắt nguồn dùng hai thư viện trong `requirements.txt`.
Nếu cài trên máy khác, dùng Python 3.11 trở lên có Tkinter:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Repo GitHub chỉ chứa mã nguồn, hướng dẫn và tests. PDF nguồn, `Guideline.pdf`,
sản phẩm cắt, lịch sử thao tác và `.venv` được giữ ở máy, không đưa vào Git.
Sau khi clone, đặt các PDF vào `data/` theo [hướng dẫn dữ liệu](data/README.md)
hoặc sửa `TEN_NGUON` trong `ten_file.py`. Các tests tích hợp cần những PDF này;
thiếu dữ liệu sẽ được ghi nhận là bỏ qua, không được tính là đã kiểm tra thành công.

**`MA_DE_TAI` trong `ten_file.py` phải khớp mã đăng ký của nhóm.** Giữ cấu hình
bạn đã đặt; chỉ đổi khi cần sửa mã đăng ký. Đổi mã sẽ
đổi thư mục đầu ra của các lần chạy sau; tool không tự di chuyển sản phẩm cũ.

## Cắt bằng chuột

1. Mở đúng script của sách. Tool kiểm tra bản sao gốc rồi hiển thị PDF.
2. Nhập **mã tác phẩm**, ví dụ `bai0131`. Đây là mã bài, không phải trang PDF.
3. Chọn **Hán / Dịch âm / Dịch nghĩa / Dịch thơ**.
4. Kéo chuột khoanh đúng vùng của bản văn đó, bấm **Lưu vùng vào tác phẩm** hoặc Ctrl+S.
5. Nếu bản văn còn tiếp ở trang sau, mở trang tiếp theo, **giữ nguyên mã tác phẩm,
   loại bản và phiên bản**, rồi chọn/lưu tiếp. Tool lưu các PNG vào cùng thư mục tác phẩm/bản văn.
6. Làm tương tự cho các bản còn lại. Nút **Xem đủ/thiếu bản văn** giúp kiểm tra phần đã cắt.

Thứ tự bạn bấm lưu là thứ tự các phần trong mỗi bản văn. Không suy ra thứ tự chỉ từ
số trang: đôi khi phải quay lại phần trước. Lưu lại đúng vùng với cùng cấu hình
thì tool bỏ qua bản trùng. Vùng gần trùng sẽ có cảnh báo trước khi lưu thêm.

## Xem, sửa và hoàn tác

- Danh sách bên phải hiển thị các vùng của bài/phiên bản đang chọn. Bấm một dòng để
  xem ảnh hoặc đoạn TXT. Khung xanh trên trang là vùng đã lưu; khung xám là vùng
  của bài khác trên cùng trang.
- **Chỉnh vùng đã chọn**: mở lại đúng trang và khung cũ. Khoanh lại rồi bấm
  **Lưu thay khung vùng đã chọn**. Giữ nguyên mã bài, bản văn, phiên bản và số phần.
  Có thể đổi trang để sửa phần đã lấy nhầm trang. Với vùng TXT, chọn lại đoạn chữ.
- **Bỏ vùng đã chọn**: bỏ vùng khỏi sản phẩm đang dùng; TXT ghép được cập nhật
  theo các phần còn lại. Các phần khác giữ số thứ tự cũ để không mất mã tham chiếu.
- **Hoàn tác thao tác gần nhất**: khôi phục trạng thái trước lần lưu, thay, bỏ vùng
  hoặc xác nhận tiến độ. Có thể hoàn tác nhiều lần, kể cả sau khi mở lại tool.
- Dữ liệu vùng lưu từ bản tool cũ vẫn xem/sửa/bỏ được. Hoàn tác chỉ áp dụng cho
  các thao tác được thực hiện từ bản nâng cấp có lịch sử.
- Chỉnh vùng giữ nguyên loại bản văn. Nếu lưu sai loại Hán/dịch nghĩa, bỏ vùng cũ
  rồi chọn đúng loại và lưu lại; có thể hoàn tác thao tác bỏ nếu cần.

Các bản trước/sau được lưu trong `05_quan_ly/lich_su/`. Không xóa thư mục này nếu
còn cần hoàn tác. Lịch sử sử dụng thêm dung lượng theo số thao tác; metadata được
nén để giảm dung lượng. File đã sửa bên ngoài tool sẽ được giữ và báo xung đột.
Nếu lần ghi bị ngắt, lần mở tiếp theo phục hồi trạng thái trước thao tác chưa hoàn tất.

## Mặc định nguồn, nhớ vị trí và tiến độ

- Nguồn riêng bản Việt của Bắc sứ mặc định **Dịch nghĩa**; nguồn riêng Hán mặc định
  **Hán**. Với PDF chứa nhiều bản văn, bạn vẫn chọn đúng loại vùng cần lấy.
  Nếu chọn loại khác ngôn ngữ của nguồn riêng, tool cảnh báo trước khi lưu.
- Tool nhớ trang gần nhất của từng nguồn, bài, loại bản văn, phiên bản và mức phóng
  trong `05_quan_ly/phien_lam_viec.json`; mở lại để tiếp tục từ phiên đã lưu.
- **Tiến độ bốn bản văn** hiển thị Hán, dịch âm, dịch nghĩa, dịch thơ theo từng bài.
  Chỉ bấm **Đã kiểm tra đủ / bỏ xác nhận** sau khi bạn đã đối chiếu trọn bản văn.
  Thêm, sửa hoặc bỏ vùng sẽ đưa bản văn đó về trạng thái đang làm.
- Trạng thái đủ vùng do bạn xác nhận, không chứng minh câu đã dóng hàng đúng hoặc
  đã đạt chỉ tiêu cặp. Ghi nhận không có bản văn chỉ dùng khi nguồn thực sự không có.

Nguồn và bản sao được kiểm tra hash khi mở/chuẩn bị. Các lần lưu tiếp trong cùng
phiên tái sử dụng kết quả khi đường dẫn, dung lượng và thời gian file không đổi.
Nếu thông tin file thay đổi, tool kiểm tra lại; `--check` luôn đọc và kiểm tra đầy đủ.

Nếu sách thực sự không có một bản dịch, ghi lý do ở ô ghi chú rồi bấm **Ghi nhận
không có bản này**. Không dùng chức năng này để bỏ qua phần chưa đọc. Tool không
tạo bản dịch hoặc file TXT rỗng thay phần thiếu.

**Chú thích:** ở bước 3 ảnh còn giữ nguyên các chỉ dấu trong thân bài. Khoanh phần
nội dung chính, để khối khảo đính/chú thích riêng ngoài vùng. Việc loại chú thích
không thuộc nội dung Hán và làm sạch ký tự là bước 5, không phải sửa ảnh nguồn.

## Phần việc của TV2

| File chạy | Phạm vi mặc định | Điểm cần chú ý |
|---|---|---|
| `cat_ly_tran.py` | Bài 131–207; PDF 187–366 | Trên trang 187, phần trên là cuối bài 130 của TV1; chỉ lấy bài 131 phía dưới. |
| `cat_van_sach.py` | Bài 14–18; PDF 188–365 | Mốc đầu dịch nghĩa/Hán từng bài có trong script; cần tự kiểm tra điểm kết thúc. |
| `cat_bac_su.py` | Theo bảng mới: Việt PDF 32–61; Hán PDF 49–101 | Cắt ảnh vùng lớn; Việt chỉ chỉnh mốc đầu/cuối phần giao. Không tách cột/đoạn, không dóng hàng, không lấy Hán 102. |
| `cat_hich_tuong_si.py` | Hán/dịch âm 11–20; dịch nghĩa 4–6; diễn thơ 21–26 | Đây là mẫu chung TV2 kiểm tra, không cộng bộ cặp thứ hai. |

Số trang luôn là thứ tự trong **PDF gốc**, tính từ 1. Khi cần trang lân cận để giữ
trọn bài, bật **Cho phép ngữ cảnh/mẫu ngoài phạm vi TV2** và ghi lý do.

## Bố cục đã tạo

```text
data/                                      # PDF đầu vào, giữ nguyên
san_pham/TV02/<MA_DE_TAI>_CPO_12/           # Ví dụ Lý–Trần
├── 01_nguon/
│   ├── chung/ban_goc/                      # Bản sao nguyên PDF hỗn hợp
│   ├── han/
│   │   └── CPO_12_TV02_bai0131_han_v01/
│   │       └── phan0001_pdfp0187.png
│   └── viet/
│       ├── dich_am/                        # Gom riêng theo bài, giống phía Hán
│       ├── dich_nghia/
│       └── dich_tho/
├── 02_ocr_tho/
│   ├── han/                               # TXT và metadata OCR bản Hán
│   └── viet/
├── 03_text_sach/                           # TXT sạch theo bài và bản văn
├── 04_dong_hang/                           # TSV/XLSX theo bài sau khi xuất
└── 05_quan_ly/
    ├── nguon.json                         # Nguồn, bản sao, SHA-256, phạm vi
    ├── vung_cat.json                       # Tác phẩm, bản văn, trang/vùng/thứ tự
    ├── phien_lam_viec.json                 # Trang và các lựa chọn gần nhất
    ├── lich_su/                           # Bản trước/sau để phục hồi, hoàn tác
    ├── text_tho/                          # Đoạn text trích xuất, nếu chọn
    └── dong_hang/TV02/bai0131/             # Nháp, phản hồi CLC và bản duyệt
```

Các thư mục CPO_09 / CPO_10 / CPO_11 có bố cục tương tự. Với Bắc sứ, bản gốc Hán
được sao lưu trong `han/ban_goc/`, bản Việt trong `viet/ban_goc/`.
Ba thư mục con dưới `viet/` và `05_quan_ly/` bổ sung việc quản lý bốn bản văn và
truy vết, giữ nguyên bốn tầng chính cô khuyến nghị.

**Một thư mục ảnh = một tác phẩm + một bản văn + một phiên bản.** Các PNG bên trong
được đánh số theo thứ tự lưu; không được tính mỗi ảnh là một tác phẩm/cặp dóng hàng.

Ví dụ thư mục `CPO_12_TV02_bai0131_han_v01/`: CPO_12 là mã sách, TV02 là thành viên 2,
bai0131 là bài 131, han là bản Hán, v01 là phiên bản đầu. `phan0001_pdfp0187.png`
là phần thứ nhất của bản văn, lấy từ trang gốc 187. Dùng số cố định chiều dài,
không dùng tên final/final2/final_new.

Tool chỉ xuất PNG vùng đã chọn, không tạo PDF sau khi cắt. PDF gốc và bản sao
nguyên vẹn vẫn được giữ để đối chiếu. Muốn lấy chữ từ PDF Text, dùng tùy chọn bên dưới.

## Cắt TXT và PDF Text

- **TXT UTF-8 có sẵn:** bấm **Mở TXT để chọn chữ**, bôi đen đúng phần cần lấy rồi lưu.
  Mã tác phẩm, loại bản và phiên bản lấy từ cửa sổ chính. File nguồn được sao lưu.
- **PDF có lớp chữ:** khoanh vùng như bình thường, bật **Lấy thêm lớp chữ PDF**.
  Tool xuất PNG và TXT thô của vùng. Đây là tùy chọn trích xuất ở bước 4;
  không tự OCR hoặc coi text là đã sạch. PDF Text xoay chưa hỗ trợ trích chữ vùng.
- **PDF scan:** chỉ xuất PNG. Nếu bật lấy chữ nhưng vùng không có text,
  tool báo lỗi và không tạo TXT rỗng. Nếu chữ nguồn bị lỗi font thì TXT vẫn cần sửa.
- **Một phiên bản của một bản văn dùng một chế độ:** ảnh PDF, PDF có trích text,
  hoặc TXT. Muốn đổi chế độ, dùng phiên bản mới để tránh ghép TXT thiếu một nửa.

Lệnh cắt TXT theo dòng (thay đường dẫn bằng TXT thật):

```powershell
.\.venv\Scripts\python.exe .\cat_ly_tran.py --text-file "duong_dan_text.txt" --lines 10 20 --work bai0131 --kind dich_nghia
```

TXT ghép có đuôi `_trich_xuat_tho.txt`, chưa phải `han.txt/viet.txt` sạch. Công cụ
chỉ giữ đoạn được chọn, không dịch, không cắt câu hoặc suy đoán Hán/Việt theo ký tự.

## Kiểm tra / chuẩn bị lại

Các cờ dùng được cho cả bốn script:

```powershell
.\.venv\Scripts\python.exe .\cat_ly_tran.py --prepare
.\.venv\Scripts\python.exe .\cat_ly_tran.py --info
.\.venv\Scripts\python.exe .\cat_ly_tran.py --check
.\.venv\Scripts\python.exe .\cat_ly_tran.py --summary --work bai0131
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

`--check` so SHA-256 nguồn, bản sao và sản phẩm, phát hiện file thiếu/bị sửa. Nó
không kiểm tra nghĩa, thiếu câu hay đủ ranh giới tác phẩm. Hai cửa sổ có thể đọc
cùng sách nhưng không được ghi cùng lúc: khóa ghi giúp tránh mất manifest.

## Mã nguồn nằm ở đâu?

| File | Chức năng |
|---|---|
| `ten_file.py` | Tên nguồn, mã đề tài/sách/thành viên, thư mục và quy ước tên. |
| `cat_ly_tran.py`, `cat_van_sach.py`, `cat_bac_su.py`, `cat_hich_tuong_si.py` | Cấu hình/phạm vi và điểm chạy riêng từng sách. |
| `cong_cu/models.py` | Kiểu dữ liệu, kiểm tra mã bài và vùng cắt. |
| `cong_cu/pdf_ops.py` | Đọc PDF nguồn, render/cắt PNG và lấy lớp chữ theo vùng. |
| `cong_cu/text_ops.py` | Đọc/cắt TXT Unicode theo dòng/ký tự. |
| `cong_cu/storage.py` | Dấu kiểm, sao lưu, ghi file và khóa ghi. |
| `cong_cu/workspace.py` | Bố cục đầu ra, gom vùng theo tác phẩm, manifest, đủ/thiếu bản văn. |
| `cong_cu/region_actions.py` | Liệt kê, thay/bỏ vùng, kiểm tra chồng vùng và xác nhận tiến độ. |
| `cong_cu/history.py` | Lưu thay đổi, hoàn tác và phục hồi lần ghi bị ngắt. |
| `cong_cu/region_panel.py` | Danh sách xem trước và bảng tiến độ bốn bản văn. |
| `cong_cu/cli.py` | Tham số và chạy kế hoạch CSV. |
| `cong_cu/ui.py`, `cong_cu/text_ui.py` | Giao diện PDF và TXT. |
| `cong_cu/dong_hang.py`, `cong_cu/alignment_notebook.py` | Tách đơn vị, kiểm tra links và chạy dóng/xuất theo bài. |
| `cong_cu/alignment_backends.py` | Chạy code Lab, đọc cache CLC và gửi request khi được cấu hình. |

Không gộp toàn bộ xử lý vào file cấu hình hoặc một script lớn. Đã tham khảo cách
giữ nguồn, xuất ảnh và lưu manifest của [pdfslice-py](https://github.com/obj-see/pdfslice-py).
Không sao chép mã nguồn hay cài repo đó; phần cắt tác phẩm/bốn bản văn được viết riêng.

## Phạm vi bàn giao Bắc sứ

Luồng xuất hai sách ở trên áp dụng cho `CPO_11` và `CPO_12`. Bản Việt Bắc sứ bên dưới
là bộ TXT nguồn thô đã bàn giao. Để dóng một mục Bắc sứ, cần kiểm tra ranh giới nội dung
và khoảng dòng tương ứng của hai bản trong cell riêng của notebook dóng hàng.

## Bắc sứ TV2: bản Việt TXT nguồn thô

Bản bàn giao Việt ở `san_pham/TV02/CV06_CPO_09/01_nguon/viet/dich_nghia/`:

- `CPO_09_TV02_quyen01_phan_tv02_dich_nghia_v01.txt`: PDF 32–54; bắt đầu sau mục 21.
- `CPO_09_TV02_quyen04_phan_tv02_dich_nghia_v01.txt`: PDF 55–61; dừng đúng câu chốt trong `phancong.md`.

Đây là nguồn PDF Text: đọc lớp chữ sẵn có, không OCR. Giữ nguyên chú thích, chỉ mục, số trang trong phạm vi, ký tự nguồn, khoảng trắng và xuống dòng; không sửa font hoặc ghép đoạn. Ký tự form feed `U+000C` ngăn các trang; chỉ mục đối chiếu ở `05_quan_ly/nguon_tho_viet.json`. PDF gốc và bản sao vẫn nguyên vẹn.

Theo guideline, trích xuất text thuộc bước 4. TXT này chỉ là bản làm việc thô cho bàn giao nguồn; chưa chứng nhận hoàn thành bước 4/5. Bản đã chuẩn hóa ở `03_text_sach/viet.txt` và các TXT đã bỏ chú thích ở `02_ocr_tho/viet/` được rút khỏi sản phẩm hiện tại, giữ bản trước trong lịch sử hoàn tác. 30 PNG Việt cũ chỉ để tra lại, không phải bản Việt nộp.

Kế hoạch `bac_su_tv02.csv/jsonl` của lượt bàn giao cắt 43 ảnh Hán. Quyển 1 Hán giữ 34 PNG,
quyển 4 giữ 9 PNG. Dùng hai TXT đã có ở đường dẫn trên khi cần đọc lại bản Việt thô.
