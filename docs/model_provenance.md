# Nguồn gốc Mô hình, API và Tài nguyên

## 1. Mô hình và API OCR
- **OCR Hán chính (`PaddleOCR`)**: `PP-OCRv6_medium_det` + `PP-OCRv6_medium_rec` (`engine="transformers"` trên PyTorch; batch size 1 cho hàng ngang Lý–Trần; phiên bản tham chiếu từ notebook: `paddleocr==3.7.0`, `paddlex[ocr-core]==3.7.2`, `transformers==5.23.0`).
- **OCR Hán đối chứng (`CLC OCR`)**: Kim Hán Nôm Web API (`https://kimhannom.fit.hcmus.edu.vn/api/web/clc-sinonom/image-upload` và `image-ocr`), đối chiếu trực tiếp từ `TaiLieuAPI_HanNom_CLC.pdf` (trang 1–6). Sử dụng biến môi trường/secret `CLC_OCR_API_KEY`.
- **OCR Việt chính (`Tesseract OCR`)**: Binary `tesseract` hệ thống với gói ngôn ngữ `vie` (`--oem 3 --psm 6 tsv`).
- **OCR Việt đối chứng (`VietOCR`)**: `vietocr==0.3.13` (`vgg_transformer` mặc định hoặc `vgg_seq2seq`), file cấu hình ghim ở commit `fe8c3a7fc714aec57ab81cec844eb3adf0c1636c`, nhận ảnh dòng cắt bằng `line_crop()` từ `TextDetection` (`PP-OCRv6_medium_det`).

## 2. Thuật toán Tách câu & Dóng hàng
- **Hán – Dịch âm (Phiên âm)**:
  - Ghép khoảng theo độ dài bằng Quy hoạch động (`hanviet.alignment.validation.phonetic_links`).
  - Code Lab đối chiếu Levenshtein SN-QN ghim tại commit `57d4ff99d410ece36914f4d046450ba3be36232a` với mã kiểm tra SHA-256 `43dad2b97b4b75c3caed3ae9d367e3b6b20114734d3a45ff3b6f462253e97c3d`.
  - Hai từ điển tại `dict/`: `QuocNgu_SinoNom_TongHop3.csv` (99.860 dòng), `SinoNom_Similar_Dic_v2.csv` (26.045 dòng).
- **Hán – Dịch nghĩa**:
  - Mặc định: Kim Hán Nôm CLC `sentence-alignment` endpoint (tách biệt hoàn toàn với endpoint `image-ocr`).
  - Tùy chọn tắt mặc định: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (rev `e8f8c211226b894fcb81acc59f3b34ba3efd5f42`, ONNX `model_quint8_avx2.onnx`) cho Bertalign / Vecalign.

## 3. Lớp LLM
- **Giai đoạn 03 (Text Cleaning)**: Không dùng LLM API client; thành viên dùng Prompt chuẩn (`src/hanviet/cleaning/README.md`) thủ công với ChatGPT, Gemini, Claude hoặc Coding Agent.
- **Giai đoạn 06 (Hậu kiểm Dóng hàng)**: `LLMConfig` độc lập nhà cung cấp (`configs/methods/llm.yaml`), mặc định `null` (`LLM_NOT_RUN`), hỗ trợ OpenAI-compatible, Gemini REST hoặc xuất/nhập gói JSON thủ công.
