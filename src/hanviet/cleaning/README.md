# Hướng dẫn Làm sạch Văn bản Hán–Việt (Text Cleaning) & Kiểm tra Thủ công với LLM

> Tài liệu dành cho thành viên sử dụng [clean_text.ipynb](../../../notebooks/clean_text.ipynb), [03_text_cleaning.ipynb](../../../notebooks/03_text_cleaning.ipynb), hoặc script [run_cleaning_stage.py](../../../scripts/run_cleaning_stage.py) kết hợp với module `hanviet.cleaning`.

---

## 1. Mục tiêu của Text Cleaning

Giai đoạn Text Cleaning (Bước 5) chuẩn hóa định dạng kỹ thuật của văn bản sau OCR / trích xuất PDF Text mà **tuyệt đối bảo toàn nội dung nguyên tác**:

- Chuẩn hóa khoảng trắng (`whitespace`), bỏ ngoặc rỗng (`empty_brackets`), chuẩn hóa Unicode Latin NFC cho tiếng Việt (`vietnamese_nfc`), chuyển mã ký tự PDF lỗi font (như `Ƣ`/`ƣ` $\rightarrow$ `Ư`/`ư` trên PDF Text Bắc Sứ) và xóa mốc tờ `[\d{1,3}[ab]]`.
- Đánh dấu (không tự ý xóa) các dòng có nguy cơ mất/nhiễu dữ liệu để con người đối chiếu ảnh gốc trước khi xuất TXT sạch.
- **Không** tự động dịch lại, **không** giản thể hóa chữ Hán, **không** xóa từ ngoài từ điển, **không** tách câu hay dóng hàng ở bước này.
- **Không sử dụng LLM API tự động**: thành viên sử dụng LLM thủ công (sao chép prompt gửi ChatGPT, Gemini, Claude hoặc Coding Agent) sau rule-based cleaning và trước bước duyệt thủ công cuối cùng.

---

## 2. Yêu cầu môi trường

- Python `>= 3.11`.
- Chỉ cần các gói cơ bản trong `requirements/base.txt`: `PyYAML`, `pandas`, `Pillow` (tùy chọn `pypdfium2` nếu dùng chế độ xem cả trang PDF trong notebook).
- **Không yêu cầu** cài PaddleOCR/Torch GPU hoặc có API key LLM để chạy Text Cleaning.

---

## 3. Cách cấu hình đường dẫn

Module sử dụng `hanviet.common.paths.resolve_paths()` theo thứ tự ưu tiên:
1. Tham số truyền trực tiếp (`user_root=...`, `--input-path`, `--output-dir`).
2. Biến môi trường (`HANVIET_PROJECT_ROOT`, `HANVIET_DATA_ROOT`, `HANVIET_OUTPUT_ROOT`, `HANVIET_ENV`).
3. File cấu hình [configs/project.yaml](../../../configs/project.yaml) và [configs/methods/cleaning.yaml](../../../configs/methods/cleaning.yaml).
4. Tự động tìm thư mục gốc repo chứa `ten_file.py` hoặc `pyproject.toml`.

Trong notebook [clean_text.ipynb](../../../notebooks/clean_text.ipynb), kiểm tra các biến đầu cell 1: `PROJECT_ROOT`, `INPUT_PATH`, `OUTPUT_ROOT`, `SELECTED_CODES`, `SELECTED_KINDS`, `INPUT_GRANULARITY = "parts"`, `RUN_NAME`.

---

## 4. Cấu trúc dữ liệu đầu vào

Thuật toán `read_sources()` đọc thư mục hoặc file `.zip` chứa một trong hai nguồn hợp lệ:
- **OCR thô (`02_ocr_tho/`)**:
  - Chế độ `parts` (mặc định): các file `phanXXXX_pdfpYYYY.txt` kèm `.meta.json` và ảnh cắt trong `01_nguon/` để liên kết số trang PDF (`pdf_page`), ảnh (`source_image`) và tọa độ vùng (`polygon`).
  - Chế độ `merged`: các file kết thúc bằng `_ocr_tho.txt` kèm `05_quan_ly/ghep_theo_tac_pham.json`.
- **PDF Text nguồn thô (`01_nguon/viet/dich_nghia/`)**: dành riêng cho Việt Bắc Sứ (`CPO_09`), giữ `\f` ngăn trang và chỉ mục `05_quan_ly/nguon_tho_viet.json`.

