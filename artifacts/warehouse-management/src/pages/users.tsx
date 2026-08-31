import { useEffect, useMemo, useState, type FormEvent } from 'react';
import { useLocation } from 'wouter';
import { Pencil, Plus, Search, UsersRound } from 'lucide-react';
import { getGetDashboardSummaryQueryKey, getListUsersQueryKey, useCreateUser, useListRoles, useListUsers, useUpdateUser } from '@workspace/api-client-react';
import type { Role, User } from '@workspace/api-client-react';
import { useQueryClient } from '@tanstack/react-query';
import { Button, EmptyState, ErrorState, Field, LoadingRows, Modal, Notice, SelectField, StatusPill } from '@/components/ui';

function errorMessage(error: unknown, fallback: string) {
  const typed = error as { status?: number; detail?: string; response?: { data?: { detail?: string } } };
  if (typed?.status === 401) return 'انتهت الجلسة. سجّل الدخول من جديد للمتابعة.';
  if (typed?.status === 403) return 'لا تملك صلاحية تنفيذ هذا الإجراء.';
  return typed?.detail || typed?.response?.data?.detail || fallback;
}

type FormState = {
  username: string;
  password: string;
  display_name: string;
  role_id: string;
  is_active: boolean;
};

const blankForm: FormState = { username: '', password: '', display_name: '', role_id: '', is_active: true };

function initials(name: string) {
  return name.trim().split(/\s+/).slice(0, 2).map((part) => part[0]).join('');
}

function UserRow({ user, canWrite, onEdit }: { user: User; canWrite: boolean; onEdit: (user: User) => void }) {
  return (
    <div className="grid grid-cols-[minmax(180px,1.3fr)_minmax(120px,0.8fr)_100px_88px] items-center gap-4 border-b border-border px-5 py-4 last:border-0 max-md:block max-md:space-y-4" data-testid={`row-user-${user.id}`}>
      <div className="flex items-center gap-3">
        <span className="flex h-10 w-10 items-center justify-center rounded-full bg-secondary text-xs font-bold text-secondary-foreground">{initials(user.display_name)}</span>
        <div className="min-w-0">
          <p className="truncate text-sm font-bold text-foreground" data-testid={`text-user-name-${user.id}`}>{user.display_name}</p>
          <p className="truncate font-mono text-[11px] text-muted-foreground" data-testid={`text-user-username-${user.id}`}>@{user.username}</p>
        </div>
      </div>
      <div className="text-sm text-muted-foreground"><span className="mb-1 block text-[10px] text-muted-foreground/60 md:hidden">الدور</span>{user.role_name}</div>
      <div><span className="mb-1 block text-[10px] text-muted-foreground/60 md:hidden">الحالة</span><StatusPill active={user.is_active} /></div>
      <div className="text-left">
        {canWrite && <button type="button" onClick={() => onEdit(user)} data-testid={`button-edit-user-${user.id}`} className="inline-flex items-center gap-1.5 rounded-md px-2.5 py-2 text-xs font-semibold text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"><Pencil className="h-3.5 w-3.5" /> تعديل</button>}
      </div>
    </div>
  );
}

