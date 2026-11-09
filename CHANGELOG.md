# Nhật ký thay đổi

Mỗi bản phát hành cần một mục `## [X.Y.Z]` ở đây — nội dung mục này hiện trong hộp thoại "Có phiên bản mới" của app.
Viết bằng lời thường cho người dùng, mỗi dòng một thay đổi.

## [0.1.0] - 2026-11-03

- Bản đầu tiên: phân tích Google Form công khai (nhiều trang, rẽ nhánh, câu lưới, Mục khác).
- Đặt tỷ lệ đáp án, nhóm tương quan SPSS có kiểm tra thử Cronbach's Alpha, sinh câu tự luận bằng Gemini, nhập dữ liệu từ Excel/CSV.
- Gửi theo lịch "Rải đều tự nhiên" hoặc "Tốc độ tối đa", tạm dừng / tiếp tục, tự giãn nhịp khi Google giới hạn.
- Theo dõi chiến dịch trực tiếp và xuất dữ liệu ra Excel cho SPSS.
- Chế độ tập dùng với form mẫu và tour hướng dẫn cho người mới.
- Bước Soát logic bắt buộc trước khi chạy: AI đọc toàn bộ câu hỏi để câu trả lời của mỗi người khớp nhau (các câu đánh giá "sàn sàn" nhau, tuổi – nghề nghiệp hợp lý, ô "Không có…" không chọn kèm ô khác…), soát thử 200 phản hồi trong máy trước khi gửi.
- App có sẵn key Gemini chung; hết lượt thì app hỏi bạn dán API key riêng rồi chạy tiếp.
- Thông báo khi chiến dịch kết thúc (trong app và thông báo Windows): gửi thành công bao nhiêu, lỗi bao nhiêu, lý do và cách xử lý; nút "Gửi lại phản hồi lỗi" gửi lại đúng các phản hồi đó.
- Hỗ trợ câu hỏi "Đánh giá" (sao); form có câu app chưa điền được thì báo ngay thay vì gửi rồi lỗi.
