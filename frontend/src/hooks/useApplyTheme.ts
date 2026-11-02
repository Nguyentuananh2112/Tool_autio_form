import { useEffect } from 'react';

import { resolveDark, useThemeStore } from '@/store/themeStore';

/** Gắn/bỏ class "dark" trên <html> theo lựa chọn của người dùng (và theo Windows khi chọn "Theo hệ thống"). */
export function useApplyTheme(): void {
  const preference = useThemeStore((s) => s.preference);
  useEffect(() => {
    const apply = () => document.documentElement.classList.toggle('dark', resolveDark(preference));
    apply();
    if (preference !== 'system' || !window.matchMedia) return undefined;
    const media = window.matchMedia('(prefers-color-scheme: dark)');
    media.addEventListener('change', apply);
    return () => media.removeEventListener('change', apply);
  }, [preference]);
}
