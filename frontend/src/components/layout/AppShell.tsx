import type { ReactNode } from 'react';

import { UpdateDialog } from '@/components/update/UpdateDialog';
import { settingsApi } from '@/api/endpoints';
import { useAsyncData } from '@/hooks/useAsyncData';

import { BrowserSetupBanner } from './BrowserSetupBanner';
import { Sidebar } from './Sidebar';

export function AppShell({ children }: { children: ReactNode }) {
  const settings = useAsyncData(settingsApi.get, []);
  const version = window.autoformDesktop?.version ?? settings.data?.app_version ?? null;
  return (
    <div className="flex min-h-screen flex-col bg-bg md:flex-row">
      <Sidebar version={version} />
      <main className="flex min-w-0 flex-1 flex-col gap-6 px-4 py-7 md:px-8 lg:px-10">
        <BrowserSetupBanner />
        {children}
      </main>
      <UpdateDialog />
    </div>
  );
}
