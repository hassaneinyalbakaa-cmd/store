import { useEffect, useMemo, useState, type FormEvent } from 'react';
import { Building2, Pencil, Plus, Search } from 'lucide-react';
import { useLocation } from 'wouter';
import { useQueryClient } from '@tanstack/react-query';
import {
  getListDepartmentsQueryKey,
  useCreateDepartment,
  useListDepartments,
  useUpdateDepartment,
} from '@workspace/api-client-react';
import type { Department } from '@workspace/api-client-react';
import { Button, EmptyState, ErrorState, Field, LoadingRows, Modal, Notice, StatusPill } from '@/components/ui';

type DepartmentForm = { name: string; code: string; is_active: boolean };
const blankForm: DepartmentForm = { name: '', code: '', is_active: true };

function errorMessage(error: unknown, fallback: string) {
  const typed = error as { status?: number; detail?: string; response?: { data?: { detail?: string } } };
  if (typed?.status === 401) return 'انتهت الجلسة. سجّل الدخول من جديد للمتابعة.';
  if (typed?.status === 403) return 'لا تملك صلاحية تنفيذ هذا الإجراء.';
  return typed?.detail || typed?.response?.data?.detail || fallback;
}

export default function DepartmentsPage() {
  const [, setLocation] = useLocation();
  const queryClient = useQueryClient();
  const departments = useListDepartments({ request: { credentials: 'include' } });
  const createDepartment = useCreateDepartment({ request: { credentials: 'include' } });
  const updateDepartment = useUpdateDepartment({ request: { credentials: 'include' } });
  const [search, setSearch] = useState('');
  const [modal, setModal] = useState<'create' | 'edit' | null>(null);
  const [selected, setSelected] = useState<Department | null>(null);
  const [form, setForm] = useState<DepartmentForm>(blankForm);
  const [formError, setFormError] = useState('');

  const filtered = useMemo(() => {
    const needle = search.trim().toLowerCase();
    if (!needle) return departments.data || [];
    return (departments.data || []).filter((department) => `${department.name} ${department.code}`.toLowerCase().includes(needle));
  }, [departments.data, search]);

  const openCreate = () => {
    setSelected(null); setForm(blankForm); setFormError(''); setModal('create');
  };
  const openEdit = (department: Department) => {
    setSelected(department); setForm({ name: department.name, code: department.code, is_active: department.is_active }); setFormError(''); setModal('edit');
  };
  const closeModal = () => {
    if (!createDepartment.isPending && !updateDepartment.isPending) setModal(null);
  };
  const setField = (key: keyof DepartmentForm, value: string | boolean) => setForm((current) => ({ ...current, [key]: value }));

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setFormError('');
    if (!form.name.trim() || !form.code.trim()) {
      setFormError('أكمل اسم القسم ورمزه قبل الحفظ.');
      return;
    }
    const data = { name: form.name.trim(), code: form.code.trim(), is_active: form.is_active };
    const options = {
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: getListDepartmentsQueryKey() });
        setModal(null); setSelected(null); setForm(blankForm);
      },
      onError: (error: unknown) => {
        setFormError(errorMessage(error, 'تعذر حفظ القسم.'));
        if ((error as { status?: number })?.status === 401) setLocation('/login');
      },
    };
    if (modal === 'create') createDepartment.mutate({ data }, options);
    else if (selected) updateDepartment.mutate({ departmentId: selected.id, data }, options);
  };

  useEffect(() => {
    if ((departments.error as { status?: number })?.status === 401) setLocation('/login');
  }, [departments.error, setLocation]);

  return (
    <div className="space-y-7">
      <header className="flex flex-col justify-between gap-5 border-b border-border pb-7 sm:flex-row sm:items-end">
        <div><p className="mb-3 font-mono text-[10px] tracking-[0.18em] text-primary">دليل التشغيل / 05</p><h1 className="text-3xl font-bold tracking-tight text-foreground">الأقسام</h1><p className="mt-2 text-sm text-muted-foreground">الأقسام المستفيدة من المواد داخل النظام، بعدد غير محدود.</p></div>
        <Button testId="button-create-department" onClick={openCreate}><Plus className="h-4 w-4" /> قسم جديد</Button>
      </header>
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
        <div><span className="font-mono text-2xl font-semibold text-foreground" data-testid="text-departments-count">{departments.data?.length ?? '—'}</span><span className="mr-2 text-sm text-muted-foreground">قسم في الدليل</span></div>
        <label className="relative block w-full sm:w-72"><Search className="pointer-events-none absolute right-3 top-3 h-4 w-4 text-muted-foreground" /><input type="search" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="ابحث بالاسم أو الرمز" data-testid="input-search-departments" className="h-10 w-full rounded-md border border-input bg-card pr-9 pl-3 text-sm outline-none transition-[border-color,box-shadow] focus:border-primary focus:ring-2 focus:ring-primary/20" /></label>
      </div>
      <section className="overflow-hidden rounded-lg border border-border bg-card">
        <div className="hidden grid-cols-[minmax(180px,1.3fr)_160px_110px_90px] gap-4 border-b border-border bg-secondary/50 px-5 py-3 text-[11px] font-semibold text-muted-foreground md:grid"><span>القسم</span><span>الرمز</span><span>الحالة</span><span /></div>
        {departments.isLoading ? <LoadingRows /> : departments.isError ? <ErrorState onRetry={() => departments.refetch()} message={(departments.error as { status?: number })?.status === 403 ? 'لا تملك صلاحية عرض الأقسام.' : undefined} /> : filtered.length === 0 ? <EmptyState title={search ? 'لا توجد نتائج' : 'لا توجد أقسام بعد'} description={search ? 'جرّب كلمة بحث مختلفة.' : 'أضف أول قسم مستفيد من مواد المخزن.'} action={!search ? <Button testId="button-empty-create-department" onClick={openCreate}><Plus className="h-4 w-4" /> إضافة قسم</Button> : undefined} /> : filtered.map((department) => (
          <div key={department.id} className="grid grid-cols-[minmax(180px,1.3fr)_160px_110px_90px] items-center gap-4 border-b border-border px-5 py-4 last:border-0 max-md:block max-md:space-y-4" data-testid={`row-department-${department.id}`}>
            <div className="flex items-center gap-3"><span className="flex h-10 w-10 items-center justify-center rounded-md bg-accent/10 text-accent"><Building2 className="h-5 w-5" /></span><p className="truncate text-sm font-bold text-foreground">{department.name}</p></div>
            <div><span className="mb-1 block text-[10px] text-muted-foreground/60 md:hidden">الرمز</span><span className="font-mono text-xs">{department.code}</span></div>
            <div><span className="mb-1 block text-[10px] text-muted-foreground/60 md:hidden">الحالة</span><StatusPill active={department.is_active} /></div>
            <div className="text-left"><button type="button" onClick={() => openEdit(department)} data-testid={`button-edit-department-${department.id}`} className="inline-flex items-center gap-1.5 rounded-md px-2.5 py-2 text-xs font-semibold text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"><Pencil className="h-3.5 w-3.5" /> تعديل</button></div>
          </div>
        ))}
      </section>
      <div className="flex items-center gap-2 text-xs text-muted-foreground"><Building2 className="h-4 w-4" /><span>تعطيل القسم يحافظ على السجلات السابقة دون حذفه من قاعدة البيانات.</span></div>
      {modal && <Modal title={modal === 'create' ? 'إضافة قسم' : 'تعديل القسم'} eyebrow={modal === 'create' ? 'دليل الأقسام / 01' : `قسم #${selected?.id}`} onClose={closeModal}>
        {formError && <div className="mb-5"><Notice>{formError}</Notice></div>}
        <form onSubmit={submit} className="space-y-5">
          <Field label="اسم القسم" name="name" value={form.name} onChange={(value) => setField('name', value)} placeholder="مثال: قسم الصيانة" required />
          <Field label="الرمز" name="code" value={form.code} onChange={(value) => setField('code', value)} placeholder="مثال: MAINT" required />
          <label className="flex cursor-pointer items-center justify-between rounded-md border border-border bg-secondary/40 px-3 py-3 text-sm"><span><span className="block font-semibold">القسم نشط</span><span className="mt-1 block text-xs text-muted-foreground">يظهر ضمن القوائم المرجعية</span></span><input type="checkbox" checked={form.is_active} onChange={(event) => setField('is_active', event.target.checked)} data-testid="input-department-active" className="h-4 w-4 accent-[hsl(var(--primary))]" /></label>
          <div className="flex flex-col-reverse gap-3 pt-2 sm:flex-row"><Button type="submit" testId="button-save-department" disabled={createDepartment.isPending || updateDepartment.isPending}>{createDepartment.isPending || updateDepartment.isPending ? 'جارٍ الحفظ...' : 'حفظ القسم'}</Button><Button type="button" variant="secondary" testId="button-cancel-department" onClick={closeModal}>إلغاء</Button></div>
        </form>
      </Modal>}
    </div>
  );
}