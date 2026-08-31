import { type ReactNode } from 'react';
import { AlertTriangle, Check, LoaderCircle, X } from 'lucide-react';

type ButtonProps = {
  children: ReactNode;
  onClick?: () => void;
  type?: 'button' | 'submit';
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger';
  disabled?: boolean;
  className?: string;
  testId: string;
};

export function Button({
  children,
  onClick,
  type = 'button',
  variant = 'primary',
  disabled = false,
  className = '',
  testId,
}: ButtonProps) {
  const variants = {
    primary: 'bg-primary text-primary-foreground border-primary hover:brightness-95',
    secondary: 'bg-secondary text-secondary-foreground border-border hover:bg-card',
    ghost: 'bg-transparent text-muted-foreground border-transparent hover:bg-secondary hover:text-foreground',
    danger: 'bg-destructive text-destructive-foreground border-destructive hover:brightness-95',
  };
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      data-testid={testId}
      className={`inline-flex min-h-10 items-center justify-center gap-2 rounded-md border px-4 text-sm font-semibold transition-[background-color,filter,transform,opacity] duration-200 active:translate-y-px disabled:cursor-not-allowed disabled:opacity-50 ${variants[variant]} ${className}`}
    >
      {children}
    </button>
  );
}

export function Field({
  label,
  name,
  value,
  onChange,
  type = 'text',
  placeholder,
  required = false,
  hint,
  disabled = false,
}: {
  label: string;
  name: string;
  value: string;
  onChange: (value: string) => void;
  type?: string;
  placeholder?: string;
  required?: boolean;
  hint?: string;
  disabled?: boolean;
}) {
  return (
    <label className="block space-y-2 text-right">
      <span className="flex items-center justify-between text-sm font-semibold text-foreground">
        <span>{label}</span>
        {required && <span className="font-mono text-[10px] text-muted-foreground">مطلوب</span>}
      </span>
      <input
        name={name}
        type={type}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        required={required}
        disabled={disabled}
        data-testid={`input-${name}`}
        className="h-11 w-full rounded-md border border-input bg-card px-3 text-sm text-foreground outline-none transition-[border-color,box-shadow] placeholder:text-muted-foreground focus:border-primary focus:ring-2 focus:ring-primary/20 disabled:opacity-60"
      />
      {hint && <span className="block text-xs leading-5 text-muted-foreground">{hint}</span>}
    </label>
  );
}

