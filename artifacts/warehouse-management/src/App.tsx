import { type ReactNode } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ErrorBoundary } from '@/components/error-boundary';
import { Toaster } from '@/components/ui/toaster';
import { TooltipProvider } from '@/components/ui/tooltip';
import { AppShell } from '@/components/app-shell';
import { Notice } from '@/components/ui';
import { useGetCurrentUser } from '@workspace/api-client-react';
import type { SessionUser } from '@workspace/api-client-react';
import DashboardPage from '@/pages/dashboard';
import LoginPage from '@/pages/login';
import RolesPage from '@/pages/roles';
import UsersPage from '@/pages/users';
import NotFound from '@/pages/not-found';
import {
  Route,
  Switch,
  Link,
  useLocation,
  Router as WouterRouter,
} from 'wouter';

const queryClient = new QueryClient();

function Forbidden({ message = 'لا تملك الصلاحية اللازمة لعرض هذه الصفحة.' }: { message?: string }) {
  return <div className="flex min-h-[70dvh] items-center justify-center" dir="rtl"><div className="w-full max-w-md rounded-lg border border-border bg-card p-7 text-center"><p className="mb-2 font-mono text-[10px] tracking-[0.18em] text-destructive">403 / ممنوع</p><h1 className="text-2xl font-bold">هذا القسم محمي</h1><div className="mt-4"><Notice>{message}</Notice></div><Link href="/dashboard" data-testid="link-forbidden-dashboard" className="mt-5 inline-flex min-h-10 items-center justify-center rounded-md border border-border bg-secondary px-4 text-sm font-semibold text-secondary-foreground transition-colors hover:bg-card">العودة للرئيسية</Link></div></div>;
}

function Protected({ user, children, permission }: { user: SessionUser; children: ReactNode; permission?: string }) {
  if (permission && !user.permissions.includes(permission)) return <AppShell user={user}><Forbidden /></AppShell>;
  return <AppShell user={user}>{children}</AppShell>;
}

function Router({ user }: { user: SessionUser | null }) {
  return (
    // Keep a shared shell (sidebar, navbar) outside the boundary so it
    // survives a page crash.
    <RoutedErrorBoundary>
      <Switch>
        <Route path="/">{() => user ? <Protected user={user}><DashboardPage user={user} /></Protected> : <LoginPage />}</Route>
        <Route path="/login" component={LoginPage} />
        <Route path="/dashboard">{() => user ? <Protected user={user}><DashboardPage user={user} /></Protected> : <LoginPage />}</Route>
        <Route path="/users">{() => user ? <Protected user={user} permission="users:read"><UsersPage canWrite={user.permissions.includes('users:write')} /></Protected> : <LoginPage />}</Route>
        <Route path="/roles">{() => user ? <Protected user={user}><RolesPage /></Protected> : <LoginPage />}</Route>
        <Route component={NotFound} />
      </Switch>
    </RoutedErrorBoundary>
  );
}

function RoutedErrorBoundary({ children }: { children: ReactNode }) {
  const [location] = useLocation();
  return <ErrorBoundary resetKey={location}>{children}</ErrorBoundary>;
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <WouterRouter base={import.meta.env.BASE_URL.replace(/\/$/, '')}>
          <AuthAwareRouter />
        </WouterRouter>
        <Toaster />
      </TooltipProvider>
    </QueryClientProvider>
  );
}

function AuthAwareRouter() {
  const currentUser = useGetCurrentUser({
    request: { credentials: 'include' },
    query: { retry: false },
  });
  if (currentUser.isLoading && !currentUser.error) return <div className="flex min-h-[100dvh] items-center justify-center bg-background" dir="rtl"><div className="w-64 space-y-3" data-testid="loading-session"><div className="h-2 animate-pulse rounded bg-muted" /><div className="h-2 w-3/4 animate-pulse rounded bg-muted" /><div className="h-2 w-1/2 animate-pulse rounded bg-muted" /></div></div>;
  return <Router user={currentUser.data || null} />;
}

export default App;
