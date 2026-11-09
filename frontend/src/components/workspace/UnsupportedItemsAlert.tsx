import { Alert } from '@/components/ui/Alert';
import type { ParsedFormStructure } from '@/types/form';

/** Form có câu kiểu app chưa điền được (VD tải tệp lên). Câu bắt buộc → Google từ chối mọi phản hồi (BUG-017). */
export function UnsupportedItemsAlert({ structure }: { structure: ParsedFormStructure }) {
  const items = structure.unsupported_items ?? [];
  if (items.length === 0) return null;
  const blocking = items.filter((item) => item.is_required);
  return (
    <Alert
      tone={blocking.length > 0 ? 'bad' : 'warn'}
      title={blocking.length > 0
        ? `Form có ${blocking.length} câu bắt buộc mà app chưa điền được — chưa thể chạy`
        : `Form có ${items.length} câu app chưa điền được (không bắt buộc, sẽ để trống)`}
    >
      <ul className="m-0 list-disc pl-5">
        {items.map((item) => (
          <li key={item.item_id}>{item.title} (trang {item.page_index + 1}){item.is_required ? ' — bắt buộc' : ''}</li>
        ))}
      </ul>
      {blocking.length > 0 && <p className="m-0 mt-1">Cách xử lý: trong Google Form, tắt &quot;Bắt buộc&quot; ở các câu này (hoặc đổi sang kiểu trắc nghiệm / thang đo), rồi phân tích lại link.</p>}
    </Alert>
  );
}
