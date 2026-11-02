import { useParams, useSearchParams } from 'react-router-dom';

import { formsApi } from '@/api/endpoints';
import { StepIndicator } from '@/components/layout/StepIndicator';
import { SpssPanel } from '@/components/spss/SpssPanel';
import { ErrorAlert } from '@/components/ui/Alert';
import { Spinner } from '@/components/ui/EmptyState';
import { ExcelImportPanel } from '@/components/workspace/excel/ExcelImportPanel';
import { MissingConfigAlert } from '@/components/workspace/MissingConfigAlert';
import { PageRail } from '@/components/workspace/PageRail';
import { QuestionList } from '@/components/workspace/QuestionList';
import { RunSettingsPanel } from '@/components/workspace/run-settings/RunSettingsPanel';
import { SourceTabs, type WorkspaceTab } from '@/components/workspace/SourceTabs';
import { WorkspaceHeader } from '@/components/workspace/WorkspaceHeader';
import { useAsyncData } from '@/hooks/useAsyncData';
import { computeReadiness } from '@/lib/readiness';
import { useFormConfig } from '@/store/formConfigStore';
import type { FormDetail } from '@/types/form';

const TABS: WorkspaceTab[] = ['weights', 'spss', 'excel'];

function WorkspaceBody({ form }: { form: FormDetail }) {
  const [params, setParams] = useSearchParams();
  const config = useFormConfig(form.id);
  const requested = params.get('tab') as WorkspaceTab | null;
  const tab: WorkspaceTab = requested && TABS.includes(requested) ? requested : 'weights';
  const readiness = computeReadiness(form.structure, config.rules, config.groups);

  return (
    <>
      <StepIndicator current={2} />
      <WorkspaceHeader form={form} />
      <SourceTabs active={tab} onChange={(next) => setParams({ tab: next }, { replace: true })} counts={{ spss: config.groups.length }} />
      <div className={tab === 'weights' ? 'grid items-start gap-5 lg:grid-cols-[230px_minmax(0,1fr)_320px]' : 'grid items-start gap-5 xl:grid-cols-[minmax(0,1fr)_320px]'}>
        {tab === 'weights' && <PageRail structure={form.structure} readiness={readiness} />}
        <div className="flex min-w-0 flex-col gap-4">
          {tab === 'weights' && (
            <>
              {config.dataSource !== 'EXCEL' && <MissingConfigAlert formId={form.id} structure={form.structure} readiness={readiness} />}
              <QuestionList formId={form.id} structure={form.structure} />
            </>
          )}
          {tab === 'spss' && <SpssPanel formId={form.id} structure={form.structure} />}
          {tab === 'excel' && <ExcelImportPanel formId={form.id} structure={form.structure} />}
        </div>
        <RunSettingsPanel form={form} readiness={readiness} />
      </div>
    </>
  );
}

export function FormWorkspacePage() {
  const { formId = '' } = useParams();
  const form = useAsyncData(() => formsApi.get(formId), [formId]);
  if (form.loading && !form.data) return <Spinner label="Đang mở form…" />;
  if (!form.data) return <ErrorAlert error={form.error ?? { message: 'Không tìm thấy form.' }} />;
  return <WorkspaceBody form={form.data} />;
}
