# Phương pháp Trích xuất Dual-OCR (`OCR_METHOD.md`)

## 1. Định nghĩa bài toán
Tài liệu cổ chữ Hán–Nôm (`Hán`) và bản dịch tiếng Việt (`Dịch âm`, `Dịch nghĩa`, `Dịch thơ`) có nhiều đặc thù phức tạp: cột dọc đọc từ phải sang trái (`Thi Đình`, `Bắc sứ`), hàng ngang thơ (`Lý–Trần`), mực thấm xuyên trang, dấu triện đỏ và chữ Nôm hiếm. Dùng một bộ OCR duy nhất dễ bỏ sót chữ, đảo thứ tự cột hoặc sai dấu thanh.

## 2. Đầu vào và Đầu ra
- **Đầu vào**: Ảnh PNG cắt theo tác phẩm/phiên bản từ Giai đoạn 01 (`01_nguon/`) hoặc lớp chữ PDF / TXT gốc (`native_text`).
- **Đầu ra**: TXT/JSON thô độc lập theo từng engine + Bản ghi OCR dùng chung đạt chuẩn `schemas/ocr_record.schema.json` lưu tại `02_ocr_tho/{han,viet}/<engine>/` hoặc `native_text/`.

## 3. Đặc điểm dữ liệu
- `CPO_11` (`Văn sách thi Đình`): Cột dọc đọc từ phải sang trái, xen tiểu chú nhỏ.
- `CPO_12` (`Thơ văn Lý–Trần`): Hàng ngang chữ Hán và các dòng dịch tiếng Việt.
- `CPO_09` (`Bắc sứ thông lục`): Bản Hán scan có dấu đỏ/thấm trang (`bac_su_preprocess`: lọc màu đỏ HSV + bù nền + nhị phân Otsu tùy chọn) và bản Việt PDF Text trích nguyên lớp chữ kèm ký tự ngắt trang `\f`.

## 4. Phương pháp luận
- **Nhánh Hán**: `PaddleOCR` (`PP-OCRv6_medium_det` + `PP-OCRv6_medium_rec`, engine chính) kết hợp đối chứng với `CLC OCR` (`image-upload` + `image-ocr`, engine phụ).
- **Nhánh Việt**: `Tesseract OCR` (`vie`, `--oem 3 --psm 6 tsv`, engine chính) kết hợp đối chứng với `VietOCR` (`vgg_transformer` cấp dòng sau `TextDetection` + `line_crop`, engine phụ).
- **Văn bản sẵn chữ (Native Text)**: PDF Text và TXT UTF-8 đi qua `hanviet.extraction.native_text`, không gọi OCR hoặc API.

## 5. Thuật toán
1. Tiền xử lý ảnh Hán giữ nguyên hệ tọa độ 1:1 (`bac_su_preprocess`) hoặc tách hàng ngang bằng chiếu mực (`horizontal_han_rows`).
2. Sắp xếp thứ tự đọc (`grouped_vertical_columns` cho cột phải $\rightarrow$ trái, `top_to_bottom` cho hàng ngang/Việt).
3. Chạy hai engine độc lập, không gộp điểm tin cậy chưa hiệu chuẩn để chọn kết quả tự động.

## 6. Triển khai mã nguồn
- `src/hanviet/extraction/engines/{paddle_han,clc_han,tesseract_viet,vietocr_viet}.py`
- `src/hanviet/extraction/preprocessing/{han_preprocess,viet_preprocess}.py`
- `src/hanviet/extraction/native_text/extractor.py`
- Cấu hình: `configs/methods/ocr.yaml`.

## 7. Kiểm tra thủ công
Mọi vùng tin cậy thấp, cảnh báo hình học (`small_or_short_regions`, `separated_regions_in_column`, `ambiguous_column_assignment`) và vị trí bất đồng giữa hai engine đều phải đưa vào bước hiệu đính thủ công trước khi làm sạch văn bản.

## 8. Chỉ số đánh giá
Chỉ tính `CER`, `WER` (`hanviet.evaluation.metrics`) khi có bản chép chuẩn do người kiểm tra (`reference_available=True`); tuyệt đối không dùng điểm tin cậy nội bộ làm độ chính xác.

## 9. Phân tích lỗi
Các lỗi phổ biến: sót số/tiểu chú kích thước nhỏ, nhiễu dấu triện ở Bắc Sứ, nhầm chữ Nôm mở rộng Extension B+, và cắt cụt chuỗi VietOCR khi vượt `VIETOCR_MAX_WIDTH = 512px`.

## 10. Hạn chế
- CLC OCR API cần mạng và bị giới hạn quota (`25/phút`, `50/giờ`, `200/ngày`, `600/tuần`).
- Tesseract cần cài binary hệ thống và gói `vie.traineddata` ngoài Python pip.
- Confidence của PaddleOCR, Tesseract và VietOCR nằm trên các thang đo khác nhau, không so sánh trực tiếp.

## 11. Khả năng tái lập thực nghiệm
Cấu hình cố định trong `configs/methods/ocr.yaml`, lưu SHA-256 đầu vào/cấu hình cho từng ảnh và bảo toàn bản OCR thô tách biệt với bản đã hiệu đính.
