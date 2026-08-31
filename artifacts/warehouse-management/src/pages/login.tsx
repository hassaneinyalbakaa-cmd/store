import { useEffect, useState, type FormEvent } from 'react';
import { useLocation } from 'wouter';
import { ArrowLeft, Box, LockKeyhole, UserRound } from 'lucide-react';
import { useGetCurrentUser, useLogin } from '@workspace/api-client-react';
import { getGetCurrentUserQueryKey } from '@workspace/api-client-react';
import { useQueryClient } from '@tanstack/react-query';
import { Button, Field, Notice } from '@/components/ui';

function getErrorMessage(error: unknown, fallback: string) {
  const typedError = error as { status?: number; detail?: string; response?: { data?: { detail?: string } } };
  if (typedError?.status === 401) return 'اسم المستخدم أو كلمة المرور غير صحيحة.';
  return typedError?.detail || typedError?.response?.data?.detail || fallback;
}

export default function LoginPage() {
  const [, setLocation] = useLocation();
  const queryClient = useQueryClient();
  const currentUser = useGetCurrentUser({
    request: { credentials: 'include' },
    query: { retry: false, queryKey: getGetCurrentUserQueryKey() },
  });
  const login = useLogin({ request: { credentials: 'include' } });
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [formError, setFormError] = useState('');

  useEffect(() => {
    if (currentUser.data) setLocation('/dashboard');
  }, [currentUser.data, setLocation]);

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setFormError('');
    login.mutate(
      { data: { username: username.trim(), password } },
      {
        onSuccess: (user) => {
          queryClient.setQueryData(getGetCurrentUserQueryKey(), user);
          setLocation('/dashboard');
        },
        onError: (error) => setFormError(getErrorMessage(error, 'تعذر إتمام تسجيل الدخول. حاول مرة أخرى.')),
      },
    );
  };

  return (
    <div className="min-h-[100dvh] bg-background" dir="rtl">
      <div className="grid min-h-[100dvh] lg:grid-cols-[1fr_0.95fr]">
        <section className="relative hidden overflow-hidden bg-sidebar p-12 text-sidebar-foreground lg:flex lg:flex-col lg:justify-between">
          <div className="absolute -left-24 top-20 h-72 w-72 rounded-full border border-sidebar-primary/20" />
          <div className="absolute -left-12 top-32 h-48 w-48 rounded-full border border-sidebar-primary/15" />
          <div className="relative flex items-center gap-3">
            <span className="flex h-11 w-11 items-center justify-center rounded-md bg-sidebar-primary text-sidebar-primary-foreground">
              <Box className="h-5 w-5" strokeWidth={2.5} />
            </span>
            <div>
              <p className="font-bold">نظام إدارة المخزن</p>
              <p className="font-mono text-[9px] tracking-[0.18em] text-sidebar-foreground/50">WAREHOUSE / LOCAL</p>
            </div>
          </div>
          <div className="relative max-w-md pb-10">
            <p className="mb-5 font-mono text-xs tracking-[0.2em] text-sidebar-primary">01 / وصول الفريق</p>
            <h1 className="text-5xl font-bold leading-[1.2] tracking-tight">المخزن واضح.<br />العمل أسرع.</h1>
            <p className="mt-6 max-w-sm text-sm leading-7 text-sidebar-foreground/60">مساحة تشغيل داخلية لفريق المخزن، تجمع المستخدمين والأدوار في مكان واحد مرتب.</p>
          </div>
          <div className="relative flex items-center justify-between border-t border-sidebar-border pt-5 font-mono text-[10px] text-sidebar-foreground/40">
            <span>شبكة داخلية موثوقة</span>
            <span>v 1.0.0</span>
          </div>
        </section>
        <section className="flex items-center justify-center px-5 py-12 sm:px-10">
          <div className="w-full max-w-[430px]">
            <div className="mb-10 flex items-center gap-3 lg:hidden">
              <span className="flex h-10 w-10 items-center justify-center rounded-md bg-primary text-primary-foreground">
                <Box className="h-5 w-5" strokeWidth={2.5} />
              </span>
              <div>
                <p className="font-bold text-foreground">نظام إدارة المخزن</p>
                <p className="font-mono text-[9px] tracking-[0.18em] text-muted-foreground">WAREHOUSE / LOCAL</p>
              </div>
            </div>
            <div className="mb-9">
              <p className="mb-3 font-mono text-[10px] tracking-[0.18em] text-primary">تسجيل الدخول / 01</p>
              <h2 className="text-3xl font-bold tracking-tight text-foreground">مرحباً بعودتك</h2>
              <p className="mt-3 text-sm leading-6 text-muted-foreground">أدخل بيانات حسابك للوصول إلى مساحة الفريق.</p>
            </div>
            <form onSubmit={submit} className="space-y-5">
              {formError && <Notice>{formError}</Notice>}
               <Field label="اسم المستخدم" name="username" value={username} onChange={setUsername} placeholder="مثال: ahmed.warehouse" autoComplete="username" required />
               <Field label="كلمة المرور" name="password" type="password" value={password} onChange={setPassword} placeholder="أدخل كلمة المرور" autoComplete="current-password" required />
              <Button type="submit" testId="button-login" className="mt-3 w-full" disabled={login.isPending || !username || !password}>
                {login.isPending ? 'جارٍ التحقق...' : <>دخول إلى النظام <ArrowLeft className="h-4 w-4" /></>}
              </Button>
            </form>
            <div className="mt-9 grid grid-cols-2 gap-3">
              <div className="rounded-md border border-border bg-card p-3">
                <UserRound className="mb-3 h-4 w-4 text-accent" />
                <p className="text-xs font-semibold text-foreground">حساب داخلي</p>
                <p className="mt-1 text-[11px] text-muted-foreground">لأعضاء فريق المخزن</p>
              </div>
              <div className="rounded-md border border-border bg-card p-3">
                <LockKeyhole className="mb-3 h-4 w-4 text-primary" />
                <p className="text-xs font-semibold text-foreground">وصول محمي</p>
                <p className="mt-1 text-[11px] text-muted-foreground">ضمن الشبكة المحلية</p>
              </div>
            </div>
            <p className="mt-10 text-center font-mono text-[10px] tracking-wide text-muted-foreground">إذا واجهت مشكلة، تواصل مع مسؤول النظام</p>
          </div>
        </section>
      </div>
    </div>
  );
}