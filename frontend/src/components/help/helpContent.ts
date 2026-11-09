/** Nội dung trang Hướng dẫn (artboard 10). Sửa chữ ở đây, không cần đụng component. */

export interface FeatureHelp {
  title: string;
  when: string;
  how: string;
  to: string;
  cta: string;
  keywords: string;
}

export const FEATURES: FeatureHelp[] = [
  { title: 'Phân tích form', when: 'mọi lần bắt đầu với một Google Form mới.', how: 'dán link chia sẻ (nút Gửi → biểu tượng liên kết). Không dùng link /edit.', to: '/forms', cta: 'Phân tích form', keywords: 'link url edit dán' },
  { title: 'Chế độ tập dùng', when: 'bạn mới dùng app và muốn thử mà không gửi gì ra ngoài.', how: 'bấm “Thử với form mẫu” ở Tổng quan. Mọi lần gửi trên form mẫu chỉ là mô phỏng.', to: '/', cta: 'Mở Tổng quan', keywords: 'thử demo mẫu tập' },
  { title: 'Tỷ lệ đáp án', when: 'muốn kiểm soát bao nhiêu % chọn mỗi đáp án.', how: 'kéo thanh trượt, hoặc bấm nhanh Phân phối đều / Hình chuông / Nghiêng về cao.', to: '/forms', cta: 'Mở cấu hình', keywords: 'phần trăm % thanh trượt' },
  { title: 'Rẽ nhánh', when: 'form chuyển trang khác nhau theo câu trả lời.', how: 'app tự nhận. Tỷ lệ ở câu rẽ nhánh quyết định bao nhiêu phản hồi đi vào mỗi nhánh — xem ô “Đường đi dự kiến”.', to: '/forms', cta: 'Xem đường đi', keywords: 'nhánh trang section' },
  { title: 'Nhóm tương quan SPSS', when: 'nhiều câu thang đo cùng đo một yếu tố (VD: các hàng của một câu lưới).', how: 'tab Nhóm tương quan SPSS → Tạo nhóm, chọn câu, đặt điểm trung bình và mức tương quan, bấm Kiểm tra thử Alpha.', to: '/forms', cta: 'Tạo nhóm', keywords: 'alpha cronbach likert spss tương quan' },
  { title: 'Câu tự luận & Gemini', when: 'form có câu hỏi viết tự do bắt buộc.', how: 'nhập ngữ cảnh, bấm Sinh 50 câu bằng Gemini (app có sẵn key chung; hết lượt thì dán key riêng trong Cài đặt), hoặc tự dán danh sách câu trả lời. Khi gửi, mỗi người điền có kiểu gõ riêng (viết tắt, không dấu, không chấm câu…) để giống người thật.', to: '/settings', cta: 'Nhập Gemini key', keywords: 'ai gemini tự luận key' },
  { title: 'Nhập từ Excel / CSV', when: 'bạn đã có bảng dữ liệu, mỗi dòng là một người trả lời.', how: 'tab Nhập từ Excel / CSV → kéo thả file, kiểm tra cột được ghép với câu nào, sửa chỗ màu cam, rồi bấm Dùng các dòng này.', to: '/forms', cta: 'Nhập file', keywords: 'excel csv file bảng' },
  { title: 'Soát logic', when: 'trước MỌI lần chạy dữ liệu tự sinh — app bắt buộc bước này để câu trả lời của một người khớp nhau.', how: 'bấm “Tiếp: Soát logic”. AI đọc toàn bộ câu hỏi; xem nhóm câu cùng thái độ, ràng buộc NẾU…THÌ, ô “Không có…”; sửa nếu cần, chỉnh độ đồng đều, rồi bấm Xác nhận & chạy. Hết lượt AI thì dán API key riêng.', to: '/forms', cta: 'Mở cấu hình', keywords: 'logic mâu thuẫn khớp nhất quán soát ai thái độ ràng buộc' },
  { title: 'Cách gửi', when: 'trước khi chạy (bước Cấu hình).', how: '“Rải đều tự nhiên” giãn cách trong số phút bạn chọn; “Tốc độ tối đa” gửi nhanh nhất. Luôn gửi thử 1 phản hồi trước.', to: '/forms', cta: 'Thiết lập chạy', keywords: 'tốc độ rải đều lịch' },
  { title: 'Thông báo kết thúc & Gửi lại phản hồi lỗi', when: 'chiến dịch chạy xong, gửi không thành công, hoặc app tự tạm dừng.', how: 'ở bất kỳ màn hình nào app cũng hiện hộp thoại (và thông báo Windows nếu bạn đang làm việc khác): số thành công / lỗi, lý do lỗi và cách xử lý. Bấm “Gửi lại X phản hồi lỗi” để gửi lại đúng các phản hồi đó, nội dung giữ nguyên.', to: '/campaigns', cta: 'Mở chiến dịch', keywords: 'thông báo hoàn tất lỗi gửi lại thất bại lý do' },
  { title: 'Theo dõi, tạm dừng, xuất dữ liệu', when: 'chiến dịch đang chạy hoặc đã xong.', how: 'mở Chiến dịch để xem tiến độ trực tiếp, bấm Tạm dừng / Tiếp tục, và Xuất dữ liệu ra Excel cho SPSS.', to: '/campaigns', cta: 'Mở chiến dịch', keywords: 'tạm dừng xuất export spss tiến độ' },
];

