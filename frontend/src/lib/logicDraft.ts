/**
 * Thao tác thuần (không đổi dữ liệu gốc) để người dùng sửa bản đồ logic trên màn Soát logic.
 * Mọi thay đổi làm mất trạng thái "đã xác nhận": phải soát lại trước khi chạy.
 */
import type { ParsedQuestion } from '@/types/form';
import type { AttitudeGroup, Consistency, LogicMap, LogicRule } from '@/types/logic';

function edited(logic: LogicMap, patch: Partial<LogicMap>): LogicMap {
  return { ...logic, ...patch, confirmed: false };
}

function mapGroup(logic: LogicMap, groupId: string, update: (group: AttitudeGroup) => AttitudeGroup | null): LogicMap {
  const groups = logic.attitude_groups.flatMap((group) => {
    if (group.group_id !== groupId) return [group];
    const next = update(group);
    return next && next.items.length > 0 ? [next] : [];
  });
  const alive = new Set(groups.map((g) => g.group_id));
  return edited(logic, { attitude_groups: groups, text_attitudes: logic.text_attitudes.filter((t) => alive.has(t.group_id)) });
}

export function toggleDirection(logic: LogicMap, groupId: string, entryId: string): LogicMap {
  return mapGroup(logic, groupId, (group) => ({
    ...group,
    items: group.items.map((item) => (item.entry_id === entryId ? { ...item, positive_high: !item.positive_high } : item)),
  }));
}

export function removeFromGroup(logic: LogicMap, groupId: string, entryId: string): LogicMap {
  return mapGroup(logic, groupId, (group) => ({ ...group, items: group.items.filter((item) => item.entry_id !== entryId) }));
}

export function addToGroup(logic: LogicMap, groupId: string, entryId: string, positiveHigh = true): LogicMap {
  const without = logic.attitude_groups.map((group) => ({ ...group, items: group.items.filter((i) => i.entry_id !== entryId) }));
  return mapGroup({ ...logic, attitude_groups: without }, groupId, (group) => ({
    ...group,
    items: [...group.items, { entry_id: entryId, positive_high: positiveHigh }],
  }));
}

export function addGroup(logic: LogicMap, name: string, firstEntryId: string): LogicMap {
  const used = new Set(logic.attitude_groups.map((g) => g.group_id));
  let index = logic.attitude_groups.length + 1;
  while (used.has(`g${index}`)) index += 1;
  const group: AttitudeGroup = { group_id: `g${index}`, name: name.trim() || `Nhóm ${index}`, items: [] };
  const withGroup = { ...logic, attitude_groups: [...logic.attitude_groups, group] };
  return addToGroup(withGroup, group.group_id, firstEntryId);
}

export function upsertRule(logic: LogicMap, rule: LogicRule): LogicMap {
  const exists = logic.rules.some((r) => r.rule_id === rule.rule_id);
  return edited(logic, { rules: exists ? logic.rules.map((r) => (r.rule_id === rule.rule_id ? rule : r)) : [...logic.rules, rule] });
}

export function removeRule(logic: LogicMap, ruleId: string): LogicMap {
  return edited(logic, { rules: logic.rules.filter((r) => r.rule_id !== ruleId) });
}

export function nextRuleId(logic: LogicMap): string {
  const used = new Set(logic.rules.map((r) => r.rule_id));
  let index = logic.rules.length + 1;
  while (used.has(`r${index}`)) index += 1;
  return `r${index}`;
}

export function toggleExclusive(logic: LogicMap, entryId: string, value: string): LogicMap {
  const has = logic.exclusive_options.some((o) => o.entry_id === entryId && o.value === value);
  return edited(logic, {
    exclusive_options: has
      ? logic.exclusive_options.filter((o) => !(o.entry_id === entryId && o.value === value))
      : [...logic.exclusive_options, { entry_id: entryId, value }],
  });
}

export function setConsistency(logic: LogicMap, consistency: Consistency): LogicMap {
  return edited(logic, { consistency });
}

/** Câu có thể đưa vào nhóm thái độ: chọn một, ≥ 2 đáp án thường, chưa thuộc nhóm nào. */
export function attitudeCandidates(questions: ParsedQuestion[], logic: LogicMap): ParsedQuestion[] {
  const used = new Set(logic.attitude_groups.flatMap((g) => g.items.map((i) => i.entry_id)));
  return questions.filter((q) => !q.is_multi_select && q.options.filter((o) => !o.is_other).length >= 2 && !used.has(q.entry_id));
}

/** Câu dùng được trong ràng buộc NẾU…THÌ: có lựa chọn. */
export function ruleCandidates(questions: ParsedQuestion[]): ParsedQuestion[] {
  return questions.filter((q) => q.options.length > 0);
}
