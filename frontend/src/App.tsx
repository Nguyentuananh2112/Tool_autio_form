import { HashRouter, Route, Routes } from 'react-router-dom';

import { CompletionNotifier } from '@/components/campaign/CompletionNotifier';
import { AppShell } from '@/components/layout/AppShell';
import { TourProvider } from '@/components/tour/TourProvider';
import { UpdaterProvider } from '@/components/update/UpdaterProvider';
import { EmptyState } from '@/components/ui/EmptyState';
import { useApplyTheme } from '@/hooks/useApplyTheme';
import { CampaignDetailPage } from '@/pages/CampaignDetailPage';
import { CampaignListPage } from '@/pages/CampaignListPage';
import { DashboardPage } from '@/pages/DashboardPage';
import { FormsPage } from '@/pages/FormsPage';
import { FormWorkspacePage } from '@/pages/FormWorkspacePage';
import { HelpPage } from '@/pages/HelpPage';
import { LogicReviewPage } from '@/pages/LogicReviewPage';
import { SettingsPage } from '@/pages/SettingsPage';

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<DashboardPage />} />
      <Route path="/forms" element={<FormsPage />} />
      <Route path="/forms/:formId" element={<FormWorkspacePage />} />
      <Route path="/forms/:formId/logic" element={<LogicReviewPage />} />
      <Route path="/campaigns" element={<CampaignListPage />} />
      <Route path="/campaigns/:campaignId" element={<CampaignDetailPage />} />
      <Route path="/help" element={<HelpPage />} />
      <Route path="/settings" element={<SettingsPage />} />
      <Route path="*" element={<EmptyState title="Không tìm thấy trang" description="Dùng thanh bên trái để quay lại." />} />
    </Routes>
  );
}

export function App() {
  useApplyTheme();
  return (
    // HashRouter: app desktop nạp giao diện từ file trên ổ đĩa, không có máy chủ web để xử lý đường dẫn
    <HashRouter>
      <UpdaterProvider>
        <TourProvider>
          <AppShell>
            <AppRoutes />
          </AppShell>
          <CompletionNotifier />
        </TourProvider>
      </UpdaterProvider>
    </HashRouter>
  );
}
