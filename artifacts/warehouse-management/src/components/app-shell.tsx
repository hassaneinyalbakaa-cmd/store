import { useState, type ReactNode } from 'react';
import { Link, useLocation } from 'wouter';
import { Archive, ArrowLeftRight, Box, Building2, ChevronLeft, ClipboardCheck, ClipboardList, ClipboardPlus, ClipboardPenLine, Layers3, LogOut, Menu, ShieldCheck, Users, Warehouse, X } from 'lucide-react';
import type { SessionUser } from '@workspace/api-client-react';
import { useLogout } from '@workspace/api-client-react';
import { getGetCurrentUserQueryKey } from '@workspace/api-client-react';
import { useQueryClient } from '@tanstack/react-query';

const navigation = [
  { href: '/dashboard', label: 'نظرة عامة', icon: ClipboardList, permission: null },
  { href: '/users', label: 'المستخدمون', icon: Users, permission: 'users:read' },
  { href: '/roles', label: 'الأدوار والصلاحيات', icon: ShieldCheck, permission: null },
  { href: '/warehouses', label: 'المخازن', icon: Warehouse, permission: 'warehouses:read' },
  { href: '/departments', label: 'الأقسام', icon: Building2, permission: 'departments:read' },
  { href: '/items', label: 'الأصناف', icon: Archive, permission: 'items:read' },
  { href: '/receipts', label: 'سندات الاستلام', icon: ClipboardPlus, permission: 'receipts:read' },
  { href: '/inventory', label: 'المخزون', icon: Layers3, permission: 'inventory:read' },
  { href: '/issue-requests', label: 'طلبات الصرف', icon: ClipboardCheck, permission: 'issue_requests:read' },
  { href: '/issue-vouchers', label: 'سندات الصرف', icon: ClipboardPlus, permission: 'issues:read' },
  { href: '/transfers', label: 'تحويلات المخزون', icon: ArrowLeftRight, permission: 'transfers:read' },
  { href: '/stocktakes', label: 'الجرد الفعلي', icon: ClipboardPenLine, permission: 'stocktakes:read' },
  { href: '/stocktake-adjustments', label: 'تسويات الجرد', icon: ClipboardCheck, permission: 'stocktakes:read' },
];

export function AppShell({ user, children }: { user: SessionUser; children: ReactNode }) {
  const [location, setLocation] = useLocation();
  const [mobileOpen, setMobileOpen] = useState(false);
  const logout = useLogout();
  const queryClient = useQueryClient();

  const signOut = () => {
    logout.mutate(undefined, {
      onSuccess: () => {
        queryClient.setQueryData(getGetCurrentUserQueryKey(), null);
        setLocation('/login');
      },
      onError: () => {
        setLocation('/login');
      },
    });
  };

  return (
    <div className="min-h-[100dvh] bg-background" dir="rtl">
      <button
        type="button"
        aria-label="فتح القائمة"
        data-testid="button-open-menu"
        onClick={() => setMobileOpen(true)}
        className="fixed right-4 top-4 z-30 flex h-10 w-10 items-center justify-center rounded-md border border-border bg-card text-foreground shadow-md md:hidden"
      >
        <Menu className="h-5 w-5" />
      </button>
      {mobileOpen && (
        <button
          type="button"
          aria-label="إغلاق القائمة"
          data-testid="button-close-menu-overlay"
          onClick={() => setMobileOpen(false)}
          className="fixed inset-0 z-40 bg-foreground/30 md:hidden"
        />
      )}
      <aside
        className={`fixed inset-y-0 right-0 z-50 flex w-[min(84vw,300px)] flex-col border-l border-sidebar-border bg-sidebar text-sidebar-foreground transition-transform duration-300 md:translate-x-0 ${
          mobileOpen ? 'translate-x-0' : 'translate-x-full'
        }`}
      >
        <div className="flex items-center justify-between border-b border-sidebar-border px-6 py-6">
          <Link href="/dashboard" data-testid="link-brand" className="flex items-center gap-3" onClick={() => setMobileOpen(false)}>
            <span className="flex h-10 w-10 items-center justify-center rounded-md bg-sidebar-primary text-sidebar-primary-foreground">
              <Box className="h-5 w-5" strokeWidth={2.5} />
            </span>
            <span>
              <span className="block text-[15px] font-bold">نظام إدارة المخزن</span>
              <span className="mt-0.5 block font-mono text-[9px] tracking-[0.16em] text-sidebar-foreground/55">WAREHOUSE / LOCAL</span>
            </span>
          </Link>
          <button type="button" onClick={() => setMobileOpen(false)} data-testid="button-close-menu" className="rounded-md p-2 text-sidebar-foreground/60 hover:bg-sidebar-accent md:hidden">
            <X className="h-5 w-5" />
          </button>
        </div>
        <div className="px-4 pt-7">
          <p className="mb-3 px-3 font-mono text-[10px] uppercase tracking-[0.18em] text-sidebar-foreground/45">مساحة العمل</p>
          <nav className="space-y-1">
            {navigation.map((item) => {
              const allowed = !item.permission || user.permissions.includes(item.permission);
              if (!allowed) return null;
              const active = location === item.href;
              const Icon = item.icon;
              return (
                <Link
                  href={item.href}
                  key={item.href}
                  data-testid={`link-nav-${item.href.slice(1)}`}
                  onClick={() => setMobileOpen(false)}
                  className={`group flex items-center gap-3 rounded-md px-3 py-3 text-sm transition-colors ${
                    active ? 'bg-sidebar-primary font-bold text-sidebar-primary-foreground' : 'text-sidebar-foreground/70 hover:bg-sidebar-accent hover:text-sidebar-foreground'
                  }`}
                >
                  <Icon className="h-[18px] w-[18px]" />
                  <span>{item.label}</span>
                  {active && <ChevronLeft className="mr-auto h-4 w-4 opacity-70" />}
                </Link>
              );
            })}
          </nav>
        </div>
        <div className="mt-auto border-t border-sidebar-border px-4 py-5">
          <div className="mb-4 flex items-center gap-3 rounded-md bg-sidebar-accent/60 px-3 py-3">
            <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-sidebar-primary text-sm font-bold text-sidebar-primary-foreground">
              {user.display_name.slice(0, 1)}
            </span>
            <span className="min-w-0">
              <span className="block truncate text-sm font-semibold">{user.display_name}</span>
              <span className="block truncate text-xs text-sidebar-foreground/50">{user.role_name}</span>
            </span>
          </div>
          <button
            type="button"
            onClick={signOut}
            disabled={logout.isPending}
            data-testid="button-logout"
            className="flex w-full items-center gap-3 rounded-md px-3 py-3 text-sm text-sidebar-foreground/60 transition-colors hover:bg-sidebar-accent hover:text-sidebar-foreground disabled:opacity-50"
          >
            <LogOut className="h-[18px] w-[18px]" />
            {logout.isPending ? 'جارٍ الخروج...' : 'تسجيل الخروج'}
          </button>
        </div>
      </aside>
      <main className="min-h-[100dvh] md:mr-[300px]">
        <div className="mx-auto max-w-[1440px] px-5 pb-10 pt-20 sm:px-8 md:px-10 md:pt-9">{children}</div>
      </main>
    </div>
  );
}