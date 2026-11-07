# Tool chuẩn bị ngữ liệu Hán–Việt — thành viên 2

Tool phục vụ **bước 3: sao lưu, đặt tên và cắt nguồn theo từng tác phẩm/bản văn**.
Đọc `CONTEXT.md` để xem các quy tắc cô đã dặn. Tool giữ đủ các bản có trong sách:
**Hán – dịch âm – dịch nghĩa – dịch thơ**. Chưa OCR, sửa chữ hoặc dóng hàng tự động.

## Chạy ngay

Mở PowerShell tại thư mục repo (máy hiện tại là `D:\code\CS\NLP`), chạy một trong bốn file:

```powershell
.\.venv\Scripts\python.exe .\cat_ly_tran.py
.\.venv\Scripts\python.exe .\cat_van_sach.py
.\.venv\Scripts\python.exe .\cat_bac_su.py
.\.venv\Scripts\python.exe .\cat_hich_tuong_si.py
```

Môi trường `.venv` đã được tạo; tool dùng hai thư viện trong `requirements.txt`.
Nếu cài trên máy khác, dùng Python 3.11 trở lên có Tkinter:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Repo GitHub chỉ chứa mã nguồn, hướng dẫn và tests. PDF nguồn, `Guideline.pdf`,
sản phẩm cắt, lịch sử thao tác và `.venv` được giữ ở máy, không đưa vào Git.
Sau khi clone, đặt các PDF vào `data/` theo [hướng dẫn dữ liệu](DATA_SETUP.md)
hoặc sửa `TEN_NGUON` trong `ten_file.py`. Các tests tích hợp cần những PDF này;
thiếu dữ liệu sẽ được ghi nhận là bỏ qua, không được tính là đã kiểm tra thành công.

**`MA_DE_TAI` trong `ten_file.py` phải khớp mã đăng ký của nhóm.** Giữ cấu hình
bạn đã đặt; chỉ đổi khi cần sửa mã đăng ký. Đổi mã sẽ
đổi thư mục đầu ra của các lần chạy sau; tool không tự di chuyển sản phẩm cũ.

## Cắt bằng chuột

1. Mở đúng script của sách. Tool kiểm tra bản sao gốc rồi hiển thị PDF.
2. Nhập **mã tác phẩm**, ví dụ `bai0131`. Đây là mã bài, không phải trang PDF.
3. Chọn **Hán / Dịch âm / Dịch nghĩa / Dịch thơ**.
4. Kéo chuột khoanh đúng vùng của bản văn đó, bấm **Lưu vùng vào tác phẩm** hoặc Ctrl+S.
5. Nếu bản văn còn tiếp ở trang sau, mở trang tiếp theo, **giữ nguyên mã tác phẩm,
   loại bản và phiên bản**, rồi chọn/lưu tiếp. Tool lưu các PNG vào cùng thư mục tác phẩm/bản văn.
6. Làm tương tự cho các bản còn lại. Nút **Xem đủ/thiếu bản văn** giúp kiểm tra phần đã cắt.

Thứ tự bạn bấm lưu là thứ tự các phần trong mỗi bản văn. Không suy ra thứ tự chỉ từ
số trang: đôi khi phải quay lại phần trước. Lưu lại đúng vùng với cùng cấu hình
thì tool bỏ qua bản trùng. Vùng gần trùng sẽ có cảnh báo trước khi lưu thêm.

## Xem, sửa và hoàn tác

- Danh sách bên phải hiển thị các vùng của bài/phiên bản đang chọn. Bấm một dòng để
  xem ảnh hoặc đoạn TXT. Khung xanh trên trang là vùng đã lưu; khung xám là vùng
  của bài khác trên cùng trang.
- **Chỉnh vùng đã chọn**: mở lại đúng trang và khung cũ. Khoanh lại rồi bấm
  **Lưu thay khung vùng đã chọn**. Giữ nguyên mã bài, bản văn, phiên bản và số phần.
  Có thể đổi trang để sửa phần đã lấy nhầm trang. Với vùng TXT, chọn lại đoạn chữ.
- **Bỏ vùng đã chọn**: bỏ vùng khỏi sản phẩm đang dùng; TXT ghép được cập nhật
  theo các phần còn lại. Các phần khác giữ số thứ tự cũ để không mất mã tham chiếu.
