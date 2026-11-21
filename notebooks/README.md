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
