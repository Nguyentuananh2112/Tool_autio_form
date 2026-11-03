import { sampleStructure } from '@/test/fixtures';
import type { LogicMap } from '@/types/logic';

import {
  addGroup,
  addToGroup,
  attitudeCandidates,
  nextRuleId,
  removeFromGroup,
  removeRule,
  ruleCandidates,
  setConsistency,
  toggleDirection,
  toggleExclusive,
  upsertRule,
} from './logicDraft';
import { questionShortLabel, ruleLevel } from './logicLabels';

const base = (): LogicMap => ({
  version: 1,
  attitude_groups: [{ group_id: 'g1', name: 'Thái độ', items: [{ entry_id: '1', positive_high: true }, { entry_id: '4', positive_high: true }] }],
  rules: [{ rule_id: 'r1', if_entry: '1', if_values: ['Nam'], then_entry: '4', then_op: 'IS', then_values: ['Trà'], strength: 'ALWAYS' }],
  exclusive_options: [],
  text_attitudes: [{ entry_id: '5', group_id: 'g1', labels: {} }],
  consistency: 'MODERATE',
  source: 'AI',
  model: null,
  analyzed_at: null,
  confirmed: true,
});

describe('sửa bản đồ logic', () => {
  it('mọi thay đổi bỏ trạng thái đã xác nhận và không đổi bản gốc', () => {
    const logic = base();
    const next = toggleDirection(logic, 'g1', '4');
    expect(next.confirmed).toBe(false);
    expect(next.attitude_groups[0]?.items[1]?.positive_high).toBe(false);
    expect(logic.attitude_groups[0]?.items[1]?.positive_high).toBe(true);
    expect(logic.confirmed).toBe(true);
  });

  it('bỏ câu cuối cùng thì xoá nhóm và câu tự luận gắn với nhóm', () => {
    const empty = removeFromGroup(removeFromGroup(base(), 'g1', '1'), 'g1', '4');
    expect(empty.attitude_groups).toEqual([]);
    expect(empty.text_attitudes).toEqual([]);
  });

  it('thêm câu vào nhóm khác thì rời nhóm cũ (một câu chỉ thuộc một nhóm)', () => {
    const withTwo = addGroup(base(), 'Nhóm mới', '2');
    expect(withTwo.attitude_groups.map((g) => g.group_id)).toEqual(['g1', 'g2']);
    const moved = addToGroup(withTwo, 'g2', '1');
    expect(moved.attitude_groups[0]?.items.map((i) => i.entry_id)).toEqual(['4']);
    expect(moved.attitude_groups[1]?.items.map((i) => i.entry_id)).toEqual(['2', '1']);
  });

  it('thêm / sửa / xoá ràng buộc và sinh mã không trùng', () => {
    const logic = base();
    expect(nextRuleId(logic)).toBe('r2');
    const added = upsertRule(logic, { ...logic.rules[0]!, rule_id: 'r2', strength: 'USUALLY' });
    expect(added.rules).toHaveLength(2);
    const edited = upsertRule(added, { ...added.rules[0]!, then_op: 'IS_NOT' });
    expect(edited.rules[0]?.then_op).toBe('IS_NOT');
    expect(removeRule(edited, 'r1').rules.map((r) => r.rule_id)).toEqual(['r2']);
  });

  it('bật / tắt ô loại trừ và đổi độ đồng đều', () => {
    const on = toggleExclusive(base(), '3', 'Nhà');
    expect(on.exclusive_options).toEqual([{ entry_id: '3', value: 'Nhà' }]);
    expect(toggleExclusive(on, '3', 'Nhà').exclusive_options).toEqual([]);
    expect(setConsistency(base(), 'UNIFORM').consistency).toBe('UNIFORM');
  });

  it('câu được đưa vào nhóm: chọn một, ≥ 2 đáp án thường, chưa thuộc nhóm', () => {
    const questions = sampleStructure().questions;
    expect(attitudeCandidates(questions, base()).map((q) => q.entry_id)).toEqual(['2']);
    expect(ruleCandidates(questions).map((q) => q.entry_id)).toEqual(['1', '2', '3', '4']);
  });

  it('nhãn câu và mức ràng buộc', () => {
    const [first] = sampleStructure().questions;
    expect(questionShortLabel(first)).toBe('A1');
    expect(questionShortLabel(undefined)).toBe('?');
    expect(ruleLevel({ then_op: 'IS', strength: 'ALWAYS' }).label).toBe('Luôn');
    expect(ruleLevel({ then_op: 'IS_NOT', strength: 'ALWAYS' }).label).toBe('Không bao giờ');
    expect(ruleLevel({ then_op: 'IS', strength: 'USUALLY' }).label).toContain('Thường');
  });
});
