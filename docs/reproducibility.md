# Hướng dẫn Cài đặt Đa nền tảng & Tái lập Thực nghiệm

## 1. Cơ chế Phân giải Đường dẫn
`hanviet.common.paths.resolve_paths()` tìm đường dẫn theo thứ tự ưu tiên:
1. Tham số truyền trực tiếp (`user_root=...`).
2. Biến môi trường (`HANVIET_PROJECT_ROOT`, `HANVIET_DATA_ROOT`, `HANVIET_OUTPUT_ROOT`, `HANVIET_CACHE_DIR`, `HANVIET_ENV`, `HANVIET_DEVICE`).
3. File cấu hình `configs/project.yaml`.
4. Tự động tìm thư mục chứa `ten_file.py` hoặc `pyproject.toml`.

## 2. Cài đặt Trên Máy Cá nhân (Windows & Linux)
```bash
python -m venv .venv
# Windows: .venv\Scripts\python.exe  |  Linux: .venv/bin/python
python -m pip install -r requirements/base.txt
python -m pip install -e . --no-deps   # cần setuptools; hoặc đặt PYTHONPATH=src
```

### Cài đặt Tesseract Binary và Gói Ngôn ngữ Tiếng Việt (`vie`)
- **Ubuntu / Debian / Colab / Kaggle Linux**:
  ```bash
  sudo apt-get update && sudo apt-get install -y tesseract-ocr tesseract-ocr-vie
  tesseract --list-langs   # kiểm tra có chữ 'vie'
  ```
- **Windows**:
  1. Cài đặt Tesseract OCR (ví dụ bộ cài UB-Mannheim).
  2. Trong lúc cài đặt, tích chọn **Additional language data -> Vietnamese (`vie`)** hoặc chép file `vie.traineddata` vào thư mục `tessdata/`.
  3. Thêm thư mục Tesseract vào `PATH` hoặc khai báo `TESSERACT_CMD` và `TESSDATA_PREFIX` trong file `.env`.

## 3. Chạy Notebook trên Local, Google Colab và Kaggle
- **Local**: Chọn kernel `.venv`. Các notebook làm sạch, tách câu, dóng hàng, đánh giá không cần cài thư viện GPU hay PyTorch.
- **Google Colab**: Upload/clone repo, mount Drive, cài `requirements/ocr.txt` khi chạy OCR trên GPU, chỉnh `HANVIET_OUTPUT_ROOT` nếu xuất trực tiếp vào Drive.
- **Kaggle**: Bật GPU & Internet (khi tải model lần đầu), cấu hình Secrets (`GOOGLE_DRIVE_CREDENTIALS`, `CLC_OCR_API_KEY`), cài thư viện OCR cẩn thận tránh ghi đè Torch/CUDA của hệ thống (`notebooks/README.md`).

## 4. Thông tin Xác thực (Credentials)
Sao chép `.env.example` thành `.env` để lưu khóa cục bộ (không commit lên Git). Các bước chuẩn bị nguồn, làm sạch và kiểm thử hồi quy chạy bình thường khi không có API key.
