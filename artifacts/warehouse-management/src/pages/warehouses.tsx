import { useEffect, useMemo, useState, type FormEvent } from 'react';
import { Building2, Pencil, Plus, Search, Warehouse as WarehouseIcon } from 'lucide-react';
import { useLocation } from 'wouter';
import { useQueryClient } from '@tanstack/react-query';
import {
  getListWarehousesQueryKey,
  useCreateWarehouse,
  useListWarehouses,
  useUpdateWarehouse,
} from '@workspace/api-client-react';
import type { Warehouse, WarehouseInputWarehouseType } from '@workspace/api-client-react';
import { Button, EmptyState, ErrorState, Field, LoadingRows, Modal, Notice, SelectField, StatusPill } from '@/components/ui';

type WarehouseForm = {
  name: string;
  code: string;
  description: string;
  warehouse_type: WarehouseInputWarehouseType;
  is_active: boolean;
};

const blankForm: WarehouseForm = {
  name: '',
  code: '',
  description: '',
  warehouse_type: 'branch',
  is_active: true,
};

function errorMessage(error: unknown, fallback: string) {
  const typed = error as { status?: number; detail?: string; response?: { data?: { detail?: string } } };
  if (typed?.status === 401) return 'انتهت الجلسة. سجّل الدخول من جديد للمتابعة.';
  if (typed?.status === 403) return 'لا تملك صلاحية تنفيذ هذا الإجراء.';
  return typed?.detail || typed?.response?.data?.detail || fallback;
}

function WarehouseRow({ warehouse, onEdit }: { warehouse: Warehouse; onEdit: (warehouse: Warehouse) => void }) {
  return (
    <div className="grid grid-cols-[minmax(180px,1.2fr)_110px_130px_100px_90px] items-center gap-4 border-b border-border px-5 py-4 last:border-0 max-md:block max-md:space-y-4" data-testid={`row-warehouse-${warehouse.id}`}>
      <div className="flex items-center gap-3">
        <span className="flex h-10 w-10 items-center justify-center rounded-md bg-primary/10 text-primary"><WarehouseIcon className="h-5 w-5" /></span>
        <div className="min-w-0">
          <p className="truncate text-sm font-bold text-foreground" data-testid={`text-warehouse-name-${warehouse.id}`}>{warehouse.name}</p>
          <p className="truncate font-mono text-[11px] text-muted-foreground">{warehouse.description || 'بدون وصف'}</p>
        </div>
      </div>
      <div><span className="mb-1 block text-[10px] text-muted-foreground/60 md:hidden">الرمز</span><span className="font-mono text-xs text-foreground">{warehouse.code}</span></div>
      <div className="text-sm text-muted-foreground"><span className="mb-1 block text-[10px] text-muted-foreground/60 md:hidden">النوع</span>{warehouse.warehouse_type === 'main' ? 'المخزن الرئيسي' : 'مخزن فرعي'}</div>
      <div><span className="mb-1 block text-[10px] text-muted-foreground/60 md:hidden">الحالة</span><StatusPill active={warehouse.is_active} /></div>
      <div className="text-left"><button type="button" onClick={() => onEdit(warehouse)} data-testid={`button-edit-warehouse-${warehouse.id}`} className="inline-flex items-center gap-1.5 rounded-md px-2.5 py-2 text-xs font-semibold text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"><Pencil className="h-3.5 w-3.5" /> تعديل</button></div>
    </div>
  );
}