- **Hoàn tác thao tác gần nhất**: khôi phục trạng thái trước lần lưu, thay, bỏ vùng
  hoặc xác nhận tiến độ. Có thể hoàn tác nhiều lần, kể cả sau khi mở lại tool.
- Dữ liệu vùng lưu từ bản tool cũ vẫn xem/sửa/bỏ được. Hoàn tác chỉ áp dụng cho
  các thao tác được thực hiện từ bản nâng cấp có lịch sử.
- Chỉnh vùng giữ nguyên loại bản văn. Nếu lưu sai loại Hán/dịch nghĩa, bỏ vùng cũ
  rồi chọn đúng loại và lưu lại; có thể hoàn tác thao tác bỏ nếu cần.

Các bản trước/sau được lưu trong `05_quan_ly/lich_su/`. Không xóa thư mục này nếu
còn cần hoàn tác. Lịch sử sử dụng thêm dung lượng theo số thao tác; metadata được
nén để giảm dung lượng. File đã sửa bên ngoài tool sẽ được giữ và báo xung đột.
Nếu lần ghi bị ngắt, lần mở tiếp theo phục hồi trạng thái trước thao tác chưa hoàn tất.

## Mặc định nguồn, nhớ vị trí và tiến độ

- Nguồn riêng bản Việt của Bắc sứ mặc định **Dịch nghĩa**; nguồn riêng Hán mặc định
  **Hán**. Với PDF chứa nhiều bản văn, bạn vẫn chọn đúng loại vùng cần lấy.
  Nếu chọn loại khác ngôn ngữ của nguồn riêng, tool cảnh báo trước khi lưu.
- Tool nhớ trang gần nhất của từng nguồn, bài, loại bản văn, phiên bản và mức phóng
  trong `05_quan_ly/phien_lam_viec.json`; mở lại để tiếp tục từ phiên đã lưu.
- **Tiến độ bốn bản văn** hiển thị Hán, dịch âm, dịch nghĩa, dịch thơ theo từng bài.
  Chỉ bấm **Đã kiểm tra đủ / bỏ xác nhận** sau khi bạn đã đối chiếu trọn bản văn.
  Thêm, sửa hoặc bỏ vùng sẽ đưa bản văn đó về trạng thái đang làm.
- Trạng thái đủ vùng do bạn xác nhận, không chứng minh câu đã dóng hàng đúng hoặc
  đã đạt chỉ tiêu cặp. Ghi nhận không có bản văn chỉ dùng khi nguồn thực sự không có.

Nguồn và bản sao được kiểm tra hash khi mở/chuẩn bị. Các lần lưu tiếp trong cùng
phiên tái sử dụng kết quả khi đường dẫn, dung lượng và thời gian file không đổi.
Nếu thông tin file thay đổi, tool kiểm tra lại; `--check` luôn đọc và kiểm tra đầy đủ.

Nếu sách thực sự không có một bản dịch, ghi lý do ở ô ghi chú rồi bấm **Ghi nhận
không có bản này**. Không dùng chức năng này để bỏ qua phần chưa đọc. Tool không
tạo bản dịch hoặc file TXT rỗng thay phần thiếu.

**Chú thích:** ở bước 3 ảnh còn giữ nguyên các chỉ dấu trong thân bài. Khoanh phần
nội dung chính, để khối khảo đính/chú thích riêng ngoài vùng. Việc loại chú thích
không thuộc nội dung Hán và làm sạch ký tự là bước 5, không phải sửa ảnh nguồn.

## Phần việc của TV2

| File chạy | Phạm vi mặc định | Điểm cần chú ý |
|---|---|---|
| `cat_ly_tran.py` | Bài 131–207; PDF 187–366 | Trên trang 187, phần trên là cuối bài 130 của TV1; chỉ lấy bài 131 phía dưới. |
| `cat_van_sach.py` | Bài 14–18; PDF 188–365 | Mốc đầu dịch nghĩa/Hán từng bài có trong script; cần tự kiểm tra điểm kết thúc. |
| `cat_bac_su.py` | Việt PDF 39–75; Hán PDF 54–106 để kiểm kê | Hai khoảng không phải bản dịch tương ứng. Dò đúng quyển/đoạn mới dùng chung mã. |
| `cat_hich_tuong_si.py` | Hán/dịch âm 11–20; dịch nghĩa 4–6; diễn thơ 21–26 | Đây là mẫu chung TV2 kiểm tra, không cộng bộ cặp thứ hai. |

