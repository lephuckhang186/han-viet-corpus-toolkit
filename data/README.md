# PDF nguồn lưu tại máy

Các PDF không được đưa lên GitHub. Đặt file bạn đã được cung cấp theo bố cục:

```text
data/
├── HichTuongSi_TranQuocTuan.pdf
├── Nguyễn Huệ Chi (chủ biên) - Thơ văn Lý Trần 3.pdf
├── Van_sach_thi_Dinh_Thang_Long_Ha_Noi_T2.pdf
└── bắc sứ thông lục/
    ├── Bắc Sứ Thông Lục.pdf
    └── BắcSứThôngLục_北使通錄(Q1_4).pdf
```

Nếu tên/vị trí file khác, sửa `TEN_NGUON` trong `ten_file.py`. Tool giữ nguyên
PDF nguồn và chỉ tạo sản phẩm trong `san_pham/`. Tests tích hợp cần PDF nguồn;
không có file thì tests liên quan sẽ được bỏ qua với lý do cụ thể.
