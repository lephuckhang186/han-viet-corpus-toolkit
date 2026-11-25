# Kiến trúc Hệ thống — Framework Nghiên cứu Mô-đun theo Từng Giai đoạn

## 1. Mô hình thiết kế
`han-viet-corpus-toolkit` áp dụng mô hình **Stage-based Modular Research Framework with Human-in-the-loop Validation**:
- **Không xây dựng End-to-End Orchestrator**: Tuyệt đối không tạo workflow engine, Airflow/Prefect hay một script chạy thẳng từ PDF gốc đến tệp xuất cuối cùng.
- **Độc lập từng Giai đoạn (Stage Isolation)**: Mỗi giai đoạn nạp dữ liệu đã được xác nhận, chạy độc lập, xuất manifest chuẩn (`schemas/stage_manifest.schema.json`) và dừng chờ thành viên kiểm tra trước khi bước sang giai đoạn tiếp theo.
- **Bảo toàn Logic Gốc (Protected Logic Preservation)**: Các thuật toán chuẩn bị nguồn (`src/hanviet/source_preparation/`), làm sạch theo luật (`src/hanviet/cleaning/{han,viet}_cleaner.py`), tách câu (`src/hanviet/segmentation/`) và dóng hàng/xuất bảng (`src/hanviet/alignment/`, `src/hanviet/exporters/`) được bảo toàn nguyên vẹn hành vi và kiểm chứng bằng bộ kiểm thử hồi quy.

## 2. Cấu trúc gói mã nguồn (`src/hanviet/`)
- `hanviet.common`: Phân giải đường dẫn đa nền tảng (`paths.py`), nạp YAML & kiểm tra phụ thuộc (`config.py`), I/O nguyên tử (`io.py`), manifest giai đoạn (`manifests.py`), shared LLM client cho hậu kiểm dóng hàng (`llm_client.py`).
- `hanviet.source_preparation`: Cắt PDF/TXT, sao lưu SHA-256, lịch sử hoàn tác (`history.py`), giao diện Tkinter (`ui.py`, `text_ui.py`), CLI (`cli.py`).
- `hanviet.extraction`: Dual-OCR engines (`paddle_han.py`, `clc_han.py`, `tesseract_viet.py`, `vietocr_viet.py`), tiền xử lý (`han_preprocess.py`, `viet_preprocess.py`), đối chứng (`aligner.py`), hiệu đính thủ công (`reviewer.py`), trích xuất lớp chữ có sẵn (`extractor.py`).
- `hanviet.cleaning`: Thuật toán làm sạch theo luật Hán/Việt (`han_cleaner.py`, `viet_cleaner.py`, `pipeline.py`) và tài liệu hướng dẫn kiểm tra thủ công cùng LLM Prompt (`README.md`). Lưu ý: Không xây dựng LLM API client cho Text Cleaning.
- `hanviet.segmentation`: Thuật toán tách câu và dòng thơ được bảo toàn (`segmenter.py`).
- `hanviet.alignment`: Các backend Lab/CLC/embedding tùy chọn (`backends/`), kiểm tra & DP (`validation/`), bộ điều phối bài (`runner.py`, `bac_su.py`, `thi_dinh.py`), hậu kiểm và sửa lỗi dóng hàng với LLM (`llm_review/`).
- `hanviet.evaluation`: Chỉ số đánh giá trung thực (`metrics.py`) và xuất báo cáo JSON/Markdown (`reports.py`).
- `hanviet.exporters`: Xuất bảng song ngữ 4 cột TSV/XLSX và `notes.xlsx` (`tabular.py`).

## 3. Tương thích ngược
Các điểm chạy và module cũ (`ten_file.py`, `cat_*.py`, `cong_cu/*.py`) được giữ lại dưới dạng wrapper/re-export mỏng trỏ sang `src/hanviet/`, bảo toàn hoàn toàn công việc đang thực hiện và đường dẫn đầu ra cũ.
