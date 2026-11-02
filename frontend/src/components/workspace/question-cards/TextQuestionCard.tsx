import { Sparkles } from 'lucide-react';
import { useId, useState } from 'react';
import { Link } from 'react-router-dom';

import { Alert } from '@/components/ui/Alert';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Field, Select, TextArea } from '@/components/ui/Field';
import { useGeminiPool, POOL_SIZE } from '@/hooks/useGeminiPool';
import { useQuestionRule } from '@/hooks/useQuestionRule';
import type { ParsedQuestion } from '@/types/form';

import { LinesEditor } from '../weights/LinesEditor';
import { QuestionCardFrame } from './QuestionCardFrame';

const PERSONAS = ['Sinh viên đại học tại Việt Nam, 18–25 tuổi', 'Nhân viên văn phòng', 'Người làm tự do', 'Người lớn tuổi, viết ngắn gọn'];

/** Câu tự luận: pool câu trả lời mẫu (Gemini hoặc tự dán). */
export function TextQuestionCard({ formId, formTitle, question, tourId }: {
  formId: string;
  formTitle: string;
  question: ParsedQuestion;
  tourId?: string;
}) {
  const { rule, update } = useQuestionRule(formId, question);
  const { busy, error, generate } = useGeminiPool();
  const contextId = useId();
  const personaId = useId();
  const [context, setContext] = useState(rule?.ai_context ?? formTitle);
  const [persona, setPersona] = useState(rule?.ai_persona ?? PERSONAS[0] ?? '');
  const pool = rule?.text_pool ?? [];
  const missing = question.is_required && pool.length === 0;

  const runGemini = async () => {
    const answers = await generate(question.title, context, persona);
    if (answers) update({ text_pool: answers, ai_context: context, ai_persona: persona });
  };

  return (
    <QuestionCardFrame
      question={question}
      tourId={tourId}
      state={missing ? 'missing' : 'normal'}
      badges={missing ? <Badge tone="warn">Thiếu câu trả lời mẫu</Badge> : pool.length > 0 && <Badge tone="ok">{pool.length} câu mẫu</Badge>}
    >
      <div className="flex flex-wrap gap-3">
        <div className="min-w-[260px] flex-[2]">
          <Field label="Ngữ cảnh cho AI" htmlFor={contextId}>
            <TextArea id={contextId} rows={2} value={context} onChange={(e) => setContext(e.target.value)} />
          </Field>
        </div>
        <div className="min-w-[200px] flex-1">
          <Field label="Chân dung người trả lời" htmlFor={personaId}>
            <Select id={personaId} value={persona} onChange={(e) => setPersona(e.target.value)}>
              {PERSONAS.map((p) => <option key={p}>{p}</option>)}
            </Select>
          </Field>
        </div>
      </div>
      <div className="flex flex-wrap gap-2">
        <Button variant="primary" onClick={() => void runGemini()} loading={busy}><Sparkles aria-hidden className="size-4" />Sinh {POOL_SIZE} câu bằng Gemini</Button>
      </div>
      {error && (
        <Alert tone="bad" title={error.message}>
          {error.status === 400 && <Link to="/settings">Mở Cài đặt để nhập Gemini API key</Link>}
        </Alert>
      )}
      <LinesEditor label="Câu trả lời mẫu (hoặc tự dán danh sách)" value={pool} rows={pool.length > 0 ? 6 : 3} placeholder="Mỗi dòng một câu trả lời" onChange={(lines) => update({ text_pool: lines })} />
    </QuestionCardFrame>
  );
}
