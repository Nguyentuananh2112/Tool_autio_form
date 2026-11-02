import { forwardRef, useId, type InputHTMLAttributes, type ReactNode, type SelectHTMLAttributes, type TextareaHTMLAttributes } from 'react';

import { cn } from '@/lib/cn';

const CONTROL = 'w-full box-border rounded-[10px] border border-line bg-bg px-3 text-ink text-sm placeholder:text-muted';

export function Field({ label, hint, error, children, htmlFor }: {
  label: ReactNode;
  hint?: ReactNode;
  error?: ReactNode;
  htmlFor: string;
  children: ReactNode;
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={htmlFor} className="text-[13px] font-medium text-muted">{label}</label>
      {children}
      {error ? <span className="text-[13px] text-bad">{error}</span> : hint && <span className="text-xs text-muted">{hint}</span>}
    </div>
  );
}

export const TextInput = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement> & { invalid?: boolean }>(
  function TextInput({ className, invalid, ...rest }, ref) {
    return (
      <input
        ref={ref}
        aria-invalid={invalid || undefined}
        className={cn(CONTROL, 'min-h-11', invalid && 'border-2 border-bad', className)}
        {...rest}
      />
    );
  },
);

export function TextArea({ className, ...rest }: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return <textarea className={cn(CONTROL, 'py-2.5 resize-y', className)} {...rest} />;
}

export function Select({ className, children, ...rest }: SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select className={cn(CONTROL, 'min-h-11', className)} {...rest}>
      {children}
    </select>
  );
}

/** Ô nhập có nhãn sẵn — dùng cho trường hợp đơn giản. */
export function LabeledInput({ label, hint, ...rest }: InputHTMLAttributes<HTMLInputElement> & { label: string; hint?: string }) {
  const id = useId();
  return (
    <Field label={label} hint={hint} htmlFor={id}>
      <TextInput id={id} {...rest} />
    </Field>
  );
}
