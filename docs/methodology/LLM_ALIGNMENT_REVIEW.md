# Phương pháp Hậu kiểm và Đề xuất Sửa Dóng hàng bằng LLM (`LLM_ALIGNMENT_REVIEW.md`)

## 1. Định nghĩa bài toán
Thực hiện hậu kiểm toàn bộ kết quả dóng hàng nháp (`draft.json` do Lab, CLC hoặc bước ghép thơ tạo ra) để phát hiện thiếu ý (`OMISSION`), thừa ý (`ADDITION`), thiếu ghép (`MISSING`), sai ranh giới câu, lệch tên riêng/chức danh/niên hiệu hoặc lỗi từ OCR/cleaning, trước khi người dùng chốt `review.json`.

## 2. Đầu vào và Đầu ra
- **Đầu vào**: `draft.json` (`work`, `fingerprint`, `units`, `links`, `unmatched`, `lab_diagnostics`) và `review.json` hiện có (nếu có).
- **Đầu ra**: Hồ sơ kiểm chứng tách biệt trong `06_llm_hau_kiem/{before,requests,responses,patches,manual_review,after}/` và bản nháp ứng viên `review_candidate.json` (luôn giữ `approved: false`).

## 3. Đặc điểm dữ liệu
Kiểm tra đồng thời 4 phiên bản với tiêu chí khác nhau: `Hán – Dịch âm` đánh giá quan hệ phiên âm Hán–Việt; `Hán – Dịch nghĩa` đánh giá tương đương nghĩa; `Hán – Dịch thơ` chấp nhận diễn đạt linh hoạt nhưng vẫn giữ đủ ý nguồn.

## 4. Phương pháp luận
`TXT sạch đã duyệt -> Thuật toán tách câu & dóng hàng hiện tại -> draft.json -> LLM Hậu kiểm -> Đề xuất sửa JSON -> Kiểm tra Patch bằng Code -> Thành viên duyệt -> review.json`. Không thay thế Lab hoặc CLC bằng LLM.

## 5. Thuật toán
1. LLM sinh danh sách `findings` (nhãn chính thức `OMISSION`/`ADDITION`/`MISSING` + nhãn chẩn đoán) và `proposals` (`KEEP`, `MERGE`, `SPLIT`, `RELINK`, `ADD_LINK`, `REMOVE_LINK`, `FLAG_OCR`, `FLAG_CLEANING`, `REQUEST_REVIEW`).
2. `validate_alignment_proposals()` kiểm tra `verify_identity`, xác minh mọi `segment_id` đều tồn tại, cùng tác phẩm, liền kề đúng thứ tự qua `validate_links()`, chặn mọi đề xuất tự bịa bản dịch hay tự đặt `approved: true`, và từ chối chỉnh sửa nếu `review.json` đã có `approved: true`.
3. `apply_approved_alignment_repairs()` chỉ áp dụng các patch có `APPROVE` từ con người và lưu kết quả ứng viên chưa phê duyệt.

## 6. Triển khai mã nguồn
- `src/hanviet/alignment/llm_review/{verifier,patch_validator,applier}.py`
- `prompts/alignment/{poetry_alignment,alignment_verification,alignment_repair}.md`
- `schemas/alignment_repair.schema.json`
- CLI: `scripts/run_llm_alignment_review.py` và notebook `notebooks/06_llm_alignment_review.ipynb`.

## 7. Kiểm tra thủ công
Thành viên xem từng đề xuất để chọn `APPROVE`, `REJECT` hoặc `DEFER`. Nếu LLM gắn `FLAG_OCR` / `FLAG_CLEANING`, người dùng chủ động quay lại giai đoạn trước, không tự động chạy lại dây chuyền.

## 8. Chỉ số đánh giá
Báo cáo `summarize_alignment_review()` so sánh số hàng hợp lệ và số đơn vị chưa dóng trước/sau kiểm tra, số lỗi dự đoán và tỷ lệ approve/reject của con người.

## 9. Phân tích lỗi
Phân biệt rõ phiên bản không tồn tại trong sách gốc với phiên bản có tồn tại nhưng bị thuật toán dóng sót.

## 10. Hạn chế
Mặc định ở trạng thái `LLM_NOT_RUN` khi chưa cấu hình provider/credential; không tự sửa text nguồn để ép hai vế khớp nhau.

## 11. Khả năng tái lập thực nghiệm
Lưu hash request/response, snapshot `before/` và `after/`, cùng schema JSON kiểm tra tự động.