Số trang luôn là thứ tự trong **PDF gốc**, tính từ 1. Khi cần trang lân cận để giữ
trọn bài, bật **Cho phép ngữ cảnh/mẫu ngoài phạm vi TV2** và ghi lý do.

## Bố cục đã tạo

```text
data/                                      # PDF đầu vào, giữ nguyên
san_pham/TV02/<MA_DE_TAI>_CPO_12/           # Ví dụ Lý–Trần
├── 01_nguon/
│   ├── chung/ban_goc/                      # Bản sao nguyên PDF hỗn hợp
│   ├── han/
│   │   └── CPO_12_TV02_bai0131_han_v01/
│   │       └── phan0001_pdfp0187.png
│   └── viet/
│       ├── dich_am/                        # Gom riêng theo bài, giống phía Hán
│       ├── dich_nghia/
│       └── dich_tho/
├── 02_ocr_tho/
│   ├── han/                               # Để trống cho bước 4
│   └── viet/
├── 03_text_sach/                           # Chưa có han.txt/viet.txt sạch
├── 04_dong_hang/                           # Chưa tạo TSV/XLSX
└── 05_quan_ly/
    ├── nguon.json                         # Nguồn, bản sao, SHA-256, phạm vi
    ├── vung_cat.json                       # Tác phẩm, bản văn, trang/vùng/thứ tự
    ├── phien_lam_viec.json                 # Trang và các lựa chọn gần nhất
    ├── lich_su/                           # Bản trước/sau để phục hồi, hoàn tác
    └── text_tho/                          # Đoạn text trích xuất, nếu chọn
```

Các thư mục CPO_09 / CPO_10 / CPO_11 có bố cục tương tự. Với Bắc sứ, bản gốc Hán
được sao lưu trong `han/ban_goc/`, bản Việt trong `viet/ban_goc/`.
Ba thư mục con dưới `viet/` và `05_quan_ly/` bổ sung việc quản lý bốn bản văn và
truy vết, giữ nguyên bốn tầng chính cô khuyến nghị.

**Một thư mục ảnh = một tác phẩm + một bản văn + một phiên bản.** Các PNG bên trong
được đánh số theo thứ tự lưu; không được tính mỗi ảnh là một tác phẩm/cặp dóng hàng.

Ví dụ thư mục `CPO_12_TV02_bai0131_han_v01/`: CPO_12 là mã sách, TV02 là thành viên 2,
bai0131 là bài 131, han là bản Hán, v01 là phiên bản đầu. `phan0001_pdfp0187.png`
là phần thứ nhất của bản văn, lấy từ trang gốc 187. Dùng số cố định chiều dài,
không dùng tên final/final2/final_new.

Tool chỉ xuất PNG vùng đã chọn, không tạo PDF sau khi cắt. PDF gốc và bản sao
nguyên vẹn vẫn được giữ để đối chiếu. Muốn lấy chữ từ PDF Text, dùng tùy chọn bên dưới.

## Cắt TXT và PDF Text

- **TXT UTF-8 có sẵn:** bấm **Mở TXT để chọn chữ**, bôi đen đúng phần cần lấy rồi lưu.
  Mã tác phẩm, loại bản và phiên bản lấy từ cửa sổ chính. File nguồn được sao lưu.
- **PDF có lớp chữ:** khoanh vùng như bình thường, bật **Lấy thêm lớp chữ PDF**.
  Tool xuất PNG và TXT thô của vùng. Đây là tùy chọn trích xuất ở bước 4;
  không tự OCR hoặc coi text là đã sạch. PDF Text xoay chưa hỗ trợ trích chữ vùng.
- **PDF scan:** chỉ xuất PNG. Nếu bật lấy chữ nhưng vùng không có text,
  tool báo lỗi và không tạo TXT rỗng. Nếu chữ nguồn bị lỗi font thì TXT vẫn cần sửa.
