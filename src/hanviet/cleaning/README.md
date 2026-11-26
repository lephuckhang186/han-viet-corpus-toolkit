# Mô-đun làm sạch `hanviet.cleaning`

Thư mục này chứa các quy tắc và hàm xử lý văn bản sau OCR hoặc trích xuất: [han_cleaner.py](han_cleaner.py) xử lý bản Hán, [viet_cleaner.py](viet_cleaner.py) xử lý bản Việt, còn [pipeline.py](pipeline.py) đọc nguồn, tạo hàng duyệt, áp dụng quyết định và ghép TXT theo tác phẩm. Bước làm sạch có thể thay đổi khoảng trắng, ký tự hoặc dòng theo quy tắc và quyết định; cần đối chiếu nguồn, không xem kết quả tự động là bản đã được xác nhận.

Đây là bước xử lý sau chuẩn bị nguồn. Không sửa hoặc thay thế PDF, TXT thô và kết quả OCR gốc. Với Bắc sứ TV2, TXT Việt nguồn thô bàn giao ở bước 3 giữ nguyên chú thích, ký tự và ngắt trang; không dùng bản làm sạch thay cho bản bàn giao đó.

## Đầu vào và cấu hình

`read_sources()` trong `pipeline.py` nhận thư mục hoặc ZIP, quét TXT trong `02_ocr_tho/` theo bản văn. Hàm cũng nhận TXT Bắc sứ dịch nghĩa ở `01_nguon/viet/dich_nghia/`. Các tham số `selected_codes`, `selected_kinds`, `member_number` và `input_granularity` giới hạn dữ liệu. `parts` chọn TXT theo phần; `merged` chọn tên kết thúc `_ocr_tho.txt`.

Ánh xạ mặc định trong module hiện là `CPO_09 → BacSu`, `CPO_11 → ThiDinh`, `CPO_12 → LyTran`. Các thư mục cục bộ tương ứng đã đổi thành `CP09`, `CP011`, `CP012`: khi gọi Python trực tiếp, truyền ánh xạ qua tham số `book_folders`; notebook có `BOOK_FOLDERS` để chỉnh. CLI hiện không có tham số ánh xạ, vì vậy cần kiểm tra phù hợp nguồn trước khi dùng CLI. Module này không nhận trực tiếp cấu trúc `CP024/03_text_sach/` làm đầu vào cleaning; CP024 đã có TXT dùng cell riêng trong [dong_hang.ipynb](../../../notebooks/dong_hang.ipynb).

## Dùng notebook

Mở [clean_text.ipynb](../../../notebooks/clean_text.ipynb) trong kernel dự án và kiểm tra `INPUT_PATH`, `OUTPUT_ROOT`, `BOOK_FOLDERS`, `SELECTED_CODES`, `SELECTED_KINDS` và `INPUT_GRANULARITY`. Lần tạo bảng duyệt đầu tiên, đặt:

```python
EXPORT_REVIEW = True
APPLY_REVIEW = False
WRITE_OUTPUTS = False
```

Chạy các cell tạo dữ liệu và xem bảng `duyet_lam_sach.csv` trong thư mục `05_quan_ly/<RUN_NAME>/` của output. Mỗi hàng có văn bản nguồn `raw`, đề xuất `clean`, lý do cần xem và thông tin truy vết. Đối chiếu nguồn, chỉ sửa các cột quyết định `action`, `replacement`, `note`:

| `action` | Ý nghĩa |
|---|---|
| `keep` | Giữ đề xuất ở cột `clean`. |
| `replace` | Dùng nội dung không rỗng trong `replacement`. |
| `delete` | Bỏ dòng sau khi đã kiểm tra. |
| `join_next` | Ghép với dòng kế tiếp theo logic pipeline. |

Sau khi lưu CSV, đặt `APPLY_REVIEW = True` để xem kết quả, và chỉ đặt `WRITE_OUTPUTS = True` khi đã duyệt. `REQUIRE_ALL_FLAGS_REVIEWED = True` chặn xuất khi còn dòng được đánh dấu chưa có quyết định. Không sửa các cột nguồn, hash hoặc ID trong CSV.

## Dùng module hoặc CLI

Từ thư mục gốc repo, sau khi cài các gói cơ bản, xem tham số:

```powershell
.\.venv\Scripts\python.exe scripts\run_cleaning_stage.py --help
```

Script này dùng `read_sources()` và `build_records()` để tạo bảng duyệt và manifest trong `--output-dir`. Nó **không** đọc quyết định đã duyệt để tự xuất TXT sạch. Với dữ liệu không khớp tên thư mục mặc định, dùng notebook đã cấu hình hoặc gọi API Python với `book_folders` phù hợp.

Các hàm chính trong [pipeline.py](pipeline.py) gồm `read_sources`, `build_records`, `read_decisions`, `apply_decisions` và `assemble_works`. Xem chữ ký thực tế trong mã trước khi tích hợp. Các hàm làm sạch không tự dịch và không thay thế bước duyệt nội dung.

## Hỗ trợ duyệt thủ công

Có thể dùng [prompt Hán](../../../prompts/cleaning/han_cleaning.md) hoặc [prompt Việt](../../../prompts/cleaning/viet_cleaning.md) để xin đề xuất, kèm ảnh và ngữ cảnh phù hợp nếu có. Người dùng phải kiểm tra mọi đề xuất so với nguồn trước khi nhập quyết định; không tự thêm `[MASK]` hay khôi phục chữ chỉ dựa vào phỏng đoán. Xem thêm [phương pháp làm sạch](../../../docs/methodology/TEXT_CLEANING.md) và [hướng dẫn notebook](../../../notebooks/README.md).
