# Phân công bước 3: Sao lưu và đặt tên file — nhóm 4 người

Phạm vi: chuẩn bị nguồn, sao lưu, thống nhất tên và ghi rõ quyền sở hữu phần việc. Chưa OCR, làm sạch hoặc dóng hàng. Các mốc trang hai tuyển tập kế thừa bảng kiểm tra nguồn ngày 02/11/2026; hai bản Bắc sứ đã được mở lại để kiểm tra số trang, lớp chữ, bố cục và các mốc mở đầu mục. Đây là kế hoạch phân công, chưa phải các file nguồn đã được sao lưu/tách thực tế.

## 1. Phạm vi chuẩn bị của từng người

Tính trang theo số thứ tự trong trình đọc PDF, bắt đầu từ 1.

| Người | Văn sách thi Đình tập 2 | Thơ văn Lý–Trần tập 3 | Bắc sứ thông lục: bản Việt |
|---|---|---|---|
| TV1 | Bài 8–13, PDF 5–187: 183 trang | Bài 1–130, PDF 13–187: 175 trang | PDF 2–38: 37 trang |
| TV2 | Bài 14–18, PDF 188–365: 178 trang | Bài 131–207, PDF 187–366: 180 trang | PDF 39–75: 37 trang |
| TV3 | Bài 19–22, PDF 366–564: 199 trang | Bài 208–313, PDF 367–525: 159 trang | PDF 76–111: 36 trang |
| TV4 | Bài 23–24, PDF 565–698: 134 trang | Bài 314–415, PDF 526–749: 224 trang | PDF 112–148: 37 trang |

- Mỗi người có 358 trang phạm vi ở hai tuyển tập scan, cộng 36–37 trang mốc bản Việt Bắc sứ. Đây là mức chia gần đều để chuẩn bị nguồn, không chứng minh thời gian OCR hoặc số cặp tương đương.
- Trang PDF 187 của Lý–Trần có cuối bài 130 và đầu bài 131: TV1 nhận bài 130, TV2 nhận bài 131. Ghi quyền sở hữu theo bài, không nhân đôi dữ liệu.
- Hịch tướng sĩ ngắn nên giữ làm mẫu chung. TV1 chuẩn bị phạm vi Hán PDF 11–20, Việt dịch nghĩa PDF 4–6; TV2 kiểm tra đủ trang, TV3 kiểm tra tên/phiên bản, TV4 kiểm tra mở được bản sao và ranh giới phần lấy. Không tính bốn bản kiểm tra thành bốn bộ dữ liệu.
- Bắc sứ bản Hán đã được tìm lại và mở ở `D:\code\CS\NLP\data\bắc sứ thông lục\BắcSứThôngLục_北使通錄(Q1_4).pdf`: 210 trang scan. Không thiếu nguồn Hán. Đã đối chiếu các mốc mở đầu: lời tựa bắt đầu Hán PDF 9 / Việt PDF 2; lời đề từ Hán PDF 11 / Việt PDF 4; quyển một Hán PDF 13 / Việt PDF 7; quyển bốn Hán PDF 93 / Việt PDF 55. Đây là mốc bắt đầu mục, không có nghĩa hai trang tương ứng trọn vẹn hay các trang sau có độ lệch cố định.
- Với riêng bước 3, có thể chia trách nhiệm kiểm kê/đặt tên trang bản Hán: TV1 PDF 1–53, TV2 PDF 54–106, TV3 PDF 107–158, TV4 PDF 159–210 (53/53/52/52 trang). Giữ cả bìa/trang trắng trong bản lưu nguồn và đánh dấu loại trang. Đây chỉ là phân công chuẩn bị nguồn, không ghép các khoảng Hán này với khoảng Việt ở bảng trên. Khi làm corpus phải xác định lại ranh giới nội dung tương ứng.
- Nếu một đoạn Bắc sứ chạy qua ranh giới, người có trang bắt đầu nhận trọn đoạn; ghi câu đầu/cuối khi xác định được.

## 2. Người quản lý bản sao gốc chung

| Người | Bộ nguồn phụ trách lưu bản gốc và kiểm tra bản sao |
|---|---|
| TV1 | Hịch tướng sĩ: 1 PDF |
| TV2 | Thơ văn Lý–Trần tập 3: 1 PDF |
| TV3 | Văn sách thi Đình tập 2: 1 PDF |
| TV4 | Bắc sứ thông lục: cả PDF Hán và PDF Việt |