export const TERMS: { term: string; text: string }[] = [
  { term: 'Cronbach’s Alpha (α)', text: 'Độ nhất quán của một nhóm câu thang đo, từ 0 đến 1. Từ 0,7 trở lên thường được coi là đạt; trên 0,9 là rất cao.' },
  { term: 'Thang đo Likert', text: 'Câu chọn mức độ, VD 1 = Rất không đồng ý … 5 = Rất đồng ý.' },
  { term: 'Tương quan (r)', text: 'Mức các câu trong nhóm “đi cùng nhau”: người chọn cao ở câu này cũng có xu hướng chọn cao ở câu kia.' },
  { term: 'Mục khác', text: 'Ô “Khác” cho người trả lời tự gõ; cần có danh sách câu trả lời mẫu nếu đặt tỷ lệ lớn hơn 0%.' },
  { term: 'Trình duyệt dự phòng', text: 'Khi form từ chối dữ liệu gửi trực tiếp, app mở một trình duyệt ẩn để điền và bấm Gửi giống người dùng. Cần tải một lần trong Cài đặt.' },
];

export const FAQS: { q: string; a: string }[] = [
  { q: 'Vì sao link của tôi bị báo “link chỉnh sửa”?', a: 'Link có /edit chỉ dành cho người tạo form. Hãy mở form, bấm Gửi → biểu tượng liên kết → Sao chép, rồi dán link đó.' },
  { q: 'Vì sao chiến dịch tự tạm dừng?', a: 'Google đang giới hạn số lần gửi. App đã tự gửi chậm lại; nếu vẫn bị giới hạn 3 lần liên tiếp thì dừng để bạn quyết định. Chờ một lúc rồi bấm Tiếp tục.' },
  { q: 'Nút Bắt đầu chạy bị mờ?', a: 'Còn câu chưa cấu hình xong (thường là câu tự luận bắt buộc chưa có câu trả lời mẫu). Ô “Kiểm tra trước khi chạy” bên phải liệt kê từng việc còn thiếu.' },
  { q: 'Tắt app giữa chừng có mất dữ liệu không?', a: 'Không. Các phản hồi đã gửi được lưu lại; mở app và bấm Tiếp tục, app sẽ gửi tiếp phần còn lại.' },
  { q: 'File Excel đã chọn biến mất sau khi mở lại app?', a: 'Đúng vậy: file lớn không được lưu vào bản nháp. Hãy chọn lại file ở tab Nhập từ Excel / CSV.' },
];