---

## 5. Cách chạy thuật toán làm sạch hiện tại

Có thể chạy bằng một trong hai cách (thuật toán `clean_han`, `clean_viet`, `build_records`, `apply_decisions`, `assemble_works` giữ nguyên 100%):

- **Cách 1 — Chạy qua Notebook**: Mở `notebooks/clean_text.ipynb` (hoặc `notebooks/03_text_cleaning.ipynb`), lượt đầu đặt `EXPORT_REVIEW = True`, `APPLY_REVIEW = False`, `WRITE_OUTPUTS = False` để sinh bảng `duyet_lam_sach.csv`.
- **Cách 2 — Chạy qua Script CLI độc lập**:
  ```bash
  python scripts/run_cleaning_stage.py --member 4 --codes CPO_09 CPO_11 CPO_12 --output-dir san_pham/TV04/05_quan_ly/clean_v04_parts
  ```

---

## 6. Cách đọc kết quả và các cảnh báo

Bảng `duyet_lam_sach.csv` hiển thị song song bản gốc (`raw`), bản sau quy tắc tự động (`clean`), ngữ cảnh trước/sau (`context_before`, `context_after`) và 2 cột chẩn đoán:
- **`automatic_rules`**: Các quy tắc an toàn đã áp dụng (`whitespace`, `empty_brackets`, `punctuation_config`, `vietnamese_nfc`, `vietnamese_pdf_glyph`, `vietnamese_pdf_folio`, `standalone_version_label`).
- **`reasons`** (cờ nghi vấn cần duyệt):
  - `possible_note_marker`: chứa dạng `(1)`, `[12]`, `【1】`.
  - `unbalanced_brackets`: ngoặc đơn/vuông đóng mở lệch nhau.
  - `standalone_number`: cả dòng chỉ có chữ số (dễ là số trang).
  - `letters_attached_to_digits`: chữ dính số (ví dụ `người1` — cột `suggested` gợi ý bỏ hậu tố số cho bản Việt, **chưa tự áp dụng**).
  - `unexpected_symbol`: ký tự rác (`_`, `#`, `\ufffd`, control chars).
  - `latin_in_han`: xuất hiện chữ cái Latin trong dòng Hán (ngoại trừ `[MASK]`).
  - `han_symbol_check` / `percent_check`: chứa `%`, `％`, `○`.
  - `possible_note_section`: dòng dạng `Chú thích:`.
  - `repeated_line`: dòng lặp lại từ 2 lần trở lên trong tác phẩm (có thể là tiêu đề lặp hoặc điệp ngữ thơ).
  - `configured_non_content_line`: khớp dòng khai báo trong `KNOWN_NON_CONTENT_LINES`.
  - `page_boundary_check`: dòng có chữ cuối cùng trước ngắt trang `\f` (kiểm tra câu có bị ngắt qua trang không).
- **`oov_tokens`** (chỉ báo tham khảo cho `dich_am`): các âm tiết ngoài từ điển `QuocNgu_SinoNom_TongHop3.csv`, không tự coi là lỗi.

---

## 7. Hướng dẫn sử dụng LLM hỗ trợ làm sạch Hán văn

1. Chạy rule-based cleaning để tạo `duyet_lam_sach.csv`.
2. Chuẩn bị từng lô nhỏ theo từng bài hoặc đoạn (không nhồi cả tập sách dài vượt quá context của mô hình), gồm: mã tác phẩm, `raw`, `clean`, `reasons`, `context_before`/`context_after`, kết quả đối chứng PaddleOCR/CLC OCR và ảnh nguồn (nếu có).
3. Sao chép **nguyên văn Prompt Hán văn ở Mục 8** dưới đây dán cho ChatGPT, Gemini, Claude hoặc Coding Agent.
4. LLM chỉ trả về **bảng đề xuất sửa và thống kê** — tuyệt đối không dùng để ghi đè trực tiếp dữ liệu hay tự ý điền vào `[MASK]`.

---

## 8. Prompt hoàn chỉnh để làm sạch Hán văn

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

---

## 9. Hướng dẫn sử dụng LLM hỗ trợ làm sạch văn bản Việt