export function SelectField({
  label,
  name,
  value,
  onChange,
  options,
  required = false,
}: {
  label: string;
  name: string;
  value: string;
  onChange: (value: string) => void;
  options: { value: string; label: string }[];
  required?: boolean;
}) {
  return (
    <label className="block space-y-2 text-right">
      <span className="flex items-center justify-between text-sm font-semibold text-foreground">
        <span>{label}</span>
        {required && <span className="font-mono text-[10px] text-muted-foreground">مطلوب</span>}
      </span>
      <select
        name={name}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        required={required}
        data-testid={`select-${name}`}
        className="h-11 w-full rounded-md border border-input bg-card px-3 text-sm text-foreground outline-none transition-[border-color,box-shadow] focus:border-primary focus:ring-2 focus:ring-primary/20"
      >
        <option value="">اختر من القائمة</option>
        {options.map((option) => (
          <option value={option.value} key={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  );
}

export function StatusPill({ active }: { active: boolean }) {
  return (
    <span
      data-testid={`status-user-${active ? 'active' : 'inactive'}`}
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold ${
        active ? 'bg-accent/10 text-accent' : 'bg-muted text-muted-foreground'
      }`}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${active ? 'bg-accent' : 'bg-muted-foreground/60'}`} />
      {active ? 'نشط' : 'موقوف'}
    </span>
  );
}

export function Modal({
  title,
  eyebrow,
  children,
  onClose,
}: {
  title: string;
  eyebrow?: string;
  children: ReactNode;
  onClose: () => void;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-foreground/40 p-4 backdrop-blur-[2px]" dir="rtl">
      <div className="max-h-[90dvh] w-full max-w-lg overflow-y-auto rounded-lg border border-border bg-card shadow-2xl motion-safe:animate-in motion-safe:fade-in motion-safe:zoom-in-95">
        <div className="flex items-start justify-between gap-5 border-b border-border px-5 py-5 sm:px-7">
          <div className="space-y-1">
            {eyebrow && <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-primary">{eyebrow}</p>}
            <h2 className="text-xl font-bold text-foreground">{title}</h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="إغلاق"
            data-testid="button-close-modal"
            className="rounded-md p-2 text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"
          >
            <X className="h-5 w-5" />
          </button>
        </div>
        <div className="px-5 py-6 sm:px-7">{children}</div>
      </div>
    </div>
  );
}

export function Notice({ children, tone = 'error' }: { children: ReactNode; tone?: 'error' | 'success' | 'info' }) {
  const styles = {
    error: 'border-destructive/25 bg-destructive/8 text-destructive',
    success: 'border-accent/25 bg-accent/8 text-accent',
    info: 'border-primary/25 bg-primary/8 text-foreground',
  };
  return (
    <div className={`flex items-start gap-2 rounded-md border px-3 py-3 text-sm leading-6 ${styles[tone]}`} role="alert">
      {tone === 'error' ? <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" /> : <Check className="mt-0.5 h-4 w-4 shrink-0" />}
      <span>{children}</span>
    </div>
  );
}

export function LoadingRows({ count = 5 }: { count?: number }) {
  return (
    <div className="space-y-3 p-4" aria-label="جاري التحميل" data-testid="loading-rows">
      {Array.from({ length: count }).map((_, index) => (
        <div className="flex animate-pulse items-center gap-4" key={index}>
          <div className="h-10 w-10 rounded-full bg-muted" />
          <div className="flex-1 space-y-2">
            <div className="h-3 w-1/3 rounded bg-muted" />
            <div className="h-2 w-1/5 rounded bg-muted" />
          </div>
          <div className="h-6 w-16 rounded-full bg-muted" />
        </div>
      ))}
    </div>
  );
}

export function EmptyState({ title, description, action }: { title: string; description: string; action?: ReactNode }) {
  return (
    <div className="flex flex-col items-center justify-center px-5 py-16 text-center" data-testid="empty-state">
      <div className="mb-5 flex h-14 w-14 items-center justify-center rounded-lg border border-dashed border-primary/50 bg-primary/8 text-primary">
        <span className="font-mono text-lg">00</span>
      </div>
      <h3 className="text-lg font-bold text-foreground">{title}</h3>
      <p className="mt-2 max-w-sm text-sm leading-6 text-muted-foreground">{description}</p>
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}

export function ErrorState({ onRetry, message = 'تعذر تحميل البيانات من الخادم المحلي.' }: { onRetry: () => void; message?: string }) {
  return (
    <div className="flex flex-col items-center justify-center px-5 py-14 text-center" data-testid="error-state">
      <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-destructive/10 text-destructive">
        <AlertTriangle className="h-5 w-5" />
      </div>
      <h3 className="text-base font-bold text-foreground">حدثت مشكلة في الاتصال</h3>
      <p className="mt-2 max-w-sm text-sm leading-6 text-muted-foreground">{message}</p>
      <Button testId="button-retry" variant="secondary" onClick={onRetry} className="mt-5">
        إعادة المحاولة
      </Button>
    </div>
  );
}

export function SavingLabel({ active }: { active: boolean }) {
  if (!active) return null;
  return (
    <span className="inline-flex items-center gap-1.5 text-xs text-muted-foreground" data-testid="status-saving">
      <LoaderCircle className="h-3.5 w-3.5 animate-spin" />
      جارٍ الحفظ
    </span>
  );
}