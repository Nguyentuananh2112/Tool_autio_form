import { settingsApi } from '@/api/endpoints';
import { PageHeader } from '@/components/layout/PageHeader';
import { AppearanceSection } from '@/components/settings/AppearanceSection';
import { DataSection } from '@/components/settings/DataSection';
import { GeminiKeySection } from '@/components/settings/GeminiKeySection';
import { UpdateSection } from '@/components/settings/UpdateSection';
import { ErrorAlert } from '@/components/ui/Alert';
import { useAsyncData } from '@/hooks/useAsyncData';

export function SettingsPage() {
  const settings = useAsyncData(settingsApi.get, []);
  const version = window.autoformDesktop?.version ?? settings.data?.app_version ?? null;
  return (
    <div className="flex max-w-[880px] flex-col gap-5">
      <PageHeader title="Cài đặt" />
      <ErrorAlert error={settings.error} />
      <GeminiKeySection settings={settings.data} onSaved={() => void settings.reload()} />
      <UpdateSection version={version} />
      <AppearanceSection />
      <DataSection settings={settings.data} />
    </div>
  );
}
