import { ArrowRight, Box } from 'lucide-react';
import { Link } from 'wouter';

export default function NotFound() {
  return (
    <div className="flex min-h-[100dvh] items-center justify-center bg-background px-5" dir="rtl">
      <div className="w-full max-w-md text-center">
        <div className="mx-auto mb-6 flex h-14 w-14 items-center justify-center rounded-md bg-primary text-primary-foreground"><Box className="h-6 w-6" /></div>
        <p className="font-mono text-xs tracking-[0.2em] text-primary">404 / غير موجود</p>
        <h1 className="mt-3 text-3xl font-bold text-foreground">هذه الصفحة ليست في المخزن.</h1>
        <p className="mt-3 text-sm leading-6 text-muted-foreground">تحقق من العنوان أو عد إلى لوحة التشغيل للمتابعة.</p>
        <Link href="/dashboard" data-testid="link-not-found-dashboard" className="mt-7 inline-flex items-center gap-2 rounded-md border border-border bg-card px-4 py-3 text-sm font-semibold text-foreground transition-colors hover:bg-secondary"><ArrowRight className="h-4 w-4" /> العودة للرئيسية</Link>
      </div>
    </div>
  );
}