export default function UsersPage({ canWrite }: { canWrite: boolean }) {
  const [, setLocation] = useLocation();
  const queryClient = useQueryClient();
  const users = useListUsers({ request: { credentials: 'include' } });
  const roles = useListRoles({ request: { credentials: 'include' } });
  const createUser = useCreateUser({ request: { credentials: 'include' } });
  const updateUser = useUpdateUser({ request: { credentials: 'include' } });
  const [search, setSearch] = useState('');
  const [modal, setModal] = useState<'create' | 'edit' | null>(null);
  const [selected, setSelected] = useState<User | null>(null);
  const [form, setForm] = useState<FormState>(blankForm);
  const [formError, setFormError] = useState('');

  const filteredUsers = useMemo(() => {
    const list = users.data || [];
    const needle = search.trim().toLowerCase();
    if (!needle) return list;
    return list.filter((user) => `${user.display_name} ${user.username} ${user.role_name}`.toLowerCase().includes(needle));
  }, [users.data, search]);

  const openCreate = () => {
    setSelected(null); setForm(blankForm); setFormError(''); setModal('create');
  };
  const openEdit = (user: User) => {
    setSelected(user); setForm({ username: user.username, password: '', display_name: user.display_name, role_id: String(user.role_id), is_active: user.is_active }); setFormError(''); setModal('edit');
  };
  const closeModal = () => { if (!createUser.isPending && !updateUser.isPending) setModal(null); };
  const updateField = (key: keyof FormState, value: string | boolean) => setForm((current) => ({ ...current, [key]: value }));

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setFormError('');
    if (!form.role_id || !form.display_name.trim() || (modal === 'create' && (!form.username.trim() || !form.password))) {
      setFormError('أكمل الحقول المطلوبة قبل الحفظ.');
      return;
    }
    if (modal === 'create') {
      createUser.mutate(
        { data: { username: form.username.trim(), password: form.password, display_name: form.display_name.trim(), role_id: Number(form.role_id), is_active: form.is_active } },
        {
          onSuccess: () => { queryClient.invalidateQueries({ queryKey: getListUsersQueryKey() }); queryClient.invalidateQueries({ queryKey: getGetDashboardSummaryQueryKey() }); setModal(null); setForm(blankForm); },
          onError: (error) => { const message = errorMessage(error, 'تعذر إنشاء المستخدم.'); setFormError(message); if ((error as { status?: number })?.status === 401) setLocation('/login'); },
        },
      );
    } else if (selected) {
      updateUser.mutate(
        { userId: selected.id, data: { ...(form.password ? { password: form.password } : {}), display_name: form.display_name.trim(), role_id: Number(form.role_id), is_active: form.is_active } },
        {
          onSuccess: () => { queryClient.invalidateQueries({ queryKey: getListUsersQueryKey() }); queryClient.invalidateQueries({ queryKey: getGetDashboardSummaryQueryKey() }); setModal(null); setSelected(null); },
          onError: (error) => { const message = errorMessage(error, 'تعذر تعديل المستخدم.'); setFormError(message); if ((error as { status?: number })?.status === 401) setLocation('/login'); },
        },
      );
    }
  };

  useEffect(() => {
    const status = (users.error as { status?: number })?.status;
    const roleStatus = (roles.error as { status?: number })?.status;
    if ((users.isError && status === 401) || (roles.isError && roleStatus === 401)) setLocation('/login');
  }, [roles.error, roles.isError, users.error, users.isError, setLocation]);

  return (
    <div className="space-y-7">
      <header className="flex flex-col justify-between gap-5 border-b border-border pb-7 sm:flex-row sm:items-end">
        <div><p className="mb-3 font-mono text-[10px] tracking-[0.18em] text-primary">مساحة العمل / 02</p><h1 className="text-3xl font-bold tracking-tight text-foreground">المستخدمون</h1><p className="mt-2 text-sm text-muted-foreground">حسابات الفريق وصلاحيات الوصول إلى النظام.</p></div>
        {canWrite && <Button testId="button-create-user" onClick={openCreate}><Plus className="h-4 w-4" /> مستخدم جديد</Button>}
      </header>
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
        <div><span className="font-mono text-2xl font-semibold text-foreground" data-testid="text-users-count">{users.data?.length ?? '—'}</span><span className="mr-2 text-sm text-muted-foreground">حساب في القائمة</span></div>
        <label className="relative block w-full sm:w-72">
          <Search className="pointer-events-none absolute right-3 top-3 h-4 w-4 text-muted-foreground" />
          <input type="search" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="ابحث بالاسم أو الدور" data-testid="input-search-users" className="h-10 w-full rounded-md border border-input bg-card pr-9 pl-3 text-sm outline-none transition-[border-color,box-shadow] focus:border-primary focus:ring-2 focus:ring-primary/20" />
        </label>
      </div>
      <section className="overflow-hidden rounded-lg border border-border bg-card">
        <div className="hidden grid-cols-[minmax(180px,1.3fr)_minmax(120px,0.8fr)_100px_88px] gap-4 border-b border-border bg-secondary/50 px-5 py-3 text-[11px] font-semibold text-muted-foreground md:grid"><span>المستخدم</span><span>الدور</span><span>الحالة</span><span /></div>
        {users.isLoading ? <LoadingRows /> : users.isError ? <ErrorState onRetry={() => users.refetch()} message={(users.error as { status?: number })?.status === 403 ? 'لا تملك صلاحية عرض قائمة المستخدمين.' : undefined} /> : filteredUsers.length === 0 ? <EmptyState title={search ? 'لا توجد نتائج' : 'لا يوجد مستخدمون بعد'} description={search ? 'جرّب كلمة بحث مختلفة.' : 'ابدأ بإضافة أول حساب لفريق المخزن.'} action={!search && canWrite ? <Button testId="button-empty-create-user" onClick={openCreate}><Plus className="h-4 w-4" /> إضافة مستخدم</Button> : undefined} /> : filteredUsers.map((user) => <UserRow key={user.id} user={user} canWrite={canWrite} onEdit={openEdit} />)}
      </section>
      <div className="flex items-center gap-2 text-xs text-muted-foreground"><UsersRound className="h-4 w-4" /><span>يمكن لمسؤول النظام تعديل حالة الحساب أو تغيير الدور في أي وقت.</span></div>
      {modal && (
        <Modal title={modal === 'create' ? 'إضافة مستخدم' : 'تعديل المستخدم'} eyebrow={modal === 'create' ? 'حساب جديد / 01' : `حساب #${selected?.id}`} onClose={closeModal}>
          {formError && <div className="mb-5"><Notice>{formError}</Notice></div>}
          <form onSubmit={submit} className="space-y-5">
            {modal === 'create' && <Field label="اسم المستخدم" name="username" value={form.username} onChange={(value) => updateField('username', value)} placeholder="مثال: ahmed.warehouse" required />}
            <Field label="الاسم الظاهر" name="display_name" value={form.display_name} onChange={(value) => updateField('display_name', value)} placeholder="الاسم الكامل" required />
            <Field label={modal === 'create' ? 'كلمة المرور' : 'كلمة مرور جديدة'} name="password" type="password" value={form.password} onChange={(value) => updateField('password', value)} placeholder={modal === 'edit' ? 'اتركه فارغاً للإبقاء على الحالية' : 'ثمانية أحرف على الأقل'} required={modal === 'create'} hint={modal === 'edit' ? 'اختياري عند التعديل.' : undefined} />
            <SelectField label="الدور" name="role_id" value={form.role_id} onChange={(value) => updateField('role_id', value)} required options={(roles.data || []).map((role: Role) => ({ value: String(role.id), label: role.display_name }))} />
            <label className="flex cursor-pointer items-center justify-between rounded-md border border-border bg-secondary/40 px-3 py-3 text-sm"><span><span className="block font-semibold">الحساب نشط</span><span className="mt-1 block text-xs text-muted-foreground">يسمح للمستخدم بتسجيل الدخول</span></span><input type="checkbox" checked={form.is_active} onChange={(event) => updateField('is_active', event.target.checked)} data-testid="input-is-active" className="h-4 w-4 accent-[hsl(var(--primary))]" /></label>
            {roles.isError && <Notice>تعذر تحميل الأدوار. لا يمكن الحفظ قبل اختيار دور.</Notice>}
            <div className="flex flex-col-reverse gap-3 pt-2 sm:flex-row"><Button type="submit" testId="button-save-user" disabled={createUser.isPending || updateUser.isPending || roles.isLoading}>{createUser.isPending || updateUser.isPending ? 'جارٍ الحفظ...' : 'حفظ المستخدم'}</Button><Button type="button" variant="secondary" testId="button-cancel-user" onClick={closeModal}>إلغاء</Button></div>
          </form>
        </Modal>
      )}
    </div>
  );
}