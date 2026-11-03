import { OTHER_OPTION_VALUE, type ParsedQuestion } from '@/types/form';

import { defaultCheckboxPercent, effectiveWeights } from './useQuestionRule';

function checkbox(count: number, isRequired = false): ParsedQuestion {
  const options = Array.from({ length: count }, (_, i) => ({ label: `L${i}`, value: `L${i}`, is_other: false, jump_to_section_id: null }));
  options.push({ label: 'Mục khác', value: OTHER_OPTION_VALUE, is_other: true, jump_to_section_id: null });
  return {
    item_id: 1, entry_id: '1', title: 'Câu', description: null, type_id: 4, type_name: 'CHECKBOX', page_index: 0,
    is_required: isRequired, options, scale_low_label: null, scale_high_label: null, grid_item_id: null,
    grid_title: null, row_label: null, is_multi_select: true,
  };
}

const rule = (patch: { min_checked?: number; max_checked?: number | null } = {}) => ({ entry_id: '1', question_type: 4, ...patch });

// Cùng bảng giá trị với backend tests/unit/test_spss_validation.py (BUG-014)
describe('defaultCheckboxPercent', () => {
  it.each([
    [11, true, 0, 3, 18.2],
    [11, false, 0, 3, 13.6],
    [10, false, 2, 4, 30],
    [4, true, 0, 4, 50],
    [40, false, 0, 1, 5],
  ])('%i ô, bắt buộc=%s, min=%i, max=%i → %f%%', (count, required, min, max, expected) => {
    expect(defaultCheckboxPercent(checkbox(count, required), rule({ min_checked: min, max_checked: max }))).toBe(expected);
  });

  it('không giới hạn tối đa thì giữ 50%', () => {
    expect(defaultCheckboxPercent(checkbox(11), undefined)).toBe(50);
    expect(defaultCheckboxPercent(checkbox(11), rule({ max_checked: null }))).toBe(50);
  });
});

describe('effectiveWeights hộp kiểm', () => {
  it('có giới hạn: mọi ô dùng mức mặc định mới, "Mục khác" 0', () => {
    const weights = effectiveWeights(checkbox(11, true), rule({ max_checked: 3 }));
    expect(weights[OTHER_OPTION_VALUE]).toBe(0);
    expect(new Set(Object.entries(weights).filter(([k]) => k !== OTHER_OPTION_VALUE).map(([, v]) => v))).toEqual(new Set([18.2]));
  });
});
