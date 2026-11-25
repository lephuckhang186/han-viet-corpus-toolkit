# Giao thức Đánh giá (Evaluation Protocol)

## 1. Nguyên tắc Trung thực Số liệu
1. **Hai Engine Bất đồng != Đã Xác nhận Lỗi; Hai Engine Trùng khớp != Đúng Tuyệt đối**: Kết quả trùng nhau được gắn nhãn `AGREED_UNVERIFIED`, vì cả hai mô hình vẫn có thể cùng đọc sai chữ Nôm hiếm hoặc bản in mờ.
2. **Kết quả LLM != Dữ liệu Chuẩn (Ground Truth)**: Các nhãn lỗi và đề xuất sửa từ LLM chỉ là dự đoán hỗ trợ, bắt buộc qua kiểm tra code và xác nhận của con người.
3. **Chỉ tính CER / WER / Precision / Recall / F1 khi có tập Gold Reference**: Các hàm trong `src/hanviet/evaluation/metrics.py` chỉ trả về số liệu khi có tập chuẩn do con người xác nhận; nếu không có, giá trị trả về là `None`.

## 2. Phân tách Rõ các Nhóm Thống kê
Mọi báo cáo đều tách bạch:
- `model_agreed_unverified`, `model_disagreements`, `incomplete_cross_check_regions`
- `human_confirmed_errors`, `human_manually_fixed`, `human_deferred`
- `llm_predicted_proposals`, `human_approved`, `human_edited`, `human_rejected`
- Số cặp hợp lệ và số đơn vị chưa dóng `before_llm` so với `after_llm_candidate`

## 3. Phạm vi Kiểm thử Đã Chạy
- Bộ test hồi quy, Dual-OCR cross-check, manual review, LLM alignment repair guard, portability và stage outputs đã được chạy thực tế trên `.venv` (Windows) bằng baseline fixtures và mock/cached responses.
- Thực nghiệm OCR GPU (PaddleOCR/VietOCR), Tesseract thực tế và gọi API ngoài chỉ được xác nhận khi chạy trên môi trường có đủ phần cứng/binary/token tương ứng.
