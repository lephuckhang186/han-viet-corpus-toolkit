# han-viet-corpus-toolkit

Bộ công cụ chuẩn bị và xử lý ngữ liệu Hán–Việt: lưu nguồn theo tác phẩm và phiên bản, OCR, làm sạch có duyệt, tách đơn vị và dóng hàng. Bảng song ngữ có bốn cột **Hán – Dịch âm – Dịch nghĩa – Dịch thơ**; phiên bản không có trong nguồn được để trống.

Phạm vi hiện hành của TV2 là chuẩn bị nguồn ở bước 3. Đọc [CONTEXT.md](CONTEXT.md) và [phancong.md](phancong.md) trước khi làm việc với nguồn. Các chức năng OCR, làm sạch và dóng hàng phục vụ các bước sau; chạy công cụ không đồng nghĩa với việc nội dung hoặc chỉ tiêu đã được xác nhận.

## Thư mục chính

| Thư mục | Nội dung |
|---|---|
| [notebooks](notebooks/README.md) | Notebook thao tác và hướng dẫn theo từng bước. |
| [src/hanviet](src/hanviet) | Các mô-đun chuẩn bị nguồn, trích xuất, làm sạch, segmentation, dóng hàng, xuất và đánh giá. |
| [cong_cu](cong_cu) | Các lớp tương thích và công cụ notebook hiện có. |
| [scripts](scripts) | CLI tạo bảng duyệt làm sạch, đối chiếu OCR, hậu kiểm dóng hàng và đánh giá. |
| [configs](configs) | Cấu hình dự án, thành viên, bộ sách và phương pháp. |
| [prompts](prompts) | Prompt tham khảo cho làm sạch và dóng hàng. |
| [docs](docs) | Kiến trúc, phương pháp và tài liệu kiểm thử. |
| `data/` | Dữ liệu cục bộ, không được đưa lên Git theo `.gitignore`. |
| `san_pham/` | Sản phẩm cục bộ và hồ sơ duyệt; cũng được Git bỏ qua. |
| [tests](tests) | Kiểm thử hồi quy và các giai đoạn. |

Các tên thư mục trong `data/` hiện có thể khác mặc định trong code. Đặc biệt, cleaning và một số notebook OCR vẫn dùng ánh xạ `BacSu`, `ThiDinh`, `LyTran`; dữ liệu cục bộ đã đổi sang `CP09`, `CP011`, `CP012`. Xem hướng dẫn từng notebook trước khi chạy, không đổi hoặc sao chép PDF nguồn để khắc phục đường dẫn.

## Cài đặt

Cần Python 3.11 trở lên. Với Windows, từ thư mục gốc:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements\base.txt
.\.venv\Scripts\python.exe -m pip install -r requirements\dev.txt
```

Trên Linux/macOS, thay `.\.venv\Scripts\python.exe` bằng `.venv/bin/python`. Với OCR, xem [hướng dẫn OCR](notebooks/02_ocr/README.md) và [requirements/ocr.txt](requirements/ocr.txt); các engine có thể cần cài đặt hệ thống hoặc môi trường GPU riêng. Mẫu biến môi trường nằm trong [.env.example](.env.example); không đưa token hoặc `.env` vào Git.

## Điểm bắt đầu

1. Kiểm tra nguồn, phạm vi và đường dẫn trong [ten_file.py](ten_file.py); đọc [hướng dẫn notebook](notebooks/README.md).
2. Dùng [01_source_preparation.ipynb](notebooks/01_source_preparation.ipynb) để chuẩn bị nguồn theo tác phẩm. PDF gốc bất biến; không ghi đè, đổi tên hay di chuyển chúng.
3. Khi được phân công các bước tiếp theo, dùng [OCR_han.ipynb](notebooks/02_ocr/OCR_han.ipynb), [OCR_viet.ipynb](notebooks/02_ocr/OCR_viet.ipynb), [clean_text.ipynb](notebooks/clean_text.ipynb) và [dong_hang.ipynb](notebooks/dong_hang.ipynb) theo đúng nguồn và chế độ.
4. Duyệt kết quả thủ công trước khi xuất. Riêng đầu vào CP024, xem mục CP024 trong [notebooks/README.md](notebooks/README.md).

Công cụ dòng lệnh có thể xem tham số bằng `--help`, chẳng hạn:

```powershell
.\.venv\Scripts\python.exe scripts\run_cleaning_stage.py --help
.\.venv\Scripts\python.exe scripts\run_ocr_cross_check.py --help
.\.venv\Scripts\python.exe scripts\run_llm_alignment_review.py --help
.\.venv\Scripts\python.exe scripts\run_evaluation_report.py --help
```

## Kiểm thử và tài liệu

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Xem thêm [kiến trúc](docs/architecture.md), [phương pháp làm sạch](docs/methodology/TEXT_CLEANING.md), [phương pháp dóng hàng](docs/methodology/ALIGNMENT_METHOD.md), [hậu kiểm LLM](docs/methodology/LLM_ALIGNMENT_REVIEW.md) và [khả năng tái lập](docs/reproducibility.md).
