import { forwardRef, type ButtonHTMLAttributes } from 'react';

import { cn } from '@/lib/cn';

export type ButtonVariant = 'primary' | 'secondary' | 'quiet' | 'danger' | 'dark';
export type ButtonSize = 'md' | 'sm' | 'lg';

const VARIANTS: Record<ButtonVariant, string> = {
  primary: 'bg-accent text-accent-ink hover:bg-accent-hover border border-transparent',
  secondary: 'bg-surface text-ink border border-line hover:bg-sunken',
  quiet: 'bg-transparent text-accent border border-transparent hover:bg-accent-soft',
  danger: 'bg-transparent text-bad border border-bad hover:bg-bad-soft',
  dark: 'bg-ink text-surface border border-transparent hover:opacity-90',
};

const SIZES: Record<ButtonSize, string> = {
  sm: 'min-h-9 px-3 text-[13px] rounded-lg',
  md: 'min-h-11 px-4 text-sm rounded-[10px]',
  lg: 'min-h-12 px-5 text-[15px] rounded-[10px]',
};

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant = 'secondary', size = 'md', loading = false, className, children, disabled, type = 'button', ...rest },
  ref,
) {
  return (
    <button
      ref={ref}
      type={type}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      className={cn(
        'inline-flex items-center justify-center gap-2 font-semibold transition-colors cursor-pointer',
        'disabled:cursor-not-allowed disabled:opacity-100 disabled:bg-sunken disabled:text-muted disabled:border-transparent',
        VARIANTS[variant],
        SIZES[size],
        className,
      )}
      {...rest}
    >
      {loading && <span aria-hidden className="size-4 animate-spin rounded-full border-2 border-current border-r-transparent" />}
      {children}
    </button>
  );
});
