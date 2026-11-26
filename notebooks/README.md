# Hướng dẫn thư mục notebooks

Notebook trong thư mục này được chạy theo từng cell. Mở repo trong Jupyter/VS Code, chọn kernel Python của `.venv`, kiểm tra cấu hình ở đầu cell và đường dẫn được in ra trước khi chạy. Hướng dẫn cài đặt chung nằm ở [README gốc](../README.md).

| Notebook | Chức năng |
|---|---|
| [01_source_preparation.ipynb](01_source_preparation.ipynb) | Chuẩn bị nguồn PDF/TXT và vùng theo tác phẩm. |
| [02_ocr/OCR_han.ipynb](02_ocr/OCR_han.ipynb) | OCR Hán, đối chiếu engine và duyệt thủ công. |
| [02_ocr/OCR_viet.ipynb](02_ocr/OCR_viet.ipynb) | Notebook OCR ảnh/PDF Text và các cấu hình local, Kaggle, Colab. |
| [clean_text.ipynb](clean_text.ipynb) | Tạo bảng duyệt, áp dụng quyết định làm sạch và xuất TXT. |
| [dong_hang.ipynb](dong_hang.ipynb) | Các cell dóng hàng và gộp bảng. |

[tao_quyen_drive.py](tao_quyen_drive.py) là script riêng trong thư mục này. Hướng dẫn OCR chi tiết ở [02_ocr/README.md](02_ocr/README.md); hướng dẫn mô-đun làm sạch ở [cleaning/README.md](../src/hanviet/cleaning/README.md).

## Chuẩn bị nguồn

Đọc [CONTEXT.md](../CONTEXT.md), [phancong.md](../phancong.md) và cấu hình nguồn trong [ten_file.py](../ten_file.py). Chọn cell của sách và kiểm tra nguồn, phạm vi, bài, phiên bản trước khi lưu. Số trang tính theo thứ tự trong trình đọc PDF từ 1. Một trang có thể chứa nhiều tác phẩm; một tác phẩm có thể trải qua nhiều trang. Giữ Hán, dịch âm, dịch nghĩa và dịch thơ thành các phiên bản riêng và ghi rõ bản thiếu.

Trong `01_source_preparation.ipynb`, chạy cell thiết lập chung, sau đó chỉnh cell sách: `ACTION = 'info'` để xem, `prepare` để chuẩn bị workspace và bản sao, `check` để kiểm tra, hoặc `gui`/`crop_page` để làm việc với vùng. `CUSTOM_*_PAGES` và các lựa chọn khác nằm trong cell tương ứng. Đối chiếu `TEN_NGUON` với vị trí PDF thực tế trước khi chạy. Không ghi đè, đổi tên hoặc di chuyển PDF gốc; không xem một vùng nháp là đã duyệt đủ.

Với phần Bắc sứ TV2, bàn giao Việt hiện là TXT nguồn thô, giữ chú thích, ký tự và ngắt trang; các PNG Việt cũ là ảnh xem trước. Phạm vi Hán–Việt trong bảng phân công không phải ánh xạ dịch. Kiểm tra các yêu cầu bàn giao trong [AGENTS.md](../AGENTS.md).

## OCR

Chọn nguồn, phiên bản, thành viên và giới hạn ảnh trước khi chạy các cell. Đọc [hướng dẫn OCR](02_ocr/README.md) để phân biệt OCR Hán, OCR/đọc PDF Text và các chế độ đối chiếu. Sự đồng thuận giữa hai engine không thay thế kiểm tra nguồn; `[MASK]` chỉ dùng khi người duyệt xác nhận chữ không đọc được.

## Làm sạch

Mở `clean_text.ipynb` và kiểm tra cell cấu hình: `INPUT_PATH`, `OUTPUT_ROOT`, `BOOK_FOLDERS`, `SELECTED_CODES`, `SELECTED_KINDS`, `INPUT_GRANULARITY` và các cờ chạy. Notebook hiện mặc định tên thư mục nguồn cũ `BacSu`, `ThiDinh`, `LyTran`; nếu dùng dữ liệu cục bộ đã đổi tên, chỉnh `BOOK_FOLDERS` trong notebook thành `CP09`, `CP011`, `CP012` tương ứng trước khi chạy. Không thay đổi dữ liệu nguồn.

Lượt đầu đặt `EXPORT_REVIEW = True`, `APPLY_REVIEW = False`, `WRITE_OUTPUTS = False` để tạo bảng duyệt. Đối chiếu các dòng cần xem trong `duyet_lam_sach.csv` với nguồn; sau đó mới bật áp dụng và xuất theo [hướng dẫn làm sạch](../src/hanviet/cleaning/README.md). Công cụ CLI `scripts/run_cleaning_stage.py` hiện dùng ánh xạ thư mục cũ và chỉ tạo bảng duyệt/manifest, không thực hiện toàn bộ quy trình xuất TXT.

## Dóng hàng

