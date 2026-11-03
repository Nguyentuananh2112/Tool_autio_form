import { Link, useParams } from 'react-router-dom';

import { formsApi } from '@/api/endpoints';
import { StepIndicator } from '@/components/layout/StepIndicator';
import { AiQuotaDialog } from '@/components/logic/AiQuotaDialog';
import { AttitudeGroupsSection } from '@/components/logic/AttitudeGroupsSection';
import { ExclusiveSection, TextAttitudeSection } from '@/components/logic/ExclusiveAndTextSections';
import { LogicPassCards } from '@/components/logic/LogicPassCards';
import { ConsistencyCard, ReviewResultCard, SamplePersonCard } from '@/components/logic/ReviewSidebar';
import { RulesSection } from '@/components/logic/RulesSection';
import { Alert, ErrorAlert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { Spinner } from '@/components/ui/EmptyState';
import { useAsyncData } from '@/hooks/useAsyncData';
import { useCampaignActions } from '@/hooks/useCampaignActions';
import { useLogicReview } from '@/hooks/useLogicReview';
import { formatDateTime } from '@/lib/format';
import { useFormConfig } from '@/store/formConfigStore';
import type { FormDetail } from '@/types/form';

function LogicBody({ form }: { form: FormDetail }) {
  const config = useFormConfig(form.id);
  const logic = useLogicReview(form.id, config);
  const actions = useCampaignActions(form.id, form.title, config);
  const questions = form.structure.questions;
  const { draft, result, phase } = logic;
  const busy = phase !== 'idle';

  const confirmAndRun = async () => {
    if (await logic.confirm()) await actions.start();
  };

  return (
    <>
      <StepIndicator current={3} />
      <header className="flex flex-col gap-1.5">
        <h1 className="m-0 text-2xl font-bold tracking-tight">Soát logic trước khi chạy</h1>
        <p className="m-0 max-w-[760px] text-sm text-muted">
          App đã đọc toàn bộ câu hỏi để tìm những câu phải trả lời khớp nhau. Xem lại các điểm dưới đây, sửa nếu cần, rồi bấm <b>Xác nhận &amp; chạy</b>. Mọi phản hồi đều được soát lại một lần nữa trước khi gửi.
        </p>
      </header>

      <LogicPassCards phase={phase} logic={draft} result={result} questionCount={questions.length} />
      <ErrorAlert error={logic.error} />
      {logic.error && (
        <div className="flex flex-wrap gap-2">
          <Button onClick={() => (draft ? logic.review() : void logic.analyze())}>Thử lại</Button>
          <Link to={`/forms/${form.id}?tab=weights`} className="inline-flex min-h-11 items-center px-2 text-sm font-semibold">Quay lại bước Cấu hình</Link>
        </div>
      )}

      {draft && (
        <div className="flex flex-wrap items-start gap-5">
          <div className="flex min-w-0 flex-[1_1_560px] flex-col gap-4" data-tour="logic-groups">
            <AttitudeGroupsSection logic={draft} questions={questions} onChange={logic.setDraft} />
            <RulesSection logic={draft} questions={questions} onChange={logic.setDraft} />
            <ExclusiveSection logic={draft} questions={questions} onChange={logic.setDraft} />
            <TextAttitudeSection logic={draft} questions={questions} rules={config.rules} />
          </div>
          <aside className="flex min-w-0 flex-[1_1_340px] flex-col gap-4" data-tour="logic-result">
            <ConsistencyCard logic={draft} onChange={logic.setDraft} />
            {logic.dirty && (
              <Alert tone="warn" title="Bạn vừa sửa bản đồ logic" action={<Button size="sm" loading={phase === 'reviewing'} onClick={logic.review}>Soát lại</Button>}>
                Bấm Soát lại để kiểm tra trên mẫu thử trước khi chạy.
              </Alert>
            )}
            {result && <ReviewResultCard result={result} logic={draft} questions={questions} />}
            {result && <SamplePersonCard result={result} logic={draft} questions={questions} />}
          </aside>
        </div>
      )}
      {!draft && busy && <Spinner label={phase === 'analyzing' ? 'AI đang đọc toàn bộ câu hỏi… (có thể mất 1–2 phút)' : 'Đang mở…'} />}

      <ErrorAlert error={actions.error} />
      <footer className="flex flex-wrap items-center justify-end gap-2 pt-1" data-tour="logic-confirm">
        <span className="mr-auto text-[13px] text-muted">
          {draft?.source === 'DEMO' ? 'Form tập dùng: bản đồ dựng sẵn, không cần AI.'
            : draft?.model ? `Đọc bởi ${draft.model}${draft.analyzed_at ? ` · ${formatDateTime(draft.analyzed_at)}` : ''} · đã lưu, lần sau không đọc lại` : ''}
        </span>
        <Link to={`/forms/${form.id}?tab=weights`} className="inline-flex min-h-11 items-center px-3 text-sm font-semibold">Quay lại Cấu hình</Link>
        <Button disabled={busy} loading={phase === 'analyzing'} onClick={() => void logic.analyze()}>Soát lại từ đầu</Button>
        <Button variant="primary" size="lg" disabled={!logic.ready} loading={actions.busy === 'start'} onClick={() => void confirmAndRun()}>
          Xác nhận &amp; chạy {config.target} phản hồi
        </Button>
      </footer>

      {logic.quota && (
        <AiQuotaDialog
          keys={logic.quota.keys}
          message={logic.quota.message}
          onClose={logic.closeQuota}
          onSaved={() => { const retry = logic.quota?.retry; logic.closeQuota(); retry?.(); }}
        />
      )}
    </>
  );
}

/** Bước ③ Soát logic (artboard 11, quy tắc 6): bắt buộc trước khi chạy dữ liệu tự sinh. */
export function LogicReviewPage() {
  const { formId = '' } = useParams();
  const form = useAsyncData(() => formsApi.get(formId), [formId]);
  if (form.loading && !form.data) return <Spinner label="Đang mở form…" />;
  if (!form.data) return <ErrorAlert error={form.error ?? { message: 'Không tìm thấy form.' }} />;
  return <LogicBody form={form.data} />;
}
