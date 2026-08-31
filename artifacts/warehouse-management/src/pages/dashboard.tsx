import { useEffect } from 'react';
import { Link, useLocation } from 'wouter';
import { ArrowLeft, CheckCircle2, CircleUserRound, Database, ShieldCheck, UsersRound, Wifi } from 'lucide-react';
import { getHealthCheckQueryKey, useGetDashboardSummary, useHealthCheck } from '@workspace/api-client-react';
import type { SessionUser } from '@workspace/api-client-react';
import { getGetDashboardSummaryQueryKey } from '@workspace/api-client-react';
import { ErrorState, LoadingRows } from '@/components/ui';

function StatCard({ label, value, note, icon: Icon, accent }: { label: string; value: number | undefined; note: string; icon: typeof UsersRound; accent: 'amber' | 'green' | 'petrol' | 'red' }) {
  const colors = {
    amber: 'bg-primary/10 text-primary',
    green: 'bg-accent/10 text-accent',
    petrol: 'bg-sidebar/10 text-sidebar',
    red: 'bg-destructive/10 text-destructive',
  };
  return (
    <div className="group relative overflow-hidden rounded-lg border border-border bg-card p-5 transition-[transform,box-shadow] duration-300 hover:-translate-y-0.5 hover:shadow-md">
      <div className="mb-8 flex items-start justify-between">
        <span className={`flex h-10 w-10 items-center justify-center rounded-md ${colors[accent]}`}><Icon className="h-5 w-5" /></span>
        <span className="font-mono text-[10px] text-muted-foreground">LIVE</span>
      </div>
      <p className="text-sm text-muted-foreground">{label}</p>
      <p className="mt-1 text-4xl font-bold tracking-tight text-foreground">{value === undefined ? '—' : value}</p>
      <p className="mt-2 text-xs text-muted-foreground">{note}</p>
      <span className="absolute bottom-0 right-0 h-1 w-full bg-gradient-to-l from-primary/50 to-transparent opacity-0 transition-opacity group-hover:opacity-100" />
    </div>
  );
}

