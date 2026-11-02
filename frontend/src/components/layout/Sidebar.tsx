import { Activity, HelpCircle, LayoutGrid, Settings, SlidersHorizontal, type LucideIcon } from 'lucide-react';
import { NavLink } from 'react-router-dom';

import { Button } from '@/components/ui/Button';
import { useUpdaterContext } from '@/components/update/UpdaterProvider';
import { cn } from '@/lib/cn';

interface NavItem {
  to: string;
  label: string;
  Icon: LucideIcon;
  end?: boolean;
}

const MAIN_ITEMS: NavItem[] = [
  { to: '/', label: 'Tổng quan', Icon: LayoutGrid, end: true },
  { to: '/forms', label: 'Cấu hình khảo sát', Icon: SlidersHorizontal },
  { to: '/campaigns', label: 'Chiến dịch', Icon: Activity },
];

const linkClass = ({ isActive }: { isActive: boolean }) =>
  cn(
    'flex min-h-11 items-center gap-3 rounded-[10px] px-3 text-sm no-underline',
    isActive ? 'bg-accent-soft font-semibold text-accent' : 'font-medium text-muted hover:bg-sunken hover:text-ink',
  );

function NavItemLink({ item }: { item: NavItem }) {
  return (
    <NavLink to={item.to} end={item.end} className={linkClass}>
      <item.Icon aria-hidden className="size-5" strokeWidth={1.8} />
      <span>{item.label}</span>
    </NavLink>
  );
}

export function Sidebar({ version }: { version: string | null }) {
  const updater = useUpdaterContext();
  return (
    <nav aria-label="Điều hướng chính" className="flex w-full flex-col gap-7 border-b border-line bg-surface px-3.5 py-5 md:sticky md:top-0 md:h-screen md:w-62 md:shrink-0 md:border-r md:border-b-0">
      <div className="flex items-center gap-2.5 px-2">
        <svg width="32" height="32" viewBox="0 0 32 32" aria-hidden>
          <rect x="1" y="1" width="30" height="30" rx="8" className="fill-accent" />
          <path d="M9 11h14M9 16h10M9 21h6" className="stroke-accent-ink" strokeWidth="2.4" strokeLinecap="round" />
        </svg>
        <div className="flex flex-col">
          <span className="text-base font-bold">Auto-Form</span>
          <span className="text-xs text-muted">Trợ lý khảo sát</span>
        </div>
      </div>
      <div data-tour="nav" className="flex flex-col gap-1">
        {MAIN_ITEMS.map((item) => <NavItemLink key={item.to} item={item} />)}
      </div>
      <div className="flex flex-col gap-1">
        <div data-tour="help"><NavItemLink item={{ to: '/help', label: 'Hướng dẫn', Icon: HelpCircle }} /></div>
        <NavItemLink item={{ to: '/settings', label: 'Cài đặt', Icon: Settings }} />
      </div>
      <div className="mt-auto flex flex-col gap-3">
        {updater.phase === 'available' && updater.info && (
          <div className="flex flex-col gap-2.5 rounded-xl bg-accent-soft p-3.5">
            <strong className="flex items-center gap-2 text-[13px]"><span aria-hidden className="size-2 rounded-full bg-accent" />Có bản cập nhật {updater.info.version}</strong>
            <Button variant="primary" size="sm" onClick={updater.openDialog}>Cập nhật</Button>
          </div>
        )}
        {version && <span className="px-2 text-xs text-muted">Phiên bản {version}</span>}
      </div>
    </nav>
  );
}