- **Một phiên bản của một bản văn dùng một chế độ:** ảnh PDF, PDF có trích text,
  hoặc TXT. Muốn đổi chế độ, dùng phiên bản mới để tránh ghép TXT thiếu một nửa.

Lệnh cắt TXT theo dòng (thay đường dẫn bằng TXT thật):

```powershell
.\.venv\Scripts\python.exe .\cat_ly_tran.py --text-file "duong_dan_text.txt" --lines 10 20 --work bai0131 --kind dich_nghia
```

TXT ghép có đuôi `_trich_xuat_tho.txt`, chưa phải `han.txt/viet.txt` sạch. Công cụ
chỉ giữ đoạn được chọn, không dịch, không cắt câu hoặc suy đoán Hán/Việt theo ký tự.

## Kiểm tra / chuẩn bị lại

Các cờ dùng được cho cả bốn script:

```powershell
.\.venv\Scripts\python.exe .\cat_ly_tran.py --prepare
.\.venv\Scripts\python.exe .\cat_ly_tran.py --info
.\.venv\Scripts\python.exe .\cat_ly_tran.py --check
.\.venv\Scripts\python.exe .\cat_ly_tran.py --summary --work bai0131
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

`--check` so SHA-256 nguồn, bản sao và sản phẩm, phát hiện file thiếu/bị sửa. Nó
không kiểm tra nghĩa, thiếu câu hay đủ ranh giới tác phẩm. Hai cửa sổ có thể đọc
cùng sách nhưng không được ghi cùng lúc: khóa ghi giúp tránh mất manifest.

## Mã nguồn nằm ở đâu?

| File | Chức năng |
|---|---|
| `ten_file.py` | Tên nguồn, mã đề tài/sách/thành viên, thư mục và quy ước tên. |
| `cat_ly_tran.py`, `cat_van_sach.py`, `cat_bac_su.py`, `cat_hich_tuong_si.py` | Cấu hình/phạm vi và điểm chạy riêng từng sách. |
| `cong_cu/models.py` | Kiểu dữ liệu, kiểm tra mã bài và vùng cắt. |
| `cong_cu/pdf_ops.py` | Đọc PDF nguồn, render/cắt PNG và lấy lớp chữ theo vùng. |
| `cong_cu/text_ops.py` | Đọc/cắt TXT Unicode theo dòng/ký tự. |
| `cong_cu/storage.py` | Dấu kiểm, sao lưu, ghi file và khóa ghi. |
| `cong_cu/workspace.py` | Bố cục đầu ra, gom vùng theo tác phẩm, manifest, đủ/thiếu bản văn. |
| `cong_cu/region_actions.py` | Liệt kê, thay/bỏ vùng, kiểm tra chồng vùng và xác nhận tiến độ. |
| `cong_cu/history.py` | Lưu thay đổi, hoàn tác và phục hồi lần ghi bị ngắt. |
| `cong_cu/region_panel.py` | Danh sách xem trước và bảng tiến độ bốn bản văn. |
| `cong_cu/cli.py` | Tham số và chạy kế hoạch CSV. |
| `cong_cu/ui.py`, `cong_cu/text_ui.py` | Giao diện PDF và TXT. |

Không gộp toàn bộ xử lý vào file cấu hình hoặc một script lớn. Đã tham khảo cách
giữ nguồn, xuất ảnh và lưu manifest của [pdfslice-py](https://github.com/obj-see/pdfslice-py).
Không sao chép mã nguồn hay cài repo đó; phần cắt tác phẩm/bốn bản văn được viết riêng.

## Các việc chưa thực hiện

Chưa cắt toàn bộ phần TV2, chưa OCR, làm sạch, dóng hàng bốn bản văn hoặc đếm cặp
hợp lệ. Guideline quy định TSV/XLSX hai cột Hán–Việt; yêu cầu giữ bốn phiên bản
của cô được bảo toàn ở nguồn và manifest, không tự thay đổi schema bàn giao.
Ranh giới/ánh xạ Bắc sứ vẫn cần kiểm tra nội dung; không mặc định bản Hán và Việt
khớp theo số trang hoặc khoảng chia kiểm kê.