export default function WarehousesPage() {
  const [, setLocation] = useLocation();
  const queryClient = useQueryClient();
  const warehouses = useListWarehouses({ request: { credentials: 'include' } });
  const createWarehouse = useCreateWarehouse({ request: { credentials: 'include' } });
  const updateWarehouse = useUpdateWarehouse({ request: { credentials: 'include' } });
  const [search, setSearch] = useState('');
  const [modal, setModal] = useState<'create' | 'edit' | null>(null);
  const [selected, setSelected] = useState<Warehouse | null>(null);
  const [form, setForm] = useState<WarehouseForm>(blankForm);
  const [formError, setFormError] = useState('');

  const filtered = useMemo(() => {
    const needle = search.trim().toLowerCase();
    if (!needle) return warehouses.data || [];
    return (warehouses.data || []).filter((warehouse) => `${warehouse.name} ${warehouse.code} ${warehouse.description}`.toLowerCase().includes(needle));
  }, [search, warehouses.data]);

  const openCreate = () => {
    setSelected(null);
    setForm(blankForm);
    setFormError('');
    setModal('create');
  };
  const openEdit = (warehouse: Warehouse) => {
    setSelected(warehouse);
    setForm({ name: warehouse.name, code: warehouse.code, description: warehouse.description, warehouse_type: warehouse.warehouse_type, is_active: warehouse.is_active });
    setFormError('');
    setModal('edit');
  };
  const closeModal = () => {
    if (!createWarehouse.isPending && !updateWarehouse.isPending) setModal(null);
  };
  const setField = (key: keyof WarehouseForm, value: string | boolean) => setForm((current) => ({ ...current, [key]: value }));

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setFormError('');
    if (!form.name.trim() || !form.code.trim()) {
      setFormError('أكمل اسم المخزن ورمزه قبل الحفظ.');
      return;
    }
    const data = { name: form.name.trim(), code: form.code.trim(), description: form.description.trim(), warehouse_type: form.warehouse_type, is_active: form.is_active };
    const options = {
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: getListWarehousesQueryKey() });
        setModal(null);
        setSelected(null);
        setForm(blankForm);
      },
      onError: (error: unknown) => {
        setFormError(errorMessage(error, 'تعذر حفظ المخزن.'));
        if ((error as { status?: number })?.status === 401) setLocation('/login');
      },
    };
    if (modal === 'create') {
      createWarehouse.mutate({ data }, options);
    } else if (selected) {
      updateWarehouse.mutate({ warehouseId: selected.id, data }, options);
    }
  };

  useEffect(() => {
    if ((warehouses.error as { status?: number })?.status === 401) setLocation('/login');
  }, [setLocation, warehouses.error]);

  return (
    <div className="space-y-7">
      <header className="flex flex-col justify-between gap-5 border-b border-border pb-7 sm:flex-row sm:items-end">
        <div><p className="mb-3 font-mono text-[10px] tracking-[0.18em] text-primary">دليل التشغيل / 04</p><h1 className="text-3xl font-bold tracking-tight text-foreground">المخازن</h1><p className="mt-2 text-sm text-muted-foreground">المخزن الرئيسي والمخازن الفرعية ومواقع التخزين التابعة لها.</p></div>
        <Button testId="button-create-warehouse" onClick={openCreate}><Plus className="h-4 w-4" /> مخزن جديد</Button>
      </header>
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
        <div><span className="font-mono text-2xl font-semibold text-foreground" data-testid="text-warehouses-count">{warehouses.data?.length ?? '—'}</span><span className="mr-2 text-sm text-muted-foreground">مخزن في الدليل</span></div>
        <label className="relative block w-full sm:w-72"><Search className="pointer-events-none absolute right-3 top-3 h-4 w-4 text-muted-foreground" /><input type="search" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="ابحث بالاسم أو الرمز" data-testid="input-search-warehouses" className="h-10 w-full rounded-md border border-input bg-card pr-9 pl-3 text-sm outline-none transition-[border-color,box-shadow] focus:border-primary focus:ring-2 focus:ring-primary/20" /></label>
      </div>
      <section className="overflow-hidden rounded-lg border border-border bg-card">
        <div className="hidden grid-cols-[minmax(180px,1.2fr)_110px_130px_100px_90px] gap-4 border-b border-border bg-secondary/50 px-5 py-3 text-[11px] font-semibold text-muted-foreground md:grid"><span>المخزن</span><span>الرمز</span><span>النوع</span><span>الحالة</span><span /></div>
        {warehouses.isLoading ? <LoadingRows /> : warehouses.isError ? <ErrorState onRetry={() => warehouses.refetch()} message={(warehouses.error as { status?: number })?.status === 403 ? 'لا تملك صلاحية عرض المخازن.' : undefined} /> : filtered.length === 0 ? <EmptyState title={search ? 'لا توجد نتائج' : 'لا توجد مخازن بعد'} description={search ? 'جرّب كلمة بحث مختلفة.' : 'أضف المخزن الرئيسي أو أول مخزن فرعي للبدء.'} action={!search ? <Button testId="button-empty-create-warehouse" onClick={openCreate}><Plus className="h-4 w-4" /> إضافة مخزن</Button> : undefined} /> : filtered.map((warehouse) => <WarehouseRow key={warehouse.id} warehouse={warehouse} onEdit={openEdit} />)}
      </section>
      <div className="flex items-center gap-2 text-xs text-muted-foreground"><Building2 className="h-4 w-4" /><span>تعطيل المخزن يحافظ على تاريخه ويمنع استخدامه التشغيلي مستقبلًا.</span></div>
      {modal && <Modal title={modal === 'create' ? 'إضافة مخزن' : 'تعديل المخزن'} eyebrow={modal === 'create' ? 'دليل المخازن / 01' : `مخزن #${selected?.id}`} onClose={closeModal}>
        {formError && <div className="mb-5"><Notice>{formError}</Notice></div>}
        <form onSubmit={submit} className="space-y-5">
          <Field label="اسم المخزن" name="name" value={form.name} onChange={(value) => setField('name', value)} placeholder="مثال: المخزن الرئيسي" required />
          <Field label="الرمز" name="code" value={form.code} onChange={(value) => setField('code', value)} placeholder="مثال: MAIN" required />
          <Field label="الوصف" name="description" value={form.description} onChange={(value) => setField('description', value)} placeholder="وصف مختصر للمخزن" />
          <SelectField label="نوع المخزن" name="warehouse_type" value={form.warehouse_type} onChange={(value) => setField('warehouse_type', value as WarehouseInputWarehouseType)} required options={[{ value: 'main', label: 'المخزن الرئيسي' }, { value: 'branch', label: 'مخزن فرعي' }]} />
          <label className="flex cursor-pointer items-center justify-between rounded-md border border-border bg-secondary/40 px-3 py-3 text-sm"><span><span className="block font-semibold">المخزن نشط</span><span className="mt-1 block text-xs text-muted-foreground">يظهر في قوائم الربط مع الأصناف</span></span><input type="checkbox" checked={form.is_active} onChange={(event) => setField('is_active', event.target.checked)} data-testid="input-warehouse-active" className="h-4 w-4 accent-[hsl(var(--primary))]" /></label>
          <div className="flex flex-col-reverse gap-3 pt-2 sm:flex-row"><Button type="submit" testId="button-save-warehouse" disabled={createWarehouse.isPending || updateWarehouse.isPending}>{createWarehouse.isPending || updateWarehouse.isPending ? 'جارٍ الحفظ...' : 'حفظ المخزن'}</Button><Button type="button" variant="secondary" testId="button-cancel-warehouse" onClick={closeModal}>إلغاء</Button></div>
        </form>
      </Modal>}
    </div>
  );
}