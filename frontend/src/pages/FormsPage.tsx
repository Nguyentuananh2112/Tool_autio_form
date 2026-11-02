import { formsApi } from '@/api/endpoints';
import { QuickParseCard } from '@/components/dashboard/QuickParseCard';
import { RecentForms } from '@/components/dashboard/RecentForms';
import { PageHeader } from '@/components/layout/PageHeader';
import { StepIndicator } from '@/components/layout/StepIndicator';
import { ErrorAlert } from '@/components/ui/Alert';
import { useAsyncData } from '@/hooks/useAsyncData';

/** Mục "Cấu hình khảo sát": bước 1 — chọn hoặc phân tích form. */
export function FormsPage() {
  const forms = useAsyncData(formsApi.list, []);
  return (
    <>
      <StepIndicator current={1} />
      <PageHeader title="Cấu hình khảo sát" description="Dán link một Google Form mới, hoặc mở lại form đã phân tích." />
      <ErrorAlert error={forms.error} />
      <div className="flex flex-wrap gap-4">
        <div className="min-w-[320px] flex-[3]"><QuickParseCard /></div>
        <div className="min-w-[280px] flex-[2]"><RecentForms forms={forms.data ?? []} /></div>
      </div>
    </>
  );
}
