import { create } from 'zustand';
import { createJSONStorage, persist } from 'zustand/middleware';

import type { DataSource, QuestionRuleConfig, ScheduleConfig, SpssGroupConfig } from '@/types/campaign';

/** Bản nháp cấu hình của MỘT form (lưu trên máy để mở lại không mất). */
export interface FormConfig {
  name: string;
  rules: Record<string, QuestionRuleConfig>;
  groups: SpssGroupConfig[];
  dataSource: DataSource;
  excel: { fileName: string; records: Record<string, unknown>[]; validRows: number } | null;
  target: number;
  schedule: ScheduleConfig;
  proxy: string;
  useFallback: boolean;
}

export const defaultFormConfig = (): FormConfig => ({
  name: '',
  rules: {},
  groups: [],
  dataSource: 'PROBABILITY',
  excel: null,
  target: 100,
  schedule: { mode: 'SCHEDULED', duration_minutes: 60, concurrency: 5 },
  proxy: '',
  useFallback: true,
});

interface FormConfigState {
  configs: Record<string, FormConfig>;
  updateRule: (formId: string, rule: QuestionRuleConfig) => void;
  patchRules: (formId: string, rules: QuestionRuleConfig[]) => void;
  upsertGroup: (formId: string, group: SpssGroupConfig) => void;
  removeGroup: (formId: string, groupId: string) => void;
  patchConfig: (formId: string, patch: Partial<FormConfig>) => void;
  resetConfig: (formId: string) => void;
}

const withConfig = (state: FormConfigState, formId: string, change: (c: FormConfig) => FormConfig) => ({
  configs: { ...state.configs, [formId]: change(state.configs[formId] ?? defaultFormConfig()) },
});

export const useFormConfigStore = create<FormConfigState>()(
  persist(
    (set) => ({
      configs: {},
      updateRule: (formId, rule) =>
        set((s) => withConfig(s, formId, (c) => ({ ...c, rules: { ...c.rules, [rule.entry_id]: rule } }))),
      patchRules: (formId, rules) =>
        set((s) =>
          withConfig(s, formId, (c) => ({
            ...c,
            rules: { ...c.rules, ...Object.fromEntries(rules.map((r) => [r.entry_id, { ...c.rules[r.entry_id], ...r }])) },
          })),
        ),
      upsertGroup: (formId, group) =>
        set((s) =>
          withConfig(s, formId, (c) => ({
            ...c,
            groups: [...c.groups.filter((g) => g.group_id !== group.group_id), group],
          })),
        ),
      removeGroup: (formId, groupId) =>
        set((s) => withConfig(s, formId, (c) => ({ ...c, groups: c.groups.filter((g) => g.group_id !== groupId) }))),
      patchConfig: (formId, patch) => set((s) => withConfig(s, formId, (c) => ({ ...c, ...patch }))),
      resetConfig: (formId) => set((s) => withConfig(s, formId, () => defaultFormConfig())),
    }),
    {
      name: 'autoform.form-configs',
      storage: createJSONStorage(() => localStorage),
      version: 1,
      // Dữ liệu Excel (tới 20.000 dòng) có thể vượt giới hạn ~5 MB của localStorage → không lưu nháp;
      // mở lại app thì quay về tỷ lệ %, người dùng chọn lại file nếu cần.
      partialize: (state) => ({
        configs: Object.fromEntries(
          Object.entries(state.configs).map(([id, c]) => [id, { ...c, excel: null, dataSource: 'PROBABILITY' as const }]),
        ),
      }),
    },
  ),
);

const EMPTY = defaultFormConfig();

export function useFormConfig(formId: string): FormConfig {
  return useFormConfigStore((s) => s.configs[formId] ?? EMPTY);
}
