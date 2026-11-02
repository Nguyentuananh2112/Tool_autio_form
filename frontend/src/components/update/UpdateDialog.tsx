import { useAsyncData } from '@/hooks/useAsyncData';
import { campaignsApi } from '@/api/endpoints';
import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { Dialog } from '@/components/ui/Dialog';
import { ProgressBar } from '@/components/ui/ProgressBar';

import { useUpdaterContext } from './UpdaterProvider';

const MB = 1024 * 1024;

/** Luồng artboard 5: Có bản mới → Đang tải → Sẵn sàng cài → Khởi động lại. */
export function UpdateDialog() {
  const updater = useUpdaterContext();
  const running = useAsyncData(campaignsApi.list, [updater.dialogOpen]);
  const runningCount = (running.data ?? []).filter((c) => c.is_active).length;
  const info = updater.info;
  if (!info) return null;

  const close = updater.snooze;
  const sizeMb = Math.max(1, Math.round(info.sizeBytes / MB));

  if (updater.phase === 'ready') {
    return (
      <Dialog
        open={updater.dialogOpen}
        onClose={close}
        title="Sẵn sàng cài đặt"
        description={`Ứng dụng sẽ đóng, cài bản ${info.version} rồi tự mở lại. Dữ liệu và cấu hình được giữ nguyên.`}
        footer={
          <>
            <Button onClick={() => void updater.installOnQuit()}>Cài khi tắt ứng dụng</Button>
            <Button variant="primary" onClick={() => void updater.installNow()}>Khởi động lại ngay</Button>
          </>
        }
      >
        {runningCount > 0 && (
          <Alert tone="warn">{runningCount} chiến dịch đang chạy sẽ được <strong>tạm dừng an toàn</strong> và tự chạy tiếp sau khi mở lại.</Alert>
        )}
      </Dialog>
    );
  }

  return (
    <Dialog
      open={updater.dialogOpen}
      onClose={close}
      title={updater.phase === 'downloading' ? `Đang tải bản cập nhật ${info.version}…` : `Có phiên bản mới: ${info.version}`}
      description={`Dung lượng tải khoảng ${sizeMb} MB · phát hành ${new Date(info.releaseDate).toLocaleDateString('vi-VN')}`}
      footer={
        updater.phase === 'downloading' ? (
          <Button onClick={close}>Chạy nền</Button>
        ) : (
          <>
            <Button onClick={close}>Để sau</Button>
            <Button variant="primary" onClick={() => void updater.download()}>Cập nhật ngay</Button>
          </>
        )
      }
    >
      {updater.phase === 'downloading' ? (
        <div className="flex flex-col gap-3">
          <ProgressBar value={updater.progress} label="Tiến độ tải" size="lg" />
          <span className="tabular text-sm text-muted">{updater.progress}% · bạn vẫn dùng ứng dụng bình thường trong lúc tải.</span>
        </div>
      ) : (
        <div className="flex flex-col gap-4">
          <ul className="m-0 flex list-disc flex-col gap-1 pl-5 text-sm text-muted">
            {info.notes.map((note) => <li key={note}>{note}</li>)}
          </ul>
          {runningCount > 0 && (
            <Alert tone="warn">{runningCount} chiến dịch đang chạy sẽ được tạm dừng an toàn trước khi cài và tự chạy tiếp sau khi mở lại.</Alert>
          )}
          {updater.error && <Alert tone="bad">{updater.error}</Alert>}
        </div>
      )}
    </Dialog>
  );
}
