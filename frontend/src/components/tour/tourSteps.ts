/**
 * Danh sách bước của tour lần đầu (artboard 9). Thêm tính năng mới = thêm một bước ở đây và
 * gắn `data-tour="<target>"` vào phần tử tương ứng. Không cần sửa màn hình nào khác.
 */
export type TourScreen = 'dashboard' | 'workspace' | 'logic' | 'campaign';
export type Placement = 'below' | 'above' | 'right' | 'left';

export interface TourStep {
  target: string;
  screen: TourScreen;
  placement: Placement;
  title: string;
  text: string;
}

export const TOUR_STEPS: TourStep[] = [
  { screen: 'dashboard', target: 'nav', placement: 'right', title: 'Thanh điều hướng', text: 'Mọi khu vực của app nằm ở đây: Tổng quan, Cấu hình khảo sát, Chiến dịch và Cài đặt.' },
  { screen: 'dashboard', target: 'quick', placement: 'below', title: 'Bắt đầu: dán link Google Form', text: 'Mở form → nút Gửi → biểu tượng liên kết → Sao chép, dán vào đây rồi bấm Phân tích. Bấm Tiếp để xem màn hình Cấu hình với một form mẫu.' },
  { screen: 'workspace', target: 'steps', placement: 'below', title: 'Bạn đang ở bước 2 / 4', text: 'Thanh này luôn cho biết bạn đang ở đâu: Phân tích → Cấu hình → Soát logic → Chạy & theo dõi. Đây là form mẫu — không gửi gì ra ngoài.' },
  { screen: 'workspace', target: 'rail', placement: 'right', title: 'Các trang của form', text: 'Bấm để nhảy tới từng trang. Dòng màu cam là trang còn câu chưa cấu hình xong.' },
  { screen: 'workspace', target: 'weights', placement: 'right', title: 'Tỷ lệ đáp án', text: 'Kéo thanh trượt để đặt bao nhiêu % người chọn mỗi đáp án, hoặc bấm nhanh Phân phối đều / Hình chuông / Nghiêng về cao.' },
  { screen: 'workspace', target: 'branch', placement: 'right', title: 'Câu rẽ nhánh', text: 'Tỷ lệ ở câu này quyết định bao nhiêu phản hồi đi vào mỗi nhánh. Ô xám bên dưới cho thấy đường đi dự kiến.' },
  { screen: 'workspace', target: 'text', placement: 'above', title: 'Câu tự luận', text: 'Viền cam = câu bắt buộc chưa có câu trả lời mẫu. Bấm “Sinh 50 câu bằng Gemini” hoặc tự dán danh sách câu trả lời.' },
  { screen: 'workspace', target: 'tabs', placement: 'below', title: 'Thêm cách tạo dữ liệu', text: '“Nhóm tương quan SPSS” giúp nhóm câu thang đo đạt Cronbach’s Alpha mong muốn. “Nhập từ Excel / CSV” dùng bảng dữ liệu bạn có sẵn.' },
  { screen: 'workspace', target: 'run', placement: 'left', title: 'Thiết lập chạy', text: 'Nhập số phản hồi và chọn cách gửi. “Rải đều tự nhiên” giãn cách các lần gửi trong số phút bạn chọn.' },
  { screen: 'workspace', target: 'start', placement: 'left', title: 'Gửi thử trước, rồi sang Soát logic', text: 'Luôn gửi thử 1 phản hồi để kiểm tra. Nút “Tiếp: Soát logic” chỉ sáng khi mọi câu đã cấu hình xong — ô bên trên cho biết còn thiếu gì. Bấm Tiếp để xem bước Soát logic.' },
  { screen: 'logic', target: 'logic-groups', placement: 'right', title: 'Soát logic: câu nào phải khớp nhau', text: 'AI đọc toàn bộ câu hỏi và tìm: các câu cùng đo một thái độ (phải cùng cao / cùng thấp), ràng buộc NẾU…THÌ (VD dưới 18 tuổi thì là học sinh) và ô “Không có…” không được chọn kèm. Bấm nhãn “Tốt ở trên / dưới” để đổi chiều nếu AI hiểu nhầm.' },
  { screen: 'logic', target: 'logic-result', placement: 'left', title: 'Kết quả soát trên mẫu thử', text: 'App sinh thử 200 người trong máy, đọc lại từng phản hồi và sửa chỗ mâu thuẫn. Bảng so sánh cách cũ và cách mới; “0 mâu thuẫn còn lại” là sẵn sàng. Thanh trượt chỉnh mức “sàn sàn nhau” giữa các câu của một người.' },
  { screen: 'logic', target: 'logic-confirm', placement: 'above', title: 'Xác nhận rồi mới chạy', text: 'Mọi form phải qua bước này trước khi gửi. Hết lượt AI thì app hỏi bạn dán API key riêng rồi chạy tiếp. Bấm Tiếp để xem một chiến dịch tập dùng đang chạy.' },
  { screen: 'campaign', target: 'kpi', placement: 'below', title: 'Theo dõi trực tiếp', text: 'Tiến độ, tỷ lệ thành công và thời gian còn lại cập nhật ngay khi từng phản hồi được gửi.' },
  { screen: 'campaign', target: 'controls', placement: 'left', title: 'Tạm dừng và xuất dữ liệu', text: 'Tạm dừng / Tiếp tục bất cứ lúc nào. Xuất dữ liệu đã gửi ra Excel, có sẵn trang mã số để mở bằng SPSS.' },
  { screen: 'campaign', target: 'log', placement: 'above', title: 'Nhật ký gửi', text: 'Từng phản hồi vừa gửi và kết quả. Nếu Google giới hạn số lần gửi, app tự gửi chậm lại và ghi rõ ở đây.' },
  { screen: 'campaign', target: 'help', placement: 'right', title: 'Cần xem lại?', text: 'Mục Hướng dẫn có tour này và giải thích chi tiết từng tính năng, thuật ngữ, câu hỏi thường gặp.' },
];
