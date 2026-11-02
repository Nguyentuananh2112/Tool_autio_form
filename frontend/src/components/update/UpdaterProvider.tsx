import { createContext, useContext, type ReactNode } from 'react';

import { type Updater, useUpdater } from '@/hooks/useUpdater';

const UpdaterContext = createContext<Updater | null>(null);

/** Một bộ kiểm tra cập nhật cho cả app (banner, thanh bên, Cài đặt dùng chung). */
export function UpdaterProvider({ children }: { children: ReactNode }) {
  const updater = useUpdater(true);
  return <UpdaterContext.Provider value={updater}>{children}</UpdaterContext.Provider>;
}

export function useUpdaterContext(): Updater {
  const value = useContext(UpdaterContext);
  if (!value) throw new Error('useUpdaterContext phải nằm trong <UpdaterProvider>');
  return value;
}
