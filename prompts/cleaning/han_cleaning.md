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
