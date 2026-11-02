import type { QuestionRuleConfig } from '@/types/campaign';
import type { ParsedFormStructure, ParsedQuestion } from '@/types/form';

import { isBranching } from './questions';

/** Ước tính các đường đi qua trang và tỷ lệ của từng đường (giống luật PageNavigator ở backend). */
export interface BranchPath {
  pages: number[];
  label: string;
  probability: number;
}

const NEXT = -2;
const SUBMIT = -3;
const MAX_PATHS = 20;

function optionProbabilities(question: ParsedQuestion, rule: QuestionRuleConfig | undefined): number[] {
  const weights = question.options.map((o) => {
    if (rule?.weights && Object.keys(rule.weights).length > 0) return Math.max(rule.weights[o.value] ?? 0, 0);
    return o.is_other ? 0 : 1;
  });
  const total = weights.reduce((s, w) => s + w, 0);
  return total > 0 ? weights.map((w) => w / total) : weights;
}

function sectionTarget(structure: ParsedFormStructure, page: number, code: number | null): number | 'submit' {
  if (code === SUBMIT) return 'submit';
  if (code !== null && code > 0) {
    const target = structure.sections.find((s) => s.section_item_id === code);
    if (target) return target.page_index;
  }
  return page + 1;
}

function defaultNext(structure: ParsedFormStructure, page: number): number | 'submit' {
  const section = structure.sections.find((s) => s.page_index === page);
  if (!section) return page + 1;
  if (section.navigation_action === 'SUBMIT') return 'submit';
  if (section.navigation_action === 'GO_TO_PAGE') return sectionTarget(structure, page, section.jump_to_section_id);
  return page + 1;
}

export function estimateBranchPaths(
  structure: ParsedFormStructure,
  rules: Record<string, QuestionRuleConfig>,
): BranchPath[] {
  const branching = new Map<number, ParsedQuestion>();
  for (const q of structure.questions) if (isBranching(q)) branching.set(q.page_index, q); // câu rẽ nhánh cuối trang

  const finished: { pages: number[]; probability: number }[] = [];
  const walk = (pages: number[], probability: number): void => {
    if (finished.length >= MAX_PATHS || probability <= 0) return;
    const page = pages[pages.length - 1] ?? 0;
    const question = branching.get(page);
    const moves: { next: number | 'submit'; p: number }[] = [];
    if (question) {
      optionProbabilities(question, rules[question.entry_id]).forEach((p, i) => {
        const jump = question.options[i]?.jump_to_section_id ?? null;
        const next = jump === null || jump === NEXT || jump === -1 ? defaultNext(structure, page) : sectionTarget(structure, page, jump);
        moves.push({ next, p });
      });
    } else {
      moves.push({ next: defaultNext(structure, page), p: 1 });
    }
    for (const move of moves) {
      const done = move.next === 'submit' || move.next >= structure.total_pages || pages.includes(move.next);
      if (done) finished.push({ pages, probability: probability * move.p });
      else walk([...pages, move.next as number], probability * move.p);
    }
  };
  walk([0], 1);

  const merged = new Map<string, { pages: number[]; probability: number }>();
  for (const path of finished) {
    const key = path.pages.join(',');
    const existing = merged.get(key);
    merged.set(key, { pages: path.pages, probability: (existing?.probability ?? 0) + path.probability });
  }
  const titleOf = (page: number) => {
    const title = structure.sections.find((s) => s.page_index === page)?.title ?? `Trang ${page + 1}`;
    return /^[A-Z]\./.test(title) ? title.slice(0, 1) : `Trang ${page + 1}`;
  };
  return [...merged.values()]
    .filter((p) => p.probability > 0.0005)
    .sort((a, b) => b.probability - a.probability)
    .map((p) => ({
      pages: p.pages,
      probability: p.probability,
      label: p.pages.filter((page) => (structure.questions.some((q) => q.page_index === page))).map(titleOf).join(' → '),
    }));
}
