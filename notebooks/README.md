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
