import { Badge, Tag } from '@/components/ui/Badge';
import { useQuestionRule } from '@/hooks/useQuestionRule';
import { presetWeights, type PresetKind } from '@/lib/presets';
import { choiceOptions, isBranching, sectionTitle } from '@/lib/questions';
import { OTHER_OPTION_VALUE, type ParsedFormStructure, type ParsedQuestion } from '@/types/form';

import { BranchPathPreview } from '../weights/BranchPathPreview';
import { LinesEditor } from '../weights/LinesEditor';
import { PresetButtons, WeightTotal } from '../weights/PresetButtons';
import { WeightSliderRow } from '../weights/WeightSliderRow';
import { QuestionCardFrame } from './QuestionCardFrame';

/** Trắc nghiệm / Thả xuống / Thang đo / Hàng của lưới: tỷ lệ % theo từng đáp án. */
export function ChoiceQuestionCard({ formId, structure, question, tourId }: {
  formId: string;
  structure: ParsedFormStructure;
  question: ParsedQuestion;
  tourId?: string;
}) {
  const { rule, weights, inGroup, update, setWeight } = useQuestionRule(formId, question);
  const branching = isBranching(question);
  const otherOn = (weights[OTHER_OPTION_VALUE] ?? 0) > 0;
  const missingOther = otherOn && !(rule?.other_text_pool?.length);
  const total = Object.values(weights).reduce((sum, w) => sum + w, 0);

  const applyPreset = (kind: PresetKind) => {
    const values = presetWeights(kind, choiceOptions(question).length);
    let index = 0;
    update({ weights: Object.fromEntries(question.options.map((o) => [o.value, o.is_other ? 0 : values[index++] ?? 0])) });
  };

  if (inGroup) {
    return (
      <QuestionCardFrame question={question} badges={<Badge tone="accent">Nhóm SPSS: {inGroup.name}</Badge>}>
        <p className="m-0 text-sm text-muted">Câu này thuộc nhóm tương quan “{inGroup.name}”: tỷ lệ được nhóm tự tính theo điểm trung bình {inGroup.mean} để đạt độ tin cậy mong muốn.</p>
      </QuestionCardFrame>
    );
  }

  return (
    <QuestionCardFrame
      question={question}
      tourId={tourId}
      state={missingOther ? 'missing' : branching ? 'branch' : 'normal'}
      badges={branching && <Tag tone="accent">Rẽ nhánh</Tag>}
    >
      <div className="flex flex-col gap-2.5">
        {question.options.map((option) => (
          <WeightSliderRow
            key={option.value}
            label={option.label}
            sublabel={branching && option.jump_to_section_id !== null && option.jump_to_section_id !== -2 ? `→ ${sectionTitle(structure, option.jump_to_section_id)}` : undefined}
            value={weights[option.value] ?? 0}
            onChange={(percent) => setWeight(option.value, percent)}
          />
        ))}
      </div>
      {otherOn && (
        <LinesEditor label="Nội dung cho “Mục khác”" value={rule?.other_text_pool ?? []} placeholder="VD: Sendo" rows={2} onChange={(lines) => update({ other_text_pool: lines })} />
      )}
      {branching && <BranchPathPreview formId={formId} structure={structure} />}
      <div className="flex flex-wrap items-center justify-between gap-2.5 border-t border-line pt-3">
        <PresetButtons onPick={applyPreset} />
        <WeightTotal total={total} />
      </div>
    </QuestionCardFrame>
  );
}
