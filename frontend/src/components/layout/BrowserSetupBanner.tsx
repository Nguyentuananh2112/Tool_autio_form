import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { ProgressBar } from '@/components/ui/ProgressBar';
import { useBrowserInstall } from '@/hooks/useBrowserInstall';

/**
 * Chuẩn bị lần đầu: app tự tải trình duyệt dự phòng nếu máy chưa có (người dùng không phải làm gì).
 * Đã có → không hiện gì. Đang tải → dải tiến độ. Lỗi (mất mạng…) → nút Thử lại; lần mở app sau cũng tự thử lại.
 */
export function BrowserSetupBanner() {
  const { status, install } = useBrowserInstall({ autoInstall: true });
  if (!status || status.installed) return null;

  if (status.installing) {
    return (
      <Alert tone="info" title="Đang chuẩn bị cho lần dùng đầu tiên">
        <div className="flex flex-col gap-2">
          <span className="tabular">
            App đang tự tải trình duyệt dự phòng ({status.detail ?? 'đang tải…'}). Chỉ tải một lần; bạn vẫn dùng app bình thường.
          </span>
          <ProgressBar value={status.percent ?? 0} label="Tiến độ chuẩn bị lần đầu" size="sm" />
        </div>
      </Alert>
    );
  }

  if (!status.error) return null;
  return (
    <Alert
      tone="warn"
      title="Chưa chuẩn bị xong trình duyệt dự phòng"
      action={<Button onClick={() => void install()}>Thử lại</Button>}
    >
      {status.error} App vẫn gửi được phần lớn form; lần mở app sau sẽ tự thử lại.
    </Alert>
  );
}
