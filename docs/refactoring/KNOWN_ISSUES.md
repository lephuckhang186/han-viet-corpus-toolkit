# Các vấn đề đã biết & Giới hạn ghi nhận

Các vấn đề này được phát hiện trong pha kiểm toán kho mã nguồn (Giai đoạn 01). Các điểm kỳ dị nằm bên trong **logic được bảo vệ** được ghi nhận lại ở đây thay vì âm thầm chỉnh sửa.

## 1. Các đặc thù trong Logic được Bảo vệ (Không chỉnh sửa)

1. **`cong_cu/dong_hang.py` (`load_work` nhập nhằng khi quét nguồn nhiều nơi)**:
   - Dòng 142 cho phép `len(paths) > 1` chỉ khi `len({path.parent for path in paths}) == 1` VÀ `paths[0].parent.name not in {"han", "dich_am", "dich_nghia", "dich_tho"}`.
   - Trong khi đó `clean_sources_by_work` gom cả `san_pham/<member>/.../03_text_sach/.../*.txt` VÀ (với `CPO_12`) `data/LyTran/03_text_sach/.../phan*.txt`. Nếu cùng một bài vừa có file TXT đã ghép trong `san_pham` vừa có các file phần trong `data/LyTran`, `load_work` sẽ báo lỗi `ValueError: Có nhiều TXT cho ...` vì thư mục cha khác nhau.
2. **`cong_cu/bac_su_notebook.py` (`exclude_couplets` gán cứng ký tự lỗi font)**:
   - Dòng 26 tìm chuỗi `"Phía trƣớc có ba"` với ký tự lỗi `ƣ` (`U+01A3`). Hàm chạy đúng trên bản thô `data/BacSu/03_text_sach/viet/viet.txt` chừng nào file còn `ƣ`; sẽ không khớp nếu `viet.txt` bị chuẩn hóa sang `ư` trước khi gọi hàm này. Giữ nguyên hành vi theo quy tắc bảo vệ.
3. **`cong_cu/dong_hang.py` (`clean_sources_by_work` gán cứng đường dẫn tương đối `data/LyTran`)**:
   - Dùng `book_root.parents[2] / "data" / "LyTran" / "03_text_sach" / folder`, giả định độ sâu thư mục cố định cho `book_root`. Đã giữ nguyên ở wrapper tương thích đồng thời bổ sung hỗ trợ cấu hình `data_root` linh hoạt ở tầng mới.
4. **`notebooks/clean_text.ipynb` (`clean_viet` chỉ đổi `Ƣƣ -> Ưư` khi `native_pdf=True`)**:
   - Chỉ thực hiện `Ƣƣ -> Ưư` khi `native_pdf=True` (tức nguồn `01_nguon` PDF Text). Tuy nhiên các bản xuất ở `san_pham/TV04/CV06_CPO_09` trước đây vẫn kế thừa `ƣ` trong một số bảng nháp. Đã giữ nguyên hành vi của `clean_viet` và ghi nhận bước kiểm tra thủ công / prompt làm sạch Việt để thành viên rà soát.
5. **`notebooks/clean_text.ipynb` (`apply_decisions` & dấu ngăn trang)**:
   - `assemble_works` ngăn trang/file bằng `\f`, nhưng nếu dòng cuối trang dùng `join_next` nối sang dòng đầu trang sau thì dấu `\f` tại biên đó không được chèn. Hành vi này được giữ nguyên hoàn toàn.
6. **`cong_cu/alignment_backends.py` (`run_lab` dùng `csv.DictWriter` không khai báo `quoting` tường minh)**:
   - Giả định `ID`, `HanNom`, `DichAm` không làm vỡ cấu trúc TSV/CSV kỳ vọng của mã Lab. Được giữ nguyên tuyệt đối.
7. **`cong_cu/dong_hang.py` (`segment` & ngoại lệ viết tắt trong `split_prose`)**:
   - Regex `r"\b(?:TS|GS|PGS|ThS|TP|Q|tr|vd)\.$"` bỏ qua dấu chấm sau các từ viết tắt này bất kể ngữ cảnh; đồng thời `clean_spacing` gộp nhiều khoảng trắng/xuống dòng liên tiếp. Được giữ nguyên tuyệt đối.

## 2. Vấn đề về Cấu hình, Hạ tầng & Môi trường

1. **Lệch mã thành viên mặc định**: `ten_file.py` đặt `THANH_VIEN = 2` (`TV02`), trong khi dữ liệu đang làm việc ở workspace (`san_pham/TV04`, `notebooks/clean_text.ipynb`, `notebooks/dong_hang.ipynb`, `notebooks/ocr_nlp.ipynb`) chạy cho `TV04`. Đã giải quyết bằng `configs/members/TV02.yaml` và `TV04.yaml` mà không tự ý sửa mặc định của `ten_file.py`.
2. **Thiếu khai báo gói phụ thuộc**: `requirements.txt` cũ thiếu `PyYAML`, `requests`, `XlsxWriter`, `pandas`, `numpy` cũng như các gói OCR/dóng hàng/LLM/dev. Đã khắc phục bằng bộ file `requirements/*.txt` theo từng giai đoạn và `pyproject.toml`.
3. **`.gitignore` trước đó bỏ qua `/tests`**: Commit `b7e3ea85` bỏ qua `/tests`. Đã gỡ `/tests` khỏi `.gitignore` để bộ kiểm thử được theo dõi cùng dự án.
4. **Hỗ trợ LLM cho Text Cleaning dùng quy trình thủ công không API (Task 04)**: Theo ràng buộc dự án, giai đoạn Làm sạch văn bản **không** tích hợp LLM API client, **không** yêu cầu API key và **không** tự động sửa văn bản. Hai prompt đầy đủ cho Hán và Việt được đặt trực tiếp trong `src/hanviet/cleaning/README.md`, `notebooks/README.md` và `prompts/cleaning/{han,viet}_cleaning.md` để thành viên sao chép sang công cụ LLM hoặc Coding Agent của mình rồi cập nhật thủ công vào `duyet_lam_sach.csv`.
5. **Thiếu `Guideline.pdf` và các PDF gốc trong workspace**: Các kiểm thử cần PDF sách gốc sẽ tự động bỏ qua có ghi nhận nếu PDF không tồn tại cục bộ, không giả lập hay báo đạt giả tạo.
6. **Các động cơ OCR/dóng ngoài chưa cài trong `.venv` cục bộ**: `paddleocr`, `paddlex`, `transformers`, `torch`, `vietocr`, `pytesseract`/Tesseract binary, `bertalign`, `vecalign` không có sẵn trong `.venv` Windows hiện tại. Các adapter đã được kiểm tra chặt chẽ về interface, schema, đối chiếu chéo và mock fixture offline; khi suy luận OCR thật cần chạy trên môi trường đã cài các gói/binary tương ứng (như Kaggle/Colab hoặc máy có GPU + Tesseract).
