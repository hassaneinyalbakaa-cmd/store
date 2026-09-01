import { useEffect, useMemo, useState, type FormEvent } from 'react';
import { Archive, Check, Pencil, Plus, Search, SlidersHorizontal } from 'lucide-react';
import { useLocation } from 'wouter';
import { useQueryClient } from '@tanstack/react-query';
import {
  getListItemsQueryKey,
  useCreateItem,
  useListItems,
  useListWarehouses,
  useUpdateItem,
} from '@workspace/api-client-react';
import type { Item, Warehouse } from '@workspace/api-client-react';
import { Button, EmptyState, ErrorState, Field, LoadingRows, Modal, Notice, SelectField, StatusPill } from '@/components/ui';

type ItemForm = {
  code: string;
  name: string;
  description: string;
  category: string;
  unit: string;
  part_number: string;
  minimum_level: string;
  warehouse_id: string;
  area: string;
  shelf: string;
  bin: string;
  requires_serial_number: boolean;
  requires_expiry_date: boolean;
  is_active: boolean;
};

const blankForm: ItemForm = {
  code: '',
  name: '',
  description: '',
  category: '',
  unit: '',
  part_number: '',
  minimum_level: '0',
  warehouse_id: '',
  area: '',
  shelf: '',
  bin: '',
  requires_serial_number: false,
  requires_expiry_date: false,
  is_active: true,
};

function errorMessage(error: unknown, fallback: string) {
  const typed = error as { status?: number; detail?: string; response?: { data?: { detail?: string } } };
  if (typed?.status === 401) return 'انتهت الجلسة. سجّل الدخول من جديد للمتابعة.';
  if (typed?.status === 403) return 'لا تملك صلاحية تنفيذ هذا الإجراء.';
  return typed?.detail || typed?.response?.data?.detail || fallback;
}

function locationText(item: Item) {
  const location = item.storage_location;
  return location ? `${location.area} / ${location.shelf} / ${location.bin}` : 'غير محدد';
}