Mở [dong_hang.ipynb](dong_hang.ipynb), chọn đúng cell sách và cấu hình thành viên, bài/mục. Với các cell dùng workflow duyệt, `nguon` xem nguồn, `nhap` tạo nháp, `xuat` xuất bản duyệt. Cell Bắc sứ có giao diện riêng: xem `XEM_NGUON` và các biến đầu cell trước khi chạy. Một số cell phụ thuộc cấu trúc và thư mục đầu vào riêng; kiểm tra các đường dẫn in ra và hướng dẫn trong cell.

CLC dùng `CLC_API_KEY` trong `.env` ở thư mục gốc. Chạy cell nạp token để đưa giá trị vào kernel khi cần gọi CLC; cell không hiển thị token. Xem `draft.json`, sao chép `review_template.json` thành `review.json`, duyệt liên kết, điền lý do cho từng ID chưa ghép trong `skipped`, sau đó mới đặt `approved` là `true` và chạy xuất. Không xem điểm CLC hay tỷ lệ bao phủ là accuracy.

### CP024

Trong cell CP024, đặt `PHUONG_PHAP = "clc"` cho API CLC hoặc `PHUONG_PHAP = "dp"` cho quy hoạch động cục bộ dựa trên độ dài và thứ tự. DP không cần nạp token. Kết quả DP dùng cùng cấu trúc file và nằm dưới `CV06_CPO_24/dp/` để có thể duyệt độc lập. Dùng cùng phương thức khi tạo nháp và xuất.

CP024 đọc TXT trực tiếp từ `data/CP024/03_text_sach/han/` và `data/CP024/03_text_sach/viet/`, ví dụ `005.han.txt` và `005.viet.txt`. Các số không cần liên tục; `5` và `005` là cùng mã. Có thể đặt `THU_MUC_DATA` là thư mục khác chứa `CP024/`, và `THU_MUC_SAN_PHAM` là gốc output khác. Không OCR lại hoặc sửa/copy TXT nguồn.

```python
# Một file
CHAY_HANG_LOAT = False
SO_FILE = 5

# Nhiều file; danh sách rỗng chọn tất cả
CHAY_HANG_LOAT = True
DANH_SACH_FILE = [5, 6]
SO_MUC = None
SO_DONG_MOI_MUC = 10
DONG_TOAN_FILE = set()
```

Mỗi file được chia thành các mục liên tiếp; `SO_MUC = None` chạy **tất cả** các mục và mỗi yêu cầu CLC chứa tối đa 10 dòng TXT không trống của mỗi bản. Một dòng nguồn có thể có nhiều câu: CLC nhận các dòng gốc, còn kết quả được ánh xạ lại vào các ID đơn vị câu. Nếu một đơn vị câu đi qua ranh giới các liên kết do CLC trả về, chương trình báo lỗi để duyệt thủ công, không tự nhân bản câu.

Chạy `CHE_DO = 'nguon'` để xem phạm vi, đối chiếu nội dung Hán–Việt ở ranh giới từng mục và đặt `XAC_NHAN_RANH_GIOI = True` sau khi đã kiểm tra. Số dòng bằng nhau không chứng minh nội dung tương ứng. Nếu hai bản lệch số dòng, cấu hình `KHOANG_DONG_THEO_FILE` theo khoảng 1-based, bao gồm cả hai đầu, liên tục và bao phủ toàn bộ nguồn; mỗi khoảng của mỗi bản dài tối đa 10 dòng. Nếu ranh giới cần chỉnh, lưu trữ an toàn kế hoạch và draft/review cũ trước khi tạo lại. Khi chạy `nhap`, bản nháp hợp lệ đã có được dùng lại, không tự gọi CLC lần nữa.

Đầu ra của CP024 nằm trong `san_pham/TV04/CV06_CPO_24/`. Mỗi bài có một cặp TSV/XLSX trong `04_dong_hang/baiNNNN/`, với hậu tố `_ban_nhap` ở chế độ `nhap` và `_parallel` ở chế độ `xuat`. Các JSON theo bài nằm trong `05_quan_ly/dong_hang/TV04/baiNNNN/`. Mỗi loại JSON có một file chứa các mục theo khóa `mucNNNN`.

Duyệt liên kết trong `review.json` của bài, ghi lý do cho ID chưa dóng và xác nhận `approved = true` ở từng mục trước khi chạy `xuat`. Giữ `SO_MUC = None` để xử lý toàn bài. Bản nháp và phản hồi CLC theo lượt được lưu trong vùng làm việc cũ để có thể tiếp tục khi chạy lại.


### Gộp bảng

Trong cell gộp của `dong_hang.ipynb`, chọn `TAC_PHAM_CHON = ['CPO_24']` hoặc kết hợp `['CPO_11', 'CPO_12', 'CPO_24']`. Cell đọc bảng xuất trong `04_dong_hang/` và kiểm tra bốn cột. Số bảng được gộp không chứng minh toàn corpus đã hoàn thành.
