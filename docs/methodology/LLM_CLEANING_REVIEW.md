# Phương pháp Kiểm tra Làm sạch Thủ công với Hỗ trợ của LLM (`LLM_CLEANING_REVIEW.md`)

## 1. Định nghĩa bài toán
Sau khi chạy rule-based cleaning (`clean_han`, `clean_viet`), vẫn có thể sót lỗi OCR dấu thanh, chữ Hán tự dạng gần giống, lỗi bảng mã font cổ (`ƣ`/`Ƣ`), câu bị ngắt do chuyển trang hoặc chú thích ngoài chính văn. Giai đoạn này sử dụng **Prompt thủ công** (hoặc Coding Agent) giúp phát hiện lỗi trước khi thành viên duyệt CSV, mà **không cần xây dựng LLM API client hay tự động sửa file**.

## 2. Đầu vào và Đầu ra
- **Đầu vào**: Mã tác phẩm, phiên bản (`han`, `dich_am`, `dich_nghia`, `dich_tho`), thể loại, văn bản thô trước làm sạch (`raw`), văn bản sau rule-based cleaning (`clean`), danh sách cờ `reasons`, kết quả đối chứng OCR và ảnh nguồn (nếu có).
- **Đầu ra**: Bảng đề xuất hiệu chỉnh gồm 6 cột (`ID hoặc dòng | Văn bản hiện tại | Đề xuất sửa | Loại lỗi | Bằng chứng và lý do | Cần đối chiếu nguồn`), thống kê số liệu kiểm tra, và quyết định do thành viên cập nhật vào cột `action`, `replacement`, `note` của `duyet_lam_sach.csv`.

## 3. Đặc điểm dữ liệu
- Hán văn cổ đòi hỏi bảo toàn phồn thể, dị thể tự, `[MASK]` và không tự chấm câu hay hiện đại hóa.
- Bản Việt phân biệt chặt 3 chế độ: `dich_am` (giữ nguyên âm tiết Hán–Việt cổ, không chuyển sang thuần Việt), `dich_nghia` (không viết lại cho mượt), `dich_tho` (giữ nguyên dòng thơ và vần điệu).

## 4. Phương pháp luận
Luồng xử lý hoàn toàn có sự kiểm soát của con người:
`Văn bản sau OCR/PDF Text -> Rule-based Cleaning -> Chuẩn bị dữ liệu + Sao chép Prompt (Hán hoặc Việt) -> ChatGPT / Gemini / Claude / Coding Agent -> Bảng đề xuất -> Thành viên đối chiếu ảnh nguồn -> Cập nhật duyet_lam_sach.csv -> Xuất TXT sạch`.

## 5. Quy trình & Ràng buộc
1. Không xây dựng LLM API client tự động cho Text Cleaning, không yêu cầu API key và không gọi LLM trong notebook.
2. Chia nhỏ dữ liệu theo từng bài/đoạn để LLM có thể đối chiếu sát ngữ cảnh `raw` và `clean`.
3. Tách riêng hai prompt cho Hán ([han_cleaning.md](../../prompts/cleaning/han_cleaning.md)) và Việt ([viet_cleaning.md](../../prompts/cleaning/viet_cleaning.md)), nhúng trực tiếp trong [src/hanviet/cleaning/README.md](../../src/hanviet/cleaning/README.md).
4. Thành viên đối chiếu ảnh gốc tại `source_image` / `pdf_page` trước khi cập nhật `duyet_lam_sach.csv` theo đúng 4 `action` được hỗ trợ (`keep`, `replace`, `delete`, `join_next`).

## 6. Triển khai mã nguồn & Tài liệu
- Hướng dẫn 16 mục & prompt copy trực tiếp: `src/hanviet/cleaning/README.md` và `notebooks/README.md`.
- File prompt chuẩn: `prompts/cleaning/{han_cleaning,viet_cleaning}.md`.
- Notebook hướng dẫn: `notebooks/clean_text.ipynb` và `notebooks/03_text_cleaning.ipynb`.

## 7. Kiểm tra thủ công
Mọi đề xuất của LLM hoặc Coding Agent chỉ mang tính tham khảo. Thành viên tự kiểm chứng từng vị trí, bảo toàn các dòng đã duyệt trước đó và chạy cell xuất khi `unresolved_lines == 0`.

## 8. Chỉ số đánh giá
Theo dõi số dòng kiểm tra, số lỗi phát hiện theo mã lỗi (`OCR_CHARACTER_ERROR`, `DIACRITIC_ERROR`, `LEGACY_FONT_ENCODING`, `FOOTNOTE`, `CONTENT_LOSS`, ...), số vị trí `[MASK]` và số đề xuất được chấp nhận/từ chối vào `changes.jsonl`.

## 9. Phân tích lỗi
Kiểm soát chặt các rủi ro thường gặp của LLM: tự điền `[MASK]` theo suy đoán, tự sửa `dich_am` sang thuần Việt, hoặc xóa nhầm niên đại dạng `[1758]`.

## 10. Hạn chế
Chất lượng gợi ý phụ thuộc vào việc người dùng cung cấp đủ ngữ cảnh `raw`/`clean` và ảnh nguồn; khi thiếu ảnh, LLM bắt buộc giữ nguyên nội dung và đánh dấu `NEEDS_MANUAL_REVIEW`.

## 11. Khả năng tái lập thực nghiệm
Hai prompt được phiên bản hóa nguyên văn trong Git cùng schema bất biến của `duyet_lam_sach.csv` và nhật ký kiểm tra `changes.jsonl`.