export default function ItemsPage() {
  const [, setLocation] = useLocation();
  const queryClient = useQueryClient();
  const warehouses = useListWarehouses({ request: { credentials: 'include' } });
  const [search, setSearch] = useState('');
  const [warehouseFilter, setWarehouseFilter] = useState('');
  const [activeFilter, setActiveFilter] = useState('all');
  const params = useMemo(() => ({
    search: search.trim() || undefined,
    warehouseId: warehouseFilter ? Number(warehouseFilter) : undefined,
    isActive: activeFilter === 'all' ? undefined : activeFilter === 'active',
  }), [activeFilter, search, warehouseFilter]);
  const items = useListItems(params, { request: { credentials: 'include' } });
  const createItem = useCreateItem({ request: { credentials: 'include' } });
  const updateItem = useUpdateItem({ request: { credentials: 'include' } });
  const [modal, setModal] = useState<'create' | 'edit' | null>(null);
  const [selected, setSelected] = useState<Item | null>(null);
  const [form, setForm] = useState<ItemForm>(blankForm);
  const [formError, setFormError] = useState('');

  const openCreate = () => {
    setSelected(null);
    setForm({ ...blankForm, warehouse_id: warehouses.data?.find((warehouse) => warehouse.is_active)?.id.toString() || '' });
    setFormError('');
    setModal('create');
  };
  const openEdit = (item: Item) => {
    setSelected(item);
    setForm({
      code: item.code,
      name: item.name,
      description: item.description,
      category: item.category,
      unit: item.unit,
      part_number: item.part_number || '',
      minimum_level: String(item.minimum_level),
      warehouse_id: String(item.warehouse_id),
      area: item.storage_location?.area || '',
      shelf: item.storage_location?.shelf || '',
      bin: item.storage_location?.bin || '',
      requires_serial_number: item.requires_serial_number,
      requires_expiry_date: item.requires_expiry_date,
      is_active: item.is_active,
    });
    setFormError('');
    setModal('edit');
  };
  const closeModal = () => {
    if (!createItem.isPending && !updateItem.isPending) setModal(null);
  };
  const setField = (key: keyof ItemForm, value: string | boolean) => setForm((current) => ({ ...current, [key]: value }));

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setFormError('');
    if (!form.code.trim() || !form.name.trim() || !form.unit.trim() || !form.warehouse_id) {
      setFormError('أكمل كود الصنف واسمه ووحدته والمخزن قبل الحفظ.');
      return;
    }
    const hasLocation = Boolean(form.area.trim() || form.shelf.trim() || form.bin.trim());
    if (hasLocation && (!form.area.trim() || !form.shelf.trim() || !form.bin.trim())) {
      setFormError('أكمل المنطقة والرف والخانة معًا، أو اترك موقع التخزين فارغًا.');
      return;
    }
    const storage_location = hasLocation ? { area: form.area.trim(), shelf: form.shelf.trim(), bin: form.bin.trim() } : null;
    const data = {
      code: form.code.trim(),
      name: form.name.trim(),
      description: form.description.trim(),
      category: form.category.trim(),
      unit: form.unit.trim(),
      part_number: form.part_number.trim() || null,
      minimum_level: Number(form.minimum_level) || 0,
      warehouse_id: Number(form.warehouse_id),
      storage_location,
      requires_serial_number: form.requires_serial_number,
      requires_expiry_date: form.requires_expiry_date,
      is_active: form.is_active,
    };
    const options = {
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: getListItemsQueryKey() });
        setModal(null); setSelected(null); setForm(blankForm);
      },
      onError: (error: unknown) => {
        setFormError(errorMessage(error, 'تعذر حفظ الصنف.'));
        if ((error as { status?: number })?.status === 401) setLocation('/login');
      },
    };
    if (modal === 'create') createItem.mutate({ data }, options);
    else if (selected) updateItem.mutate({ itemId: selected.id, data }, options);
  };

  useEffect(() => {
    if ((items.error as { status?: number })?.status === 401 || (warehouses.error as { status?: number })?.status === 401) setLocation('/login');
  }, [items.error, setLocation, warehouses.error]);

  return (
    <div className="space-y-7">
      <header className="flex flex-col justify-between gap-5 border-b border-border pb-7 sm:flex-row sm:items-end">
        <div><p className="mb-3 font-mono text-[10px] tracking-[0.18em] text-primary">دليل التشغيل / 06</p><h1 className="text-3xl font-bold tracking-tight text-foreground">الأصناف</h1><p className="mt-2 text-sm text-muted-foreground">دليل المواد مع مخزنها وموقعها واحتياجات التتبع.</p></div>
        <Button testId="button-create-item" onClick={openCreate}><Plus className="h-4 w-4" /> صنف جديد</Button>
      </header>
      <div className="grid gap-3 md:grid-cols-[1fr_190px_160px]">
        <label className="relative block"><Search className="pointer-events-none absolute right-3 top-3 h-4 w-4 text-muted-foreground" /><input type="search" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="ابحث بالكود أو الاسم أو التصنيف أو Part Number" data-testid="input-search-items" className="h-10 w-full rounded-md border border-input bg-card pr-9 pl-3 text-sm outline-none transition-[border-color,box-shadow] focus:border-primary focus:ring-2 focus:ring-primary/20" /></label>
        <select value={warehouseFilter} onChange={(event) => setWarehouseFilter(event.target.value)} data-testid="select-filter-items-warehouse" className="h-10 rounded-md border border-input bg-card px-3 text-sm text-foreground outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"><option value="">كل المخازن</option>{(warehouses.data || []).map((warehouse) => <option key={warehouse.id} value={warehouse.id}>{warehouse.name}</option>)}</select>
        <select value={activeFilter} onChange={(event) => setActiveFilter(event.target.value)} data-testid="select-filter-items-status" className="h-10 rounded-md border border-input bg-card px-3 text-sm text-foreground outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"><option value="all">كل الحالات</option><option value="active">نشط فقط</option><option value="inactive">معطل فقط</option></select>
      </div>
      <div className="flex items-center justify-between text-sm text-muted-foreground"><div><span className="font-mono text-2xl font-semibold text-foreground" data-testid="text-items-count">{items.data?.length ?? '—'}</span><span className="mr-2">صنف في النتيجة</span></div><span className="inline-flex items-center gap-2 text-xs"><SlidersHorizontal className="h-4 w-4" /> الفلاتر تطبق مباشرة من الخادم</span></div>
      <section className="overflow-hidden rounded-lg border border-border bg-card">
        <div className="hidden grid-cols-[100px_minmax(180px,1.4fr)_120px_140px_160px_100px_90px] gap-4 border-b border-border bg-secondary/50 px-5 py-3 text-[11px] font-semibold text-muted-foreground xl:grid"><span>الكود</span><span>الصنف</span><span>التصنيف</span><span>المخزن</span><span>الموقع</span><span>الحالة</span><span /></div>
        {items.isLoading ? <LoadingRows count={5} /> : items.isError ? <ErrorState onRetry={() => items.refetch()} message={(items.error as { status?: number })?.status === 403 ? 'لا تملك صلاحية عرض الأصناف.' : undefined} /> : !items.data?.length ? <EmptyState title="لا توجد أصناف" description={search || warehouseFilter || activeFilter !== 'all' ? 'لا توجد أصناف مطابقة للفلاتر الحالية.' : 'أضف أول صنف إلى دليل المواد.'} action={!search && !warehouseFilter && activeFilter === 'all' ? <Button testId="button-empty-create-item" onClick={openCreate}><Plus className="h-4 w-4" /> إضافة صنف</Button> : undefined} /> : items.data.map((item) => (
          <div key={item.id} className="grid grid-cols-[100px_minmax(180px,1.4fr)_120px_140px_160px_100px_90px] items-center gap-4 border-b border-border px-5 py-4 last:border-0 max-xl:block max-xl:space-y-4" data-testid={`row-item-${item.id}`}>
            <div><span className="mb-1 block text-[10px] text-muted-foreground/60 xl:hidden">الكود</span><span className="font-mono text-xs font-semibold">{item.code}</span></div>
            <div className="flex items-center gap-3"><span className="flex h-9 w-9 items-center justify-center rounded-md bg-primary/10 text-primary"><Archive className="h-4 w-4" /></span><div><p className="text-sm font-bold">{item.name}</p><p className="mt-1 text-xs text-muted-foreground">{item.unit}{item.part_number ? ` · ${item.part_number}` : ''}</p></div></div>
            <div className="text-sm text-muted-foreground"><span className="mb-1 block text-[10px] text-muted-foreground/60 xl:hidden">التصنيف</span>{item.category || 'غير مصنف'}</div>
            <div className="text-sm text-muted-foreground"><span className="mb-1 block text-[10px] text-muted-foreground/60 xl:hidden">المخزن</span>{item.warehouse_name}</div>
            <div className="text-sm text-muted-foreground"><span className="mb-1 block text-[10px] text-muted-foreground/60 xl:hidden">الموقع</span><span className="font-mono text-[11px]">{locationText(item)}</span></div>
            <div><span className="mb-1 block text-[10px] text-muted-foreground/60 xl:hidden">الحالة</span><StatusPill active={item.is_active} /></div>
            <div className="text-left"><button type="button" onClick={() => openEdit(item)} data-testid={`button-edit-item-${item.id}`} className="inline-flex items-center gap-1.5 rounded-md px-2.5 py-2 text-xs font-semibold text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"><Pencil className="h-3.5 w-3.5" /> تعديل</button></div>
          </div>
        ))}
      </section>
      <div className="flex items-center gap-2 text-xs text-muted-foreground"><Check className="h-4 w-4 text-accent" /><span>لا يحتوي دليل الأصناف على Barcode؛ يتم استخدام كود الصنف وPart Number عند الحاجة.</span></div>
      {modal && <Modal title={modal === 'create' ? 'إضافة صنف' : 'تعديل الصنف'} eyebrow={modal === 'create' ? 'دليل الأصناف / 01' : `صنف #${selected?.id}`} onClose={closeModal}>
        {formError && <div className="mb-5"><Notice>{formError}</Notice></div>}
        <form onSubmit={submit} className="space-y-5">
          <div className="grid gap-5 sm:grid-cols-2"><Field label="كود الصنف" name="code" value={form.code} onChange={(value) => setField('code', value)} placeholder="مثال: MAT-001" required /><Field label="اسم الصنف" name="name" value={form.name} onChange={(value) => setField('name', value)} placeholder="الاسم المعتمد للمادة" required /></div>
          <div className="grid gap-5 sm:grid-cols-2"><Field label="التصنيف" name="category" value={form.category} onChange={(value) => setField('category', value)} placeholder="مثال: قطع غيار" /><Field label="الوحدة" name="unit" value={form.unit} onChange={(value) => setField('unit', value)} placeholder="مثال: قطعة / كرتون" required /></div>
          <div className="grid gap-5 sm:grid-cols-2"><Field label="Part Number (اختياري)" name="part_number" value={form.part_number} onChange={(value) => setField('part_number', value)} placeholder="الرقم من الشركة المصنّعة" /><Field label="الحد الأدنى" name="minimum_level" type="number" value={form.minimum_level} onChange={(value) => setField('minimum_level', value)} placeholder="0" /></div>
          <Field label="الوصف" name="description" value={form.description} onChange={(value) => setField('description', value)} placeholder="وصف مختصر للصنف" />
          <SelectField label="المخزن" name="warehouse_id" value={form.warehouse_id} onChange={(value) => setField('warehouse_id', value)} required options={(warehouses.data || []).map((warehouse: Warehouse) => ({ value: String(warehouse.id), label: `${warehouse.name}${warehouse.is_active ? '' : ' — معطل'}` }))} />
          <div className="rounded-md border border-border bg-secondary/25 p-4"><div className="mb-4"><p className="text-sm font-bold">موقع التخزين</p><p className="mt-1 text-xs text-muted-foreground">اختياري، لكن يجب إدخال المنطقة والرف والخانة معًا.</p></div><div className="grid gap-4 sm:grid-cols-3"><Field label="المنطقة" name="area" value={form.area} onChange={(value) => setField('area', value)} placeholder="A" /><Field label="الرف" name="shelf" value={form.shelf} onChange={(value) => setField('shelf', value)} placeholder="R-01" /><Field label="الخانة" name="bin" value={form.bin} onChange={(value) => setField('bin', value)} placeholder="B-04" /></div></div>
          <div className="grid gap-3 sm:grid-cols-3"><label className="flex cursor-pointer items-center justify-between gap-3 rounded-md border border-border bg-secondary/40 px-3 py-3 text-sm"><span><span className="block font-semibold">رقم تسلسلي</span><span className="mt-1 block text-xs text-muted-foreground">يتطلب تتبعًا فرديًا</span></span><input type="checkbox" checked={form.requires_serial_number} onChange={(event) => setField('requires_serial_number', event.target.checked)} data-testid="input-item-requires-serial" className="h-4 w-4 accent-[hsl(var(--primary))]" /></label><label className="flex cursor-pointer items-center justify-between gap-3 rounded-md border border-border bg-secondary/40 px-3 py-3 text-sm"><span><span className="block font-semibold">تاريخ انتهاء</span><span className="mt-1 block text-xs text-muted-foreground">يتطلب تتبع الصلاحية</span></span><input type="checkbox" checked={form.requires_expiry_date} onChange={(event) => setField('requires_expiry_date', event.target.checked)} data-testid="input-item-requires-expiry" className="h-4 w-4 accent-[hsl(var(--primary))]" /></label><label className="flex cursor-pointer items-center justify-between gap-3 rounded-md border border-border bg-secondary/40 px-3 py-3 text-sm"><span><span className="block font-semibold">الصنف نشط</span><span className="mt-1 block text-xs text-muted-foreground">يمكن استخدامه في العمليات</span></span><input type="checkbox" checked={form.is_active} onChange={(event) => setField('is_active', event.target.checked)} data-testid="input-item-active" className="h-4 w-4 accent-[hsl(var(--primary))]" /></label></div>
          <div className="flex flex-col-reverse gap-3 pt-2 sm:flex-row"><Button type="submit" testId="button-save-item" disabled={createItem.isPending || updateItem.isPending || warehouses.isLoading}>{createItem.isPending || updateItem.isPending ? 'جارٍ الحفظ...' : 'حفظ الصنف'}</Button><Button type="button" variant="secondary" testId="button-cancel-item" onClick={closeModal}>إلغاء</Button></div>
        </form>
      </Modal>}
    </div>
  );
}