1. Xác định rõ phiên bản cần kiểm tra: `dich_am` (phiên âm Hán–Việt), `dich_nghia` (dịch xuôi/diễn giải) hay `dich_tho` (dịch thơ).
2. Chuẩn bị dữ liệu đầu vào gồm: văn bản nguồn (OCR Tesseract/VietOCR hoặc PDF Text), văn bản sau rule-based cleaning (`clean`), danh sách `reasons` / `oov_tokens`, và ảnh PDF đối chiếu nếu có.
3. Sao chép **nguyên văn Prompt Việt ở Mục 10** dưới đây dán vào ChatGPT, Gemini, Claude hoặc Coding Agent.
4. Kiểm tra chặt để LLM **không** chuyển `dich_am` sang tiếng Việt hiện đại, **không** viết lại `dich_nghia` cho mượt hơn và **không** sửa vần điệu `dich_tho`.

---

## 10. Prompt hoàn chỉnh để làm sạch văn bản Việt

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

---

## 11. Cách đối chiếu đề xuất của LLM với ảnh hoặc tài liệu nguồn

- Với mỗi dòng được LLM đánh dấu lỗi hoặc nghi vấn trong bảng đầu ra, tra `row_id`, `pdf_page`, `source_image` và `polygon` tương ứng.
- Trong `clean_text.ipynb` (mục 4.3), đặt `REVIEW_CODE`, `REVIEW_KIND`, `REVIEW_PDF_PAGE` và `SHOW_FULL_PDF = True` (nếu cần cả trang PDF) để mở vùng ảnh gốc có khung đỏ bao quanh dòng đang xét.
- Với Bắc Sứ bản Việt (`01_nguon`), mở PDF gốc tại trang `pdf_page` để kiểm tra chân trang, chỉ mục chú thích và nguyên văn.
- Nếu bằng chứng ảnh không rõ chữ Hán và bước OCR đã xác nhận không thể phục dựng, giữ `[MASK]`; không dùng dự đoán ngữ nghĩa của LLM thay cho hình ảnh.

---

## 12. Cách cập nhật quyết định vào bảng review hiện có (`duyet_lam_sach.csv`)

### Schema thực tế của `duyet_lam_sach.csv` (22 cột)
Code hiện tại (`hanviet.cleaning.pipeline.build_records` / `clean_text.ipynb`) xuất chính xác **22 cột**:

| Nhóm | Các cột | Quy tắc sửa đổi |
|---|---|---|
| Định danh & đối chiếu (bắt buộc giữ nguyên) | `row_id`, `relative_path`, `source_sha256`, `page`, `line`, `clean` | **Cấm sửa**: `review_csv_rows()` đối chiếu khớp tuyệt đối 5 cột (`source_sha256`, `relative_path`, `clean`, `page`, `line`) và tập `row_id`. |
| Metadata & ngữ cảnh | `code`, `kind`, `work`, `raw`, `pdf_page`, `source_image`, `polygon`, `automatic_rules`, `reasons`, `suggested`, `context_before`, `context_after`, `oov_tokens` | Giữ nguyên để truy vết. |
| Cột quyết định của thành viên | `action`, `replacement`, `note` | Thành viên (hoặc Coding Agent với dòng chưa có quyết định) chỉ điền vào **3 cột này**. |

### Các giá trị `action` hợp lệ duy nhất (`validate_review_action`)
Hệ thống chỉ hỗ trợ đúng **5 trạng thái** (không phân biệt hoa/thường):
1. `""` (để trống): Chưa duyệt xong. Nếu `REQUIRE_ALL_FLAGS_REVIEWED = True` và dòng có `reasons` không rỗng thì hệ thống chặn xuất file sạch.
2. `keep`: Giữ nguyên giá trị cột `clean`.
3. `replace`: Thay nội dung dòng bằng chuỗi trong cột `replacement`. Ràng buộc bắt buộc: `replacement` không được để trống và **phải nằm trên 1 dòng** (không chứa ký tự xuống dòng `\r`, `\n`, `\f` hay `\t`).
4. `delete`: Xóa hoàn toàn dòng này khi xuất (dùng cho đầu/chân trang, số trang, chú thích ngoài nội dung chính). Không dùng `replace` với `replacement` rỗng.
5. `join_next`: Nối dòng hiện tại với dòng kế tiếp trong cùng `(code, kind, work)` (`""` đối với `han`, `" "` đối với `viet`). Không được đặt `join_next` ở dòng cuối cùng của tác phẩm.

> **Bảo vệ quyết định đã có**: Nếu dòng đã có giá trị ở cột `action` do thành viên duyệt trước đó, tuyệt đối không ghi đè; chỉ bổ sung nhận xét cảnh báo vào `note` nếu phát hiện nghi vấn mới.

