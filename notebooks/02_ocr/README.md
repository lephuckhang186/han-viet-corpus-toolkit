# Notebook OCR

Thư mục này có [OCR_han.ipynb](OCR_han.ipynb) và [OCR_viet.ipynb](OCR_viet.ipynb). Chúng phục vụ bước trích xuất sau khi nguồn và phạm vi đã được xác định; không sửa PDF hoặc ảnh gốc. Chọn kernel và cài môi trường theo [README gốc](../../README.md). Các engine OCR có thêm yêu cầu riêng trong [requirements/ocr.txt](../../requirements/ocr.txt); phiên bản thư viện và thiết bị cần phù hợp môi trường chạy.

## OCR_han.ipynb

1. Chạy cell import và kiểm tra `Project root`, `Data root`, `Output root` cùng tình trạng phụ thuộc được in ra.
2. Chỉnh cell cấu hình `CORPUS_ID`, `MEMBER_ID`, `TOPIC_CODE`, `SELECTED_WORKS`, `SELECTED_PAGES`, `INPUT_ROOT`, `OUTPUT_ROOT`, `DEVICE`, `MAX_IMAGES` và `RUN_ID` theo nguồn. `MAX_IMAGES = 3` giới hạn lần thử; `None` chọn toàn bộ.
3. Notebook mặc định ánh xạ `CPO_09 → BacSu`, `CPO_11 → ThiDinh`, `CPO_12 → LyTran`. Nếu dữ liệu nằm tại `data/CP09`, `data/CP011`, `data/CP012`, đặt `INPUT_ROOT` trực tiếp tới thư mục `01_nguon/han` tương ứng hoặc chỉnh `BOOK_FOLDER_MAP` trong cell. Kiểm tra danh sách ảnh được chọn trước khi OCR.
4. Chạy các cell theo `MODE`: `preprocess`, `paddle_ocr`, `clc_ocr` hoặc `import_clc`; tiếp đó `cross_check`, `review`, `apply_corrections`, `evaluate` và `export` khi phù hợp. Không phải chế độ nào cũng cần thiết cho mọi nguồn.
5. `CALL_CLC_API = False` giữ CLC ở chế độ không gửi yêu cầu khi chưa có cache. Chỉ bật `True` khi đã cấu hình xác thực và muốn gửi ảnh tới CLC. OCR CLC và CLC dóng hàng là hai tác vụ khác nhau.

Đối chiếu `review_queue.csv` với ảnh nguồn và kết quả engine, rồi nhập quyết định trong `review_decisions.csv` hoặc hàng đợi. Chỉ người duyệt mới quyết định chữ khuyết và `[MASK]`. Bất đồng hoặc đồng thuận giữa hai engine không tự chứng minh nội dung đúng. Không ghi đè dữ liệu OCR thô; kiểm tra `OVERWRITE` và trạng thái duyệt trước khi xuất. `EXPORT_APPROVED` có thể cho phép xuất nháp khi chưa duyệt, nên không coi output đó là bản hoàn chỉnh.

Các thư mục đầu ra được tạo dưới `OUTPUT_ROOT` đã chọn và phân biệt dữ liệu Paddle, CLC, đối chiếu, duyệt và bản hiệu đính. Chi tiết phương pháp ở [OCR_CROSS_CHECK.md](../../docs/methodology/OCR_CROSS_CHECK.md).

## OCR_viet.ipynb

Notebook có nhiều cell và nhánh tác vụ; đọc nội dung từng cell trước khi chạy, đặc biệt cell CLC riêng ở đầu notebook. Trong cell cấu hình chính, kiểm tra `RUNTIME`, `INPUT_MODE`, `LOCAL_INPUT_ROOT`, `OUTPUT_ROOT`, `DEVICE`, `SELECTED_JOBS` và các đường dẫn trong `JOBS`. Chọn đúng thư mục ảnh/TXT và phạm vi cho từng job; với môi trường local, dùng đường dẫn hiện có sau khi các thư mục `data/` được đổi tên.

Kaggle/Colab và Google Drive chỉ cần khi chọn nguồn hoặc output trên các môi trường đó. Không đưa token, secret hoặc file xác thực vào notebook/Git. Dùng giới hạn ảnh của notebook để kiểm tra trước, xem bảng lựa chọn và kết quả mẫu, sau đó mới quyết định chạy phạm vi lớn. Nếu bản PDF đã có text và phần việc yêu cầu giữ TXT nguồn thô, không chạy OCR hoặc làm sạch thay cho nguồn gốc.

## Chuyển tiếp và kiểm thử

Sau khi kiểm tra kết quả, chuyển bản phù hợp sang bước làm sạch theo [hướng dẫn cleaning](../../src/hanviet/cleaning/README.md). Có thể đối chiếu hai JSON OCR đã lưu bằng CLI:

```powershell
.\.venv\Scripts\python.exe scripts\run_ocr_cross_check.py --help
```

Chạy lệnh từ thư mục gốc repo. Tham số `--primary`, `--secondary`, `--variant` và `--output-dir` dùng đường dẫn thực tế của lần chạy; `--dp-line-match` là tùy chọn. Không báo cáo precision/recall/accuracy nếu không có dữ liệu chuẩn phù hợp.
