import { useEffect, useId, useState } from 'react';

import { type ApiError, toApiError } from '@/api/client';
import { campaignsApi } from '@/api/endpoints';
import { ErrorAlert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { Dialog } from '@/components/ui/Dialog';
import { Field, TextInput } from '@/components/ui/Field';
import { scaleValues } from '@/lib/questions';
import { scaleRange, spssCandidates } from '@/lib/spssCandidates';
import { useFormConfig, useFormConfigStore } from '@/store/formConfigStore';
import type { SpssGroupConfig, SpssGroupPreview } from '@/types/campaign';
import type { ParsedFormStructure } from '@/types/form';

import { AlphaResult } from './AlphaResult';
import { ItemPicker } from './ItemPicker';
import { TargetParams } from './TargetParams';

export const newGroup = (): SpssGroupConfig => ({
  group_id: `g-${Date.now().toString(36)}`,
  name: '',
  mean: 4,
  std: 0.7,
  r: 0.55,
  alpha_target: null,
  entries: [],
  reversed_entries: [],
  calibrate: true,
});

const toggle = (list: string[], id: string) => (list.includes(id) ? list.filter((x) => x !== id) : [...list, id]);

export function SpssGroupDialog({ formId, structure, initial, onClose }: {
  formId: string;
  structure: ParsedFormStructure;
  initial: SpssGroupConfig | null;
  onClose: () => void;
}) {
  const config = useFormConfig(formId);
  const upsert = useFormConfigStore((s) => s.upsertGroup);
  const nameId = useId();
  const [draft, setDraft] = useState<SpssGroupConfig>(initial ?? newGroup());
  const [preview, setPreview] = useState<SpssGroupPreview | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  useEffect(() => setPreview(null), [draft]);

  const usedElsewhere = new Set(config.groups.filter((g) => g.group_id !== draft.group_id).flatMap((g) => g.entries));
  const candidates = spssCandidates(structure)
    .map((c) => ({ ...c, questions: c.questions.filter((q) => !usedElsewhere.has(q.entry_id)) }))
    .filter((c) => c.questions.length > 0);
  const firstSelected = structure.questions.find((q) => q.entry_id === draft.entries[0]);
  const lockedScale = firstSelected ? scaleValues(firstSelected).join(',') : null;
  const scale = firstSelected ? scaleRange(firstSelected) : ([1, 5] as [number, number]);
  const valid = draft.entries.length >= 2 && draft.name.trim().length > 0;
  const patch = (p: Partial<SpssGroupConfig>) => setDraft((d) => ({ ...d, ...p }));

  const runPreview = async () => {
    setBusy(true);
    setError(null);
    try {
      const result = await campaignsApi.previewSpss({ form_id: formId, rules: Object.values(config.rules), spss_groups: [draft], sample_size: 200 });
      setPreview(result.groups[0] ?? null);
    } catch (err) {
      setError(toApiError(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Dialog
      open
      size="xl"
      onClose={onClose}
      title="Nhóm tương quan SPSS"
      description="Các câu trong cùng nhóm được sinh tương quan với nhau để đạt độ tin cậy Cronbach’s Alpha mong muốn."
      footer={
        <>
          <Button onClick={onClose}>Hủy</Button>
          <Button variant="primary" disabled={!valid} onClick={() => { upsert(formId, { ...draft, name: draft.name.trim() }); onClose(); }}>Lưu nhóm</Button>
        </>
      }
    >
      <div className="flex flex-wrap gap-6">
        <div className="flex min-w-[360px] flex-1 flex-col gap-4">
          <Field label="Tên nhân tố" htmlFor={nameId}>
            <TextInput id={nameId} value={draft.name} placeholder="VD: Hình ảnh thương hiệu" onChange={(e) => patch({ name: e.target.value })} />
          </Field>
          {candidates.length === 0 ? (
            <p className="m-0 text-sm text-muted">Form không còn câu thang đo nào chưa thuộc nhóm.</p>
          ) : (
            <ItemPicker
              candidates={candidates}
              selected={draft.entries}
              reversed={draft.reversed_entries}
              lockedScale={lockedScale}
              onToggle={(id) => setDraft((d) => {
                const entries = toggle(d.entries, id);
                return { ...d, entries, reversed_entries: d.reversed_entries.filter((r) => entries.includes(r)) };
              })}
              onToggleReversed={(id) => patch({ reversed_entries: toggle(draft.reversed_entries, id) })}
            />
          )}
        </div>
        <div className="flex min-w-[360px] flex-1 flex-col gap-4">
          <h3 className="m-0 text-base font-semibold">Thông số mục tiêu</h3>
          <TargetParams draft={draft} scale={scale} onChange={patch} />
          <Button variant="secondary" className="border-accent text-accent" disabled={draft.entries.length < 2} loading={busy} onClick={() => void runPreview()}>
            Kiểm tra thử Cronbach’s Alpha
          </Button>
          <ErrorAlert error={error} />
          {preview && <AlphaResult preview={preview} />}
        </div>
      </div>
    </Dialog>
  );
}
