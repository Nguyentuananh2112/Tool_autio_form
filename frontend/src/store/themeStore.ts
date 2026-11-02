import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export type ThemePreference = 'light' | 'dark' | 'system';

interface ThemeState {
  preference: ThemePreference;
  setPreference: (preference: ThemePreference) => void;
}

export const useThemeStore = create<ThemeState>()(
  persist((set) => ({ preference: 'system', setPreference: (preference) => set({ preference }) }), {
    name: 'autoform.theme',
  }),
);

export function resolveDark(preference: ThemePreference): boolean {
  if (preference === 'system') return window.matchMedia?.('(prefers-color-scheme: dark)').matches ?? false;
  return preference === 'dark';
}
