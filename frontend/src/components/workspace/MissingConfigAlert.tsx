import { useState } from 'react';

import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { useGeminiPool } from '@/hooks/useGeminiPool';
import type { Readiness } from '@/lib/readiness';
import { isText } from '@/lib/questions';
import { useFormConfigStore } from '@/store/formConfigStore';
import type { ParsedFormStructure } from '@/types/form';

/** Cảnh báo câu còn thiếu + nút sinh tất cả câu tự luận bằng Gemini một lượt. */
export function MissingConfigAlert({ formId, structure, readiness }: {
  formId: string;
  structure: ParsedFormStructure;
  readiness: Readiness;
}) {
  const updateRule = useFormConfigStore((s) => s.updateRule);
  const { busy, error, generate } = useGeminiPool();
  const [progress, setProgress] = useState<string | null>(null);
  if (readiness.issues.length === 0) return null;

  const missingText = structure.questions.filter(
    (q) => isText(q) && readiness.issues.some((issue) => issue.entryId === q.entry_id),
  );

  const generateAll = async () => {
    for (const [index, question] of missingText.entries()) {
      setProgress(`Đang sinh ${index + 1} / ${missingText.length}…`);
      const answers = await generate(question.title, structure.title);
      if (!answers) break;
      updateRule(formId, { entry_id: question.entry_id, question_type: question.type_id, text_pool: answers, ai_context: structure.title });
    }
    setProgress(null);
  };

  return (
    <Alert
      tone="warn"
      title={`${readiness.issues.length} câu chưa cấu hình xong`}
      action={missingText.length > 0 && (
        <Button size="sm" onClick={() => void generateAll()} loading={busy}>{progress ?? `Sinh ${missingText.length} câu tự luận bằng Gemini`}</Button>
      )}
    >
      Cần bổ sung trước khi chạy. Các câu có viền cam là câu còn thiếu.
      {error && <div className="mt-1 text-bad">{error.message}</div>}
    </Alert>
  );
}