Đây là trách nhiệm quản lý nguồn chung. Mỗi người vẫn chuẩn bị phần trang/bài của mình ở bảng trên. Bản sao dùng làm việc không thay thế bản dự phòng; nên giữ thêm một bản dự phòng riêng theo phương tiện lưu trữ nhóm đang dùng. Không sửa hoặc ghi đè PDF gốc.

## 3. Quy ước tên đề xuất

Giữ tên gốc trong nơi lưu bản gốc. Bản làm việc dùng tên ngắn, thống nhất:

| Tác phẩm | Mã tên ngắn nội bộ |
|---|---|
| Hịch tướng sĩ | HICH |
| Thơ văn Lý–Trần tập 3 | LYTRAN3 |
| Văn sách thi Đình tập 2 | VANSACH2 |
| Bắc sứ thông lục | BACSU |

Các mã trên chỉ là tên nội bộ đề xuất, không thay thế mã chính thức của cô.

Nếu chọn tạo PDF con để tiện bàn giao, ví dụ:

```text
TV01_VANSACH2_bai0008-0013_pdfp0005-0187_v01.pdf
TV02_LYTRAN3_bai0131-0207_pdfp0187-0366_v01.pdf
TV03_BACSU_viet_pdfp0076-0111_v01.pdf
```

Không bắt buộc phải tạo PDF con. Có thể chỉ giữ PDF gốc kèm bảng phạm vi để tránh sao chép tốn dung lượng. Nếu tạo PDF con, tên vẫn ghi trang PDF gốc dù trình đọc đánh lại số trang của file con.

Nếu đã xuất ảnh trang/vùng, ví dụ:

```text
LYTRAN3_bai0130_han_pdfp0186_r01.png
LYTRAN3_bai0130_viet_pdfp0187_r01.png
VANSACH2_bai0008_pdfp0018.png
```

`r01` là vùng thứ nhất được cắt từ trang. Chỉ gắn `han` hoặc `viet` khi ảnh thực sự chứa đúng vùng đó; ảnh nguyên trang lẫn Hán, phiên âm, dịch nghĩa không được mặc định gắn toàn bộ là Hán. Chưa bắt buộc xuất ảnh toàn bộ ở bước 3. Khi cần thứ tự, dùng số đủ bốn chữ số; phiên bản dùng `v01`, `v02`, tránh `final2`, `final_new`.

## 4. Bàn giao và kiểm tra

Mỗi người bàn giao:

1. Xác nhận bản gốc và bản dự phòng của bộ mình quản lý đều mở được, đúng tổng số trang và có cùng dung lượng; so sánh SHA-256 nếu nhóm có công cụ kiểm tra.
2. Bảng phạm vi phần mình gồm: tác phẩm, tên file gốc, bài/quyển, trang PDF gốc, phía Hán/Việt/chung, người phụ trách, tên file làm việc nếu có, phiên bản và ghi chú.
3. Bản làm việc nếu đã tách; nếu chưa tách, ghi rõ dùng PDF gốc và các khoảng trang nào.
4. Ghi các chỗ chưa xác định được, đặc biệt ánh xạ Hán–Việt của Bắc sứ; không tự điền mốc trang chưa kiểm chứng.

Kiểm tra chéo theo vòng: TV1 kiểm TV2, TV2 kiểm TV3, TV3 kiểm TV4, TV4 kiểm TV1. Chỉ kiểm tra nguồn/bản sao/tên/phạm vi ở bước này. Không đưa mật khẩu, cookie hoặc thông tin tài khoản vào gói bàn giao.

Bước 3 chưa tạo ra cặp dóng hàng, nên chưa dùng để chứng minh đạt chỉ tiêu cặp của toàn đồ án.

## 5. Cập nhật vị trí nguồn Bắc sứ

Hai file hiện được tìm thấy và kiểm tra trực tiếp tại:

- `D:\code\CS\NLP\data\bắc sứ thông lục\BắcSứThôngLục_北使通錄(Q1_4).pdf`
- `D:\code\CS\NLP\data\bắc sứ thông lục\Bắc Sứ Thông Lục.pdf`

Đường dẫn `D:\Download\data_nlp\...` trong bảng cũ không còn là vị trí hiện tại. Đã xem bố cục bằng ảnh thu nhỏ và mở các mốc cụ thể; chưa OCR hoặc xác nhận mọi cặp câu giữa hai bản.
