import { Fragment } from 'react';

import { isBranching, isSingleChoice, isText, questionsByPage } from '@/lib/questions';
import type { ParsedFormStructure, ParsedQuestion } from '@/types/form';

import { GridGroupHeader } from './GridGroupHeader';
import { QuestionCard } from './QuestionCard';

type Block = { kind: 'single'; question: ParsedQuestion } | { kind: 'grid'; rows: ParsedQuestion[] };

/** Gom các hàng liên tiếp của cùng một câu lưới thành một khối. */
function toBlocks(questions: ParsedQuestion[]): Block[] {
  const blocks: Block[] = [];
  for (const question of questions) {
    const last = blocks[blocks.length - 1];
    if (question.grid_item_id !== null && last?.kind === 'grid' && last.rows[0]?.grid_item_id === question.grid_item_id) {
      last.rows.push(question);
    } else if (question.grid_item_id !== null) {
      blocks.push({ kind: 'grid', rows: [question] });
    } else {
      blocks.push({ kind: 'single', question });
    }
  }
  return blocks;
}

/** Thẻ đầu tiên của mỗi loại được gắn mốc cho tour hướng dẫn. */
function tourTargets(structure: ParsedFormStructure): Record<string, string> {
  const pick = (test: (q: ParsedQuestion) => boolean) => structure.questions.find(test)?.entry_id;
  const targets: Record<string, string> = {};
  const weights = pick((q) => isSingleChoice(q) && !isBranching(q) && q.grid_item_id === null);
  const branch = pick(isBranching);
  const text = pick(isText);
  if (weights) targets[weights] = 'weights';
  if (branch) targets[branch] = 'branch';
  if (text) targets[text] = 'text';
  return targets;
}

export function QuestionList({ formId, structure }: { formId: string; structure: ParsedFormStructure }) {
  const pages = questionsByPage(structure);
  const targets = tourTargets(structure);
  return (
    <div className="flex min-w-0 flex-col gap-4">
      {structure.sections.map((section) => {
        const questions = pages.get(section.page_index) ?? [];
        if (questions.length === 0) return null;
        return (
          <Fragment key={section.page_index}>
            <h2 id={`page-${section.page_index}`} className="m-0 mt-1 scroll-mt-6 text-[15px] font-semibold text-muted">
              Trang {section.page_index + 1} · {section.title}
            </h2>
            {toBlocks(questions).map((block) =>
              block.kind === 'single' ? (
                <QuestionCard key={block.question.entry_id} formId={formId} structure={structure} question={block.question} tourId={targets[block.question.entry_id]} />
              ) : (
                <div key={block.rows[0]?.entry_id} className="flex flex-col gap-3">
                  <GridGroupHeader formId={formId} rows={block.rows} />
                  {block.rows.map((row) => <QuestionCard key={row.entry_id} formId={formId} structure={structure} question={row} />)}
                </div>
              ),
            )}
          </Fragment>
        );
      })}
    </div>
  );
}
