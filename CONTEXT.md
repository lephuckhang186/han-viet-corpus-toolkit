- Xác định ranh giới tác phẩm trước: Mỗi bài thơ, bài hịch hoặc đoạn văn được xem là một đơn vị độc lập

-nên tách văn bản theo đơn vị tác phẩm và từng ngôn ngữ, không tách theo trang PDF. Vì một tác phẩm có thể nằm trên nhiều trang, hoặc một trang chứa đồng thời bản Hán và bản Việt.

- Trường hợp có nhiều bản dịch (như dịch âm, dịch nghĩa, dịch thơ): cần thực hiện dóng hàng tất cả phiên bản theo cấu trúc: Hán – Dịch âm – Dịch nghĩa – Dịch thơ

- Trong file hướng dẫn có quy định cụ thể tại bước 5 - Làm sạch text: phần chú thích nếu không thuộc nội dung chính trong bản Hán thì cần loại bỏ

- dẫn dóng hàng Hán - dịch âm cho tác phẩm thơ ca bằng Levenshtein, sử dụng code của Lab. Các bạn lưu ý là file kết quả vẫn theo định dạng đã quy định gồm 4 cột, cấu trúc: Hán – Dịch âm – Dịch nghĩa – Dịch thơ trong "D:\code\CS\NLP\Hướng dẫn dóng hàng - dịch âm.docx"

- Lưu ý với các nhóm khi OCR chữ hán, với những trang/đoạn bị hư hỏng hoặc mờ nặng, không đọc được chữ thì đánh dấu chữ khuyết là [MASK] vào dữ liệu dóng hàng.

Lưu ý các bạn khi dóng hàng các tác phẩm thơ ca có cả dịch âm - dịch nghĩa - dịch thơ:
    + Với dóng hàng Hán - dịch âm: dùng Levenshtein
    + Với dóng hàng Hán - dịch nghĩa: dùng api clc của lab hoặc các model dóng hàng như BERTAlign, VecAlign…
    + Với dóng hàng Hán - dịch thơ: cũng giống dịch nghĩa, nhưng khó hơn, nên dùng AI LLM