---

## 13. Cách xuất văn bản sạch

1. Trong `clean_text.ipynb`: đặt `APPLY_REVIEW = True` và chạy mục **5.1** để xem trước số dòng `Chưa duyệt` (phải bằng `0` đối với các dòng có `reasons`).
2. Sau khi xác nhận ổn, đặt `WRITE_OUTPUTS = True` và chạy mục **5.2**.
3. Hàm `write_once()` kiểm tra xung đột trên mọi file đích trước khi ghi — nếu một file sạch đã tồn tại với nội dung khác, quá trình dừng lại và báo tên file để bảo vệ bản đã sửa trước đó.

---

## 14. Cấu trúc dữ liệu đầu ra

Sau khi chạy mục 5.2, sản phẩm được ghi tách biệt theo bài/bản văn tại:
```text
san_pham/TVxx/
├── CV06_CPO_xx/03_text_sach/
│   ├── han/
│   │   └── <work_stem>.txt
│   └── viet/
│       ├── dich_am/<work_stem>.txt
│       ├── dich_nghia/<work_stem>.txt
│       └── dich_tho/<work_stem>.txt
└── 05_quan_ly/<RUN_NAME>/
    ├── duyet_lam_sach.csv        # Bảng duyệt 22 cột của thành viên
    ├── work_manifest.json        # SHA-256 đầu ra & danh sách row_id nguồn
    ├── changes.jsonl             # Nhật ký trước/sau (automatic + manual)
    └── summary.json              # Thống kê tổng hợp lượt chạy
```

---

## 15. Checklist kiểm tra chất lượng

- [ ] Mọi dòng có `reasons` trong `duyet_lam_sach.csv` đều đã được kiểm tra đối chiếu ảnh/PDF và điền `action` hợp lệ (`keep`, `replace`, `delete`, `join_next`).
- [ ] Các dòng có `[MASK]` được giữ nguyên, không bị điền chữ suy đoán.
- [ ] Niên hiệu, tên người, địa danh, số lượng lịch sử khớp với ảnh nguồn.
- [ ] Các dòng chú thích ngoài nội dung Hán đã bị `delete`; chú thích hoặc niên đại thuộc chính văn được giữ.
- [ ] Không có lỗi `ƣ`/`Ƣ` sót hoặc lỗi tách dấu NFD trong bản Việt xuất.
- [ ] `summary.json` báo `unresolved_lines: 0` và file `work_manifest.json` khớp SHA-256 thực tế.

---

## 16. Các lỗi thường gặp và cách xử lý

| Thông báo lỗi / Hiện tượng | Nguyên nhân | Cách xử lý |
|---|---|---|
| `Bảng duyệt không khớp nguồn/cấu hình: <row_id> / clean` | Người dùng sửa trực tiếp vào cột `clean`, `page`, `line`, `relative_path` hoặc `source_sha256` trong CSV. | Khôi phục cột gốc; chỉ viết nội dung sửa vào cột `replacement` kèm `action = replace`. |
| `replacement phải là một dòng, không chứa TAB hay ngắt trang.` | Ô `replacement` chứa dấu xuống dòng hoặc TAB. | Chuyển thành 1 dòng duy nhất hoặc tách/giữ nhiều dòng nguồn thay vì gộp bằng `\n`. |
| `Dùng delete thay cho replacement rỗng.` | Chọn `action = replace` nhưng để trống `replacement`. | Đổi `action` thành `delete`. |
| `join_next ở cuối tác phẩm không có dòng tiếp` | Đặt `join_next` cho dòng văn bản cuối cùng của một bài. | Đổi thành `keep` hoặc `replace`. |
| `Còn N dòng cần duyệt. Chưa xuất text sạch.` | `REQUIRE_ALL_FLAGS_REVIEWED = True` nhưng vẫn còn dòng có `reasons` để trống `action`. | Mở lại `duyet_lam_sach.csv`, kiểm tra các dòng có cờ và điền `action`. |
| `File đích đã khác nội dung: ...` | Đã có bản TXT sạch trước đó có hash khác bản mới xuất. | Kiểm tra đối chiếu bản cũ; đổi `RUN_NAME` mới hoặc dọn bản xuất cũ theo quy trình mục 6 của notebook nếu chắc chắn thay thế. |
