import { useCallback, useEffect, useState } from 'react';

import type { UpdateInfo } from '@/types/settings';

/** Luồng cập nhật (artboard 5). Chỉ hoạt động trong app desktop — vỏ desktop cung cấp `window.autoformDesktop.updater`. */
export type UpdatePhase = 'idle' | 'checking' | 'available' | 'downloading' | 'ready' | 'error';

const SNOOZE_KEY = 'autoform.update-snoozed';

export interface Updater {
  supported: boolean;
  phase: UpdatePhase;
  info: UpdateInfo | null;
  progress: number;
  error: string | null;
  dialogOpen: boolean;
  check: () => Promise<void>;
  openDialog: () => void;
  snooze: () => void;
  download: () => Promise<void>;
  installNow: () => Promise<void>;
  installOnQuit: () => Promise<void>;
}

export function useUpdater(autoCheck = true): Updater {
  const bridge = window.autoformDesktop?.updater;
  const [phase, setPhase] = useState<UpdatePhase>('idle');
  const [info, setInfo] = useState<UpdateInfo | null>(null);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);

  const check = useCallback(async () => {
    if (!bridge) return;
    setPhase('checking');
    try {
      const found = await bridge.check();
      setInfo(found);
      setPhase(found ? 'available' : 'idle');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Không kiểm tra được bản cập nhật.');
      setPhase('error');
    }
  }, [bridge]);

  useEffect(() => {
    if (autoCheck) void check();
  }, [autoCheck, check]);

  const download = useCallback(async () => {
    if (!bridge) return;
    setPhase('downloading');
    setProgress(0);
    try {
      await bridge.download(setProgress);
      setPhase('ready');
      setDialogOpen(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Tải bản cập nhật thất bại.');
      setPhase('error');
    }
  }, [bridge]);

  const snoozed = info !== null && localStorage.getItem(SNOOZE_KEY) === info.version;

  return {
    supported: Boolean(bridge),
    phase: snoozed && phase === 'available' ? 'idle' : phase,
    info,
    progress,
    error,
    dialogOpen,
    check,
    openDialog: () => setDialogOpen(true),
    snooze: () => {
      if (info) localStorage.setItem(SNOOZE_KEY, info.version);
      setDialogOpen(false);
    },
    download,
    installNow: async () => {
      await bridge?.installAndRestart();
    },
    installOnQuit: async () => {
      await bridge?.installOnQuit();
      setDialogOpen(false);
    },
  };
}