export default function DashboardPage({ user }: { user: SessionUser }) {
  const [, setLocation] = useLocation();
  const summary = useGetDashboardSummary({ request: { credentials: 'include' }, query: { queryKey: getGetDashboardSummaryQueryKey() } });
  const health = useHealthCheck({ request: { credentials: 'include' }, query: { queryKey: getHealthCheckQueryKey() } });
  const canReadUsers = user.permissions.includes('users:read');
  useEffect(() => {
    if ((summary.error as { status?: number } | null)?.status === 401) setLocation('/login');
  }, [summary.error, setLocation]);

  return (
    <div className="space-y-8">
      <header className="flex flex-col justify-between gap-5 border-b border-border pb-7 sm:flex-row sm:items-end">
        <div>
          <p className="mb-3 font-mono text-[10px] tracking-[0.18em] text-primary">لوحة التشغيل / 00</p>
          <h1 className="text-3xl font-bold tracking-tight text-foreground sm:text-4xl">صباح الخير، {user.display_name.split(' ')[0]}</h1>
          <p className="mt-2 text-sm text-muted-foreground">هذه صورة سريعة عن مساحة المخزن اليوم.</p>
        </div>
        <div className="flex items-center gap-2 rounded-full border border-accent/20 bg-accent/8 px-3 py-2 text-xs font-semibold text-accent" data-testid="status-system">
          <Wifi className="h-3.5 w-3.5" />
          {health.isLoading ? 'جارٍ فحص الاتصال' : health.isError ? 'الاتصال يحتاج مراجعة' : 'النظام متصل'}
        </div>
      </header>
      {summary.isError ? (
        <div className="rounded-lg border border-border bg-card"><ErrorState onRetry={() => summary.refetch()} /></div>
      ) : summary.isLoading ? (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <div className="h-48 animate-pulse rounded-lg bg-muted" /><div className="h-48 animate-pulse rounded-lg bg-muted" /><div className="h-48 animate-pulse rounded-lg bg-muted" /><div className="h-48 animate-pulse rounded-lg bg-muted" />
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <StatCard label="إجمالي المستخدمين" value={summary.data?.users_total} note="حسابات مسجلة في النظام" icon={UsersRound} accent="amber" />
          <StatCard label="المستخدمون النشطون" value={summary.data?.active_users} note="لديهم وصول فعّال الآن" icon={CircleUserRound} accent="green" />
          <StatCard label="الأدوار المعتمدة" value={summary.data?.roles_total} note="مجموعات وصول منظمة" icon={ShieldCheck} accent="petrol" />
          <StatCard label="الصلاحيات المتاحة" value={summary.data?.permissions_total} note="صلاحيات قابلة للإسناد" icon={Database} accent="red" />
        </div>
      )}
      <div className="grid gap-5 lg:grid-cols-[1.25fr_0.75fr]">
        <section className="rounded-lg border border-border bg-card">
          <div className="flex items-center justify-between border-b border-border px-5 py-5">
            <div><p className="font-mono text-[10px] tracking-[0.16em] text-primary">وصول سريع</p><h2 className="mt-1 text-lg font-bold">أدوات الفريق</h2></div>
            <span className="font-mono text-xs text-muted-foreground">02</span>
          </div>
          <div className="grid gap-px bg-border sm:grid-cols-2">
            {canReadUsers && (
              <Link href="/users" data-testid="link-dashboard-users" className="group bg-card p-5 transition-colors hover:bg-secondary">
                <div className="mb-9 flex items-center justify-between"><UsersRound className="h-5 w-5 text-primary" /><ArrowLeft className="h-4 w-4 text-muted-foreground transition-transform group-hover:-translate-x-1" /></div>
                <h3 className="font-bold">إدارة المستخدمين</h3><p className="mt-1 text-sm text-muted-foreground">أنشئ الحسابات وعدّل أدوار الفريق.</p>
              </Link>
            )}
            <Link href="/roles" data-testid="link-dashboard-roles" className="group bg-card p-5 transition-colors hover:bg-secondary">
              <div className="mb-9 flex items-center justify-between"><ShieldCheck className="h-5 w-5 text-accent" /><ArrowLeft className="h-4 w-4 text-muted-foreground transition-transform group-hover:-translate-x-1" /></div>
              <h3 className="font-bold">الأدوار والصلاحيات</h3><p className="mt-1 text-sm text-muted-foreground">راجع خريطة الوصول المعتمدة.</p>
            </Link>
          </div>
        </section>
        <section className="rounded-lg border border-border bg-sidebar p-5 text-sidebar-foreground">
          <div className="flex items-center justify-between"><p className="font-mono text-[10px] tracking-[0.16em] text-sidebar-primary">حالة الخدمة</p><CheckCircle2 className="h-5 w-5 text-sidebar-primary" /></div>
          <h2 className="mt-10 text-xl font-bold">كل شيء يعمل كما ينبغي.</h2>
          <div className="mt-8 space-y-4 border-t border-sidebar-border pt-4 text-sm">
            <div className="flex items-center justify-between"><span className="text-sidebar-foreground/60">جلسة المستخدم</span><span className="font-semibold text-sidebar-primary">مفعّلة</span></div>
            <div className="flex items-center justify-between"><span className="text-sidebar-foreground/60">صلاحية الحساب</span><span className="font-semibold text-sidebar-primary">{user.is_active ? 'نشط' : 'موقوف'}</span></div>
            <div className="flex items-center justify-between"><span className="text-sidebar-foreground/60">معرّف الجلسة</span><span className="font-mono text-xs text-sidebar-foreground/60">#{String(user.id).padStart(4, '0')}</span></div>
          </div>
        </section>
      </div>
      {summary.isFetching && !summary.isLoading && <div className="sr-only"><LoadingRows count={1} /></div>}
    </div>
  );
}