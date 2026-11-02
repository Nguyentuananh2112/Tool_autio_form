import { useId, useState } from 'react';

import { FeatureCard } from '@/components/help/FeatureCard';
import { FAQS, FEATURES, TERMS } from '@/components/help/helpContent';
import { PageHeader } from '@/components/layout/PageHeader';
import { useTour } from '@/components/tour/TourProvider';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { TextInput } from '@/components/ui/Field';

const normalize = (text: string) => text.normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/đ/g, 'd').toLowerCase();

export function HelpPage() {
  const tour = useTour();
  const searchId = useId();
  const [query, setQuery] = useState('');
  const q = normalize(query.trim());
  const match = (...parts: string[]) => !q || normalize(parts.join(' ')).includes(q);
  const features = FEATURES.filter((f) => match(f.title, f.when, f.how, f.keywords));
  const terms = TERMS.filter((t) => match(t.term, t.text));
  const faqs = FAQS.filter((f) => match(f.q, f.a));

  return (
    <>
      <PageHeader
        title="Hướng dẫn"
        description="Mỗi tính năng: dùng khi nào và làm thế nào."
        actions={<Button variant="primary" onClick={tour.start}>Bắt đầu tour hướng dẫn</Button>}
      />
      <div className="flex flex-col gap-1.5">
        <label htmlFor={searchId} className="text-[13px] font-medium text-muted">Tìm trong hướng dẫn</label>
        <TextInput id={searchId} type="search" value={query} placeholder="VD: rẽ nhánh, Alpha, Excel, tạm dừng…" onChange={(e) => setQuery(e.target.value)} className="min-h-12 text-[15px]" />
      </div>
      {features.length > 0 && (
        <section aria-labelledby="features-title" className="flex flex-col gap-3.5">
          <h2 id="features-title" className="m-0 text-lg font-semibold">Tính năng</h2>
          <div className="grid grid-cols-[repeat(auto-fill,minmax(300px,1fr))] gap-3.5">
            {features.map((f) => <FeatureCard key={f.title} feature={f} />)}
          </div>
        </section>
      )}
      {terms.length > 0 && (
        <Card aria-labelledby="terms-title" className="flex flex-col gap-3 p-5">
          <h2 id="terms-title" className="m-0 text-lg font-semibold">Giải thích thuật ngữ</h2>
          <dl className="m-0 grid grid-cols-[minmax(140px,220px)_minmax(0,1fr)] gap-x-5 gap-y-2.5 text-sm">
            {terms.map((t) => (
              <div key={t.term} className="contents">
                <dt className="font-semibold">{t.term}</dt>
                <dd className="m-0 text-muted">{t.text}</dd>
              </div>
            ))}
          </dl>
        </Card>
      )}
      {faqs.length > 0 && (
        <section aria-labelledby="faq-title" className="flex flex-col gap-2.5">
          <h2 id="faq-title" className="m-0 text-lg font-semibold">Câu hỏi thường gặp</h2>
          {faqs.map((f) => (
            <details key={f.q} className="rounded-xl border border-line bg-surface px-4.5 py-3.5">
              <summary className="min-h-7 cursor-pointer text-[15px] font-semibold">{f.q}</summary>
              <p className="mb-0 mt-2.5 text-sm leading-relaxed text-muted">{f.a}</p>
            </details>
          ))}
        </section>
      )}
      {!features.length && !terms.length && !faqs.length && <p className="m-0 text-sm text-muted">Không tìm thấy nội dung khớp “{query}”.</p>}
    </>
  );
}
