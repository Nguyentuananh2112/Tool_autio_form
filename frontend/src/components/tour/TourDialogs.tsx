import { Button } from '@/components/ui/Button';
import { Dialog } from '@/components/ui/Dialog';

export function TourWelcomeDialog({ open, total, onStart, onLater }: { open: boolean; total: number; onStart: () => void; onLater: () => void }) {
  return (
    <Dialog
      open={open}
      onClose={onLater}
      title="Chào mừng đến với Auto-Form"
      footer={<><Button onClick={onLater}>Để sau</Button><Button variant="primary" onClick={onStart}>Bắt đầu tour</Button></>}
    >
      <p className="m-0 text-[15px] leading-relaxed text-muted">
        Mình sẽ dẫn bạn qua <strong className="text-ink">{total} tính năng chính</strong>, giải thích ngay tại chỗ trên màn hình. Tour dùng một form mẫu nên không gửi gì ra ngoài. Mất khoảng 1 phút.
      </p>
    </Dialog>
  );
}

export function TourDoneDialog({ open, onRestart, onClose }: { open: boolean; onRestart: () => void; onClose: () => void }) {
  return (
    <Dialog
      open={open}
      onClose={onClose}
      title="Xong rồi! Bắt đầu với form đầu tiên nhé"
      footer={<><Button onClick={onRestart}>Xem lại tour</Button><Button variant="primary" onClick={onClose}>Dán link form</Button></>}
    >
      <p className="m-0 text-[15px] leading-relaxed text-muted">
        Dán link Google Form ở màn hình Tổng quan, hoặc tiếp tục tập với form mẫu. Bạn có thể xem lại tour bất cứ lúc nào trong mục <strong className="text-ink">Hướng dẫn</strong>.
      </p>
    </Dialog>
  );
}
