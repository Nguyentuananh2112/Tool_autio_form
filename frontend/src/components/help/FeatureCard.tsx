import { Link } from 'react-router-dom';

import type { FeatureHelp } from './helpContent';

export function FeatureCard({ feature }: { feature: FeatureHelp }) {
  return (
    <article className="flex flex-col gap-2.5 rounded-xl border border-line bg-surface px-5 py-4">
      <h3 className="m-0 text-base font-semibold">{feature.title}</h3>
      <p className="m-0 text-sm text-muted"><strong className="text-ink">Dùng khi:</strong> {feature.when}</p>
      <p className="m-0 text-sm text-muted"><strong className="text-ink">Cách làm:</strong> {feature.how}</p>
      <Link to={feature.to} className="mt-auto text-sm font-semibold text-accent no-underline">{feature.cta} →</Link>
    </article>
  );
}
