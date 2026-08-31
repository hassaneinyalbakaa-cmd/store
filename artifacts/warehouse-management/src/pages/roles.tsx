import { useEffect, useMemo, useState } from 'react';
import { Check, ChevronDown, KeyRound, ShieldCheck } from 'lucide-react';
import { useLocation } from 'wouter';
import { useListPermissions, useListRoles } from '@workspace/api-client-react';
import type { Permission, Role } from '@workspace/api-client-react';
import { ErrorState, EmptyState, LoadingRows } from '@/components/ui';

function RoleCard({ role, expanded, onToggle, permissions }: { role: Role; expanded: boolean; onToggle: () => void; permissions: Permission[] }) {
  const rolePermissions = useMemo(() => permissions.filter((permission) => role.permissions.includes(permission.code)), [permissions, role.permissions]);
  return (
    <article className={`rounded-lg border bg-card transition-[border-color,box-shadow] duration-200 ${expanded ? 'border-primary/50 shadow-sm' : 'border-border'}`} data-testid={`card-role-${role.id}`}>
      <button type="button" onClick={onToggle} data-testid={`button-toggle-role-${role.id}`} className="flex w-full items-start justify-between gap-4 p-5 text-right">
        <span className="flex min-w-0 items-start gap-3">
          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-md bg-accent/10 text-accent"><ShieldCheck className="h-5 w-5" /></span>
          <span className="min-w-0"><span className="block text-base font-bold text-foreground">{role.display_name}</span><span className="mt-1 block font-mono text-[10px] tracking-wide text-muted-foreground">{role.name}</span></span>
        </span>
        <ChevronDown className={`mt-1 h-4 w-4 shrink-0 text-muted-foreground transition-transform ${expanded ? 'rotate-180' : ''}`} />
      </button>
      <div className="px-5 pb-5"><p className="text-sm leading-6 text-muted-foreground">{role.description}</p><div className="mt-4 flex items-center gap-2 text-xs font-semibold text-foreground"><KeyRound className="h-3.5 w-3.5 text-primary" />{role.permissions.length} صلاحيات مسندة</div></div>
      {expanded && <div className="border-t border-border bg-secondary/35 px-5 py-4"><p className="mb-3 text-xs font-bold text-muted-foreground">الصلاحيات</p><div className="grid gap-2 sm:grid-cols-2">{(rolePermissions.length ? rolePermissions : role.permissions.map((code) => ({ code, display_name: code, description: '' }))).map((permission) => <div key={permission.code} className="flex items-center gap-2 text-sm text-foreground" data-testid={`text-role-permission-${role.id}-${permission.code}`}><Check className="h-3.5 w-3.5 text-accent" />{permission.display_name}</div>)}</div></div>}
    </article>
  );
}

export default function RolesPage() {
  const [, setLocation] = useLocation();
  const roles = useListRoles({ request: { credentials: 'include' } });
  const permissions = useListPermissions({ request: { credentials: 'include' } });
  const [expanded, setExpanded] = useState<number | null>(null);

  const handleAuthError = (error: unknown) => {
    const status = (error as { status?: number })?.status;
    if (status === 401) setLocation('/login');
  };

  useEffect(() => {
    if (roles.isError) handleAuthError(roles.error);
    if (permissions.isError) handleAuthError(permissions.error);
  }, [roles.error, roles.isError, permissions.error, permissions.isError]);

  return (
    <div className="space-y-7">
      <header className="flex flex-col justify-between gap-5 border-b border-border pb-7 sm:flex-row sm:items-end">
        <div><p className="mb-3 font-mono text-[10px] tracking-[0.18em] text-primary">مساحة العمل / 03</p><h1 className="text-3xl font-bold tracking-tight text-foreground">الأدوار والصلاحيات</h1><p className="mt-2 text-sm text-muted-foreground">خريطة الوصول التي تنظّم عمل كل عضو في الفريق.</p></div>
        <div className="flex items-center gap-5 font-mono text-xs text-muted-foreground"><span data-testid="text-roles-count">{roles.data?.length ?? '—'} أدوار</span><span data-testid="text-permissions-count">{permissions.data?.length ?? '—'} صلاحيات</span></div>
      </header>
      <div className="grid gap-5 xl:grid-cols-[1fr_0.72fr]">
        <section className="space-y-3">
          <div className="mb-5 flex items-center justify-between"><h2 className="text-lg font-bold">الأدوار المعتمدة</h2><span className="font-mono text-[10px] text-muted-foreground">ROLES</span></div>
          {roles.isLoading ? <div className="rounded-lg border border-border bg-card"><LoadingRows count={3} /></div> : roles.isError ? <div className="rounded-lg border border-border bg-card"><ErrorState onRetry={() => roles.refetch()} message={(roles.error as { status?: number })?.status === 403 ? 'لا تملك صلاحية عرض الأدوار والصلاحيات.' : undefined} /></div> : !roles.data?.length ? <div className="rounded-lg border border-border bg-card"><EmptyState title="لا توجد أدوار" description="لم يتم إعداد أدوار وصول في النظام بعد." /></div> : roles.data.map((role) => <RoleCard key={role.id} role={role} expanded={expanded === role.id} onToggle={() => setExpanded(expanded === role.id ? null : role.id)} permissions={permissions.data || []} />)}
        </section>
        <section className="h-fit rounded-lg border border-border bg-sidebar p-5 text-sidebar-foreground">
          <div className="flex items-center justify-between"><p className="font-mono text-[10px] tracking-[0.16em] text-sidebar-primary">قاموس الوصول</p><KeyRound className="h-4 w-4 text-sidebar-primary" /></div>
          <h2 className="mt-8 text-xl font-bold">كل صلاحية لها سبب.</h2>
          <p className="mt-2 text-sm leading-6 text-sidebar-foreground/60">اضغط على أي دور لتفقد الصلاحيات المسندة إليه. مصدر البيانات هو إعدادات النظام الحالية.</p>
          <div className="mt-8 space-y-1 border-t border-sidebar-border pt-4">
            {permissions.isLoading ? <div className="space-y-3">{[1, 2, 3].map((item) => <div key={item} className="h-8 animate-pulse rounded bg-sidebar-accent" />)}</div> : permissions.isError ? <p className="text-sm leading-6 text-sidebar-foreground/60">تعذر تحميل قاموس الصلاحيات.</p> : (permissions.data || []).map((permission) => <div key={permission.code} className="border-b border-sidebar-border py-3 last:border-0" data-testid={`row-permission-${permission.code}`}><p className="text-sm font-semibold">{permission.display_name}</p><p className="mt-1 font-mono text-[10px] text-sidebar-foreground/45">{permission.code}</p></div>)}
          </div>
        </section>
      </div>
    </div>
  );
}