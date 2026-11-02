import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { Dialog } from '@/components/ui/Dialog';
import type { TrialSubmitResponse } from '@/types/campaign';

/** Kết quả "Gửi thử 1 phản hồi": thành công/thất bại + dữ liệu đã (hoặc sẽ) gửi. */
export function TrialResultDialog({ result, onClose }: { result: TrialSubmitResponse | null; onClose: () => void }) {
  if (!result) return null;
  const simulated = result.engine_used === 'SIMULATED';
  const entries = Object.entries(result.payload_sent).filter(([key]) => key.startsWith('entry.'));
  return (
    <Dialog
      open
      onClose={onClose}
      title={simulated ? 'Xem trước 1 phản hồi (không gửi)' : result.success ? 'Gửi thử thành công' : 'Gửi thử chưa thành công'}
      description={`Đường đi qua các trang: ${result.page_history}`}
      footer={<Button variant="primary" onClick={onClose}>Đóng</Button>}
      size="lg"
    >
      <div className="flex flex-col gap-4">
        {simulated ? (
          <Alert tone="info">Đây là mô phỏng. Không có dữ liệu nào được gửi ra ngoài.</Alert>
        ) : result.success ? (
          <Alert tone="ok">Google đã nhận phản hồi. Kiểm tra tab Câu trả lời trong Google Forms để đối chiếu.</Alert>
        ) : (
          <Alert tone="bad" title={result.error ?? 'Google không nhận phản hồi.'}>Mã HTTP {result.status_code}. Kiểm tra lại cấu hình câu trả lời rồi thử lại.</Alert>
        )}
        <div className="max-h-80 overflow-y-auto rounded-[10px] border border-line">
          <table className="w-full border-collapse text-sm">
            <tbody>
              {entries.map(([key, value]) => (
                <tr key={key} className="border-t border-line first:border-t-0">
                  <th scope="row" className="w-56 px-3 py-2 text-left font-mono text-xs font-medium text-muted">{key}</th>
                  <td className="px-3 py-2">{Array.isArray(value) ? value.join('; ') : value}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </Dialog>
  );
}
