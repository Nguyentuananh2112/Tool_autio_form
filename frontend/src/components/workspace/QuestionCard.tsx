import { isDateOrTime, isText } from '@/lib/questions';
import type { ParsedFormStructure, ParsedQuestion } from '@/types/form';

import { CheckboxQuestionCard } from './question-cards/CheckboxQuestionCard';
import { ChoiceQuestionCard } from './question-cards/ChoiceQuestionCard';
import { DateTimeQuestionCard } from './question-cards/DateTimeQuestionCard';
import { TextQuestionCard } from './question-cards/TextQuestionCard';

/** Chọn thẻ phù hợp với loại câu hỏi. */
export function QuestionCard({ formId, structure, question, tourId }: {
  formId: string;
  structure: ParsedFormStructure;
  question: ParsedQuestion;
  tourId?: string;
}) {
  if (isText(question)) return <TextQuestionCard formId={formId} formTitle={structure.title} question={question} tourId={tourId} />;
  if (isDateOrTime(question)) return <DateTimeQuestionCard formId={formId} question={question} />;
  if (question.is_multi_select) return <CheckboxQuestionCard formId={formId} question={question} />;
  return <ChoiceQuestionCard formId={formId} structure={structure} question={question} tourId={tourId} />;
}
