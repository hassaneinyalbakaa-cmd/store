import { useEffect, useMemo, useState, type FormEvent } from 'react';
import { CalendarDays, ClipboardPlus, Eye, FileText, Hash, MapPin, PackageCheck, Plus, ScanLine, Trash2, Truck } from 'lucide-react';
import { useLocation } from 'wouter';
import { useQueryClient } from '@tanstack/react-query';
import {
  getGetReceiptQueryKey,
  getListInventoryBalancesQueryKey,
  getListInventoryExpiryQueryKey,
  getListInventoryMovementsQueryKey,
  getListReceiptsQueryKey,
  useCreateReceipt,
  useGetReceipt,
  useListItems,
  useListReceipts,
  useListWarehouses,
} from '@workspace/api-client-react';
import type { Item, Receipt, ReceiptDetailInput, Warehouse } from '@workspace/api-client-react';
import { Button, EmptyState, ErrorState, Field, LoadingRows, Modal, Notice, SelectField } from '@/components/ui';

type DetailDraft = {
  item_id: string;
  quantity: string;
  warehouse_id: string;
  area: string;
  shelf: string;
  bin: string;
  expiry_date: string;
  serialText: string;
};

type ReceiptDraft = {
  receipt_date: string;
  supplier: string;
  document_number: string;
  notes: string;
  details: DetailDraft[];
};

const today = () => new Date().toISOString().slice(0, 10);
const blankDetail = (): DetailDraft => ({ item_id: '', quantity: '1', warehouse_id: '', area: '', shelf: '', bin: '', expiry_date: '', serialText: '' });
const blankDraft = (): ReceiptDraft => ({ receipt_date: today(), supplier: '', document_number: '', notes: '', details: [blankDetail()] });

function errorMessage(error: unknown, fallback: string) {
  const typed = error as { status?: number; detail?: string; response?: { data?: { detail?: string } } };
  if (typed?.status === 401) return 'انتهت الجلسة. سجّل الدخول من جديد للمتابعة.';
  if (typed?.status === 403) return 'لا تملك صلاحية تنفيذ هذا الإجراء.';
  return typed?.detail || typed?.response?.data?.detail || fallback;
}

function formatDate(value: string) {
  if (!value) return '—';
  return new Intl.DateTimeFormat('ar', { dateStyle: 'medium' }).format(new Date(value));
}

function locationText(detail: { storage_location: { area: string; shelf: string; bin: string } | null }) {
  return detail.storage_location ? `${detail.storage_location.area} / ${detail.storage_location.shelf} / ${detail.storage_location.bin}` : 'بدون موقع محدد';
}

function serialsFromText(value: string) {
  return value.split(/[\n,،]+/).map((serial) => serial.trim()).filter(Boolean);
}

function ReceiptRow({ receipt, onOpen }: { receipt: Receipt; onOpen: (receipt: Receipt) => void }) {
  const total = receipt.details.reduce((sum, detail) => sum + detail.quantity, 0);
  return (
    <button type="button" onClick={() => onOpen(receipt)} data-testid={`row-receipt-${receipt.id}`} className="grid w-full gap-4 border-b border-border px-5 py-4 text-right transition-colors hover:bg-secondary/40 md:grid-cols-[125px_minmax(170px,1.4fr)_150px_120px_110px_70px] md:items-center">
      <span className="font-mono text-xs font-semibold text-foreground">{receipt.receipt_number}</span>
      <span className="flex min-w-0 items-center gap-3"><span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-primary/10 text-primary"><Truck className="h-4 w-4" /></span><span className="min-w-0"><span className="block truncate text-sm font-bold">{receipt.supplier}</span><span className="mt-1 block truncate text-xs text-muted-foreground">{receipt.document_number || 'دون رقم مستند'}</span></span></span>
      <span className="text-sm text-muted-foreground"><span className="mb-1 block text-[10px] text-muted-foreground/60 md:hidden">تاريخ الاستلام</span>{formatDate(receipt.receipt_date)}</span>
      <span className="text-sm text-muted-foreground"><span className="mb-1 block text-[10px] text-muted-foreground/60 md:hidden">التفاصيل</span>{receipt.details.length} تفاصيل</span>
      <span className="font-mono text-sm text-foreground"><span className="mb-1 block font-sans text-[10px] text-muted-foreground/60 md:hidden">الكمية</span>{total.toLocaleString('ar')}</span>
      <span className="text-left text-muted-foreground"><Eye className="mr-auto h-4 w-4" /></span>
    </button>
  );
}

function DetailEditor({ detail, index, items, warehouses, onChange, onRemove, canRemove }: {
  detail: DetailDraft;
  index: number;
  items: Item[];
  warehouses: Warehouse[];
  onChange: (key: keyof DetailDraft, value: string) => void;
  onRemove: () => void;
  canRemove: boolean;
}) {
  const item = items.find((candidate) => String(candidate.id) === detail.item_id);
  const serials = serialsFromText(detail.serialText);
  const quantity = Number(detail.quantity);
  const serialIssue = item?.requires_serial_number && (!Number.isInteger(quantity) || serials.length !== quantity || new Set(serials).size !== serials.length);
  return (
    <div className="space-y-4 rounded-lg border border-border bg-secondary/20 p-4" data-testid={`receipt-detail-${index}`}>
      <div className="flex items-start justify-between gap-4"><div><p className="font-mono text-[10px] tracking-[0.16em] text-primary">تفصيل {String(index + 1).padStart(2, '0')}</p><p className="mt-1 text-sm font-bold">بيانات الصنف وموقعه</p></div>{canRemove && <button type="button" onClick={onRemove} data-testid={`button-remove-receipt-detail-${index}`} className="rounded-md p-2 text-muted-foreground transition-colors hover:bg-destructive/10 hover:text-destructive" aria-label="حذف التفصيل"><Trash2 className="h-4 w-4" /></button>}</div>
      <SelectField label="الصنف" name={`detail-item-${index}`} value={detail.item_id} onChange={(value) => onChange('item_id', value)} required options={items.filter((candidate) => candidate.is_active).map((candidate) => ({ value: String(candidate.id), label: `${candidate.code} — ${candidate.name}` }))} />
      {item && <div className="flex flex-wrap items-center gap-2 text-[11px]"><span className="rounded-full border border-primary/20 bg-primary/10 px-2 py-1 font-semibold text-primary">{item.unit}</span>{item.requires_serial_number && <span className="rounded-full border border-accent/20 bg-accent/10 px-2 py-1 font-semibold text-accent">تتبع تسلسلي</span>}{item.requires_expiry_date && <span className="rounded-full border border-destructive/20 bg-destructive/10 px-2 py-1 font-semibold text-destructive">تاريخ انتهاء مطلوب</span>}</div>}
      <div className="grid gap-4 sm:grid-cols-2"><Field label="الكمية" name={`detail-quantity-${index}`} type="number" value={detail.quantity} onChange={(value) => onChange('quantity', value)} required hint={item ? `الوحدة: ${item.unit}` : 'أدخل عدد الوحدات'} /><SelectField label="المخزن" name={`detail-warehouse-${index}`} value={detail.warehouse_id} onChange={(value) => onChange('warehouse_id', value)} required options={warehouses.filter((warehouse) => warehouse.is_active).map((warehouse) => ({ value: String(warehouse.id), label: `${warehouse.name} (${warehouse.code})` }))} /></div>
      <div className="rounded-md border border-border bg-card/70 p-3"><div className="mb-3 flex items-center gap-2"><MapPin className="h-4 w-4 text-primary" /><div><p className="text-xs font-bold">موقع التخزين <span className="font-normal text-muted-foreground">(اختياري)</span></p><p className="text-[11px] text-muted-foreground">اترك الحقول الثلاثة فارغة أو أكملها معًا.</p></div></div><div className="grid gap-3 sm:grid-cols-3"><Field label="المنطقة" name={`detail-area-${index}`} value={detail.area} onChange={(value) => onChange('area', value)} placeholder="A" /><Field label="الرف" name={`detail-shelf-${index}`} value={detail.shelf} onChange={(value) => onChange('shelf', value)} placeholder="R-01" /><Field label="الخانة" name={`detail-bin-${index}`} value={detail.bin} onChange={(value) => onChange('bin', value)} placeholder="B-04" /></div></div>
      <div className="grid gap-4 sm:grid-cols-2"><Field label="تاريخ الانتهاء" name={`detail-expiry-${index}`} type="date" value={detail.expiry_date} onChange={(value) => onChange('expiry_date', value)} required={Boolean(item?.requires_expiry_date)} hint={item?.requires_expiry_date ? 'هذا الصنف يتطلب تاريخ انتهاء.' : 'اختياري عند توفره.'} />{item?.requires_serial_number && <label className="block space-y-2 text-right"><span className="flex items-center justify-between text-sm font-semibold"><span>الأرقام التسلسلية</span><span className="font-mono text-[10px] text-muted-foreground">لكل وحدة</span></span><textarea name={`detail-serials-${index}`} value={detail.serialText} onChange={(event) => onChange('serialText', event.target.value)} data-testid={`input-detail-serials-${index}`} rows={3} placeholder="رقم واحد في كل سطر" className={`w-full resize-y rounded-md border bg-card px-3 py-2 text-sm outline-none transition-[border-color,box-shadow] focus:border-primary focus:ring-2 focus:ring-primary/20 ${serialIssue ? 'border-destructive' : 'border-input'}`} /><span className={`block text-xs leading-5 ${serialIssue ? 'text-destructive' : 'text-muted-foreground'}`}>{serialIssue ? `أدخل ${quantity > 0 ? quantity : 'عدد'} أرقام فريدة، رقمًا لكل وحدة.` : `${serials.length} من ${Number.isInteger(quantity) && quantity > 0 ? quantity : '—'} رقم مدخل`}</span></label>}</div>
    </div>
  );
}

export default function ReceiptsPage({ canWrite = true }: { canWrite?: boolean }) {
  const [, setLocation] = useLocation();
  const queryClient = useQueryClient();
  const receipts = useListReceipts({ request: { credentials: 'include' } });
  const items = useListItems({ isActive: true }, { request: { credentials: 'include' } });
  const warehouses = useListWarehouses({ request: { credentials: 'include' } });
  const createReceipt = useCreateReceipt({ request: { credentials: 'include' } });
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [selectedReceiptId, setSelectedReceiptId] = useState<number | null>(null);
  const [draft, setDraft] = useState<ReceiptDraft>(blankDraft);
  const [formError, setFormError] = useState('');
  const detail = useGetReceipt(selectedReceiptId ?? 0, { request: { credentials: 'include' }, query: { enabled: Boolean(selectedReceiptId), queryKey: getGetReceiptQueryKey(selectedReceiptId ?? 0) } });
  const activeItems = useMemo(() => items.data || [], [items.data]);

  useEffect(() => {
    const errors = [receipts.error, items.error, warehouses.error];
    if (errors.some((error) => (error as { status?: number } | null)?.status === 401)) setLocation('/login');
  }, [items.error, receipts.error, setLocation, warehouses.error]);

  const openCreate = () => {
    setDraft(blankDraft());
    setFormError('');
    setIsCreateOpen(true);
  };
  const closeCreate = () => { if (!createReceipt.isPending) setIsCreateOpen(false); };
  const updateDetail = (index: number, key: keyof DetailDraft, value: string) => setDraft((current) => ({ ...current, details: current.details.map((detail, detailIndex) => detailIndex === index ? { ...detail, [key]: value } : detail) }));
  const addDetail = () => setDraft((current) => ({ ...current, details: [...current.details, blankDetail()] }));
  const removeDetail = (index: number) => setDraft((current) => ({ ...current, details: current.details.filter((_, detailIndex) => detailIndex !== index) }));

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setFormError('');
    if (!draft.receipt_date || !draft.supplier.trim() || !draft.details.length) { setFormError('أكمل تاريخ الاستلام والمورد وأضف تفصيلًا واحدًا على الأقل.'); return; }
    const payload: ReceiptDetailInput[] = [];
    for (let index = 0; index < draft.details.length; index += 1) {
      const current = draft.details[index];
      const item = activeItems.find((candidate) => String(candidate.id) === current.item_id);
      const quantity = Number(current.quantity);
      if (!item || !current.warehouse_id || !Number.isFinite(quantity) || quantity <= 0) { setFormError(`أكمل الصنف والمخزن والكمية الصحيحة في التفصيل ${index + 1}.`); return; }
      if (item.requires_expiry_date && !current.expiry_date) { setFormError(`تاريخ الانتهاء مطلوب للصنف «${item.name}» في التفصيل ${index + 1}.`); return; }
      const serials = serialsFromText(current.serialText);
      if (item.requires_serial_number && (!Number.isInteger(quantity) || serials.length !== quantity || new Set(serials).size !== serials.length)) { setFormError(`أدخل رقمًا تسلسليًا فريدًا لكل وحدة من الصنف «${item.name}».`); return; }
      const hasLocation = Boolean(current.area.trim() || current.shelf.trim() || current.bin.trim());
      if (hasLocation && (!current.area.trim() || !current.shelf.trim() || !current.bin.trim())) { setFormError(`أكمل المنطقة والرف والخانة معًا في التفصيل ${index + 1}.`); return; }
      payload.push({ item_id: item.id, quantity, warehouse_id: Number(current.warehouse_id), storage_location: hasLocation ? { area: current.area.trim(), shelf: current.shelf.trim(), bin: current.bin.trim() } : null, expiry_date: current.expiry_date || null, serial_numbers: item.requires_serial_number ? serials : [] });
    }
    createReceipt.mutate({ data: { receipt_date: draft.receipt_date, supplier: draft.supplier.trim(), document_number: draft.document_number.trim(), notes: draft.notes.trim(), details: payload } }, {
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: getListReceiptsQueryKey() });
        queryClient.invalidateQueries({ queryKey: getListInventoryBalancesQueryKey() });
        queryClient.invalidateQueries({ queryKey: getListInventoryMovementsQueryKey() });
        queryClient.invalidateQueries({ queryKey: getListInventoryExpiryQueryKey() });
        setIsCreateOpen(false);
        setDraft(blankDraft());
      },
      onError: (error: unknown) => { setFormError(errorMessage(error, 'تعذر حفظ سند الاستلام.')); if ((error as { status?: number })?.status === 401) setLocation('/login'); },
    });
  };

  return (
    <div className="space-y-7">
       <header className="flex flex-col justify-between gap-5 border-b border-border pb-7 sm:flex-row sm:items-end"><div><p className="mb-3 font-mono text-[10px] tracking-[0.18em] text-primary">حركة المخزون / 07</p><h1 className="text-3xl font-bold tracking-tight text-foreground sm:text-4xl">سندات الاستلام</h1><p className="mt-2 max-w-2xl text-sm text-muted-foreground">سجّل الوارد كما وصل، مع توثيق المورد والتاريخ وموقع كل وحدة عند الحاجة.</p></div>{canWrite && <Button testId="button-create-receipt" onClick={openCreate}><Plus className="h-4 w-4" /> سند استلام جديد</Button>}</header>
      <div className="grid gap-3 sm:grid-cols-3"><div className="rounded-lg border border-border bg-card p-4"><p className="text-xs text-muted-foreground">إجمالي السندات</p><p className="mt-2 font-mono text-3xl font-semibold" data-testid="text-receipts-count">{receipts.data?.length ?? '—'}</p></div><div className="rounded-lg border border-border bg-card p-4"><p className="text-xs text-muted-foreground">وحدات مستلمة</p><p className="mt-2 font-mono text-3xl font-semibold text-primary" data-testid="text-received-quantity">{receipts.data ? receipts.data.reduce((sum, receipt) => sum + receipt.details.reduce((detailSum, detail) => detailSum + detail.quantity, 0), 0).toLocaleString('ar') : '—'}</p></div><div className="rounded-lg border border-sidebar-border bg-sidebar p-4 text-sidebar-foreground"><div className="flex items-center gap-2 text-sidebar-primary"><ScanLine className="h-4 w-4" /><span className="font-mono text-[10px] tracking-[0.16em]">TRACEABILITY</span></div><p className="mt-3 text-sm leading-6 text-sidebar-foreground/75">الأصناف التي تتطلب تتبعًا ستطلب رقمًا تسلسليًا لكل وحدة قبل الترحيل.</p></div></div>
       <section className="overflow-hidden rounded-lg border border-border bg-card"><div className="hidden grid-cols-[125px_minmax(170px,1.4fr)_150px_120px_110px_70px] gap-4 border-b border-border bg-secondary/50 px-5 py-3 text-[11px] font-semibold text-muted-foreground md:grid"><span>رقم السند</span><span>المورد / المستند</span><span>تاريخ الاستلام</span><span>التفاصيل</span><span>إجمالي الوحدات</span><span /></div>{receipts.isLoading ? <LoadingRows count={5} /> : receipts.isError ? <ErrorState onRetry={() => receipts.refetch()} message={(receipts.error as { status?: number })?.status === 403 ? 'لا تملك صلاحية عرض سندات الاستلام.' : undefined} /> : !receipts.data?.length ? <EmptyState title="لا توجد سندات استلام" description="عند وصول أول شحنة، أنشئ سندًا لتثبيت حركتها في سجل المخزون." action={canWrite ? <Button testId="button-empty-create-receipt" onClick={openCreate}><ClipboardPlus className="h-4 w-4" /> إنشاء أول سند</Button> : undefined} /> : receipts.data.map((receipt) => <ReceiptRow key={receipt.id} receipt={receipt} onOpen={(selected) => setSelectedReceiptId(selected.id)} />)}</section>
      <div className="flex items-center gap-2 text-xs text-muted-foreground"><FileText className="h-4 w-4 text-primary" /><span>كل سند يحفظ كأثر تشغيلي ويرتبط بحركات المخزون الناتجة عنه.</span></div>

      {isCreateOpen && <Modal title="إنشاء سند استلام" eyebrow="حركة المخزون / 01" onClose={closeCreate}><form onSubmit={submit} className="space-y-6">{formError && <Notice>{formError}</Notice>}<div className="grid gap-4 sm:grid-cols-2"><Field label="تاريخ الاستلام" name="receipt-date" type="date" value={draft.receipt_date} onChange={(value) => setDraft((current) => ({ ...current, receipt_date: value }))} required /><Field label="المورد" name="receipt-supplier" value={draft.supplier} onChange={(value) => setDraft((current) => ({ ...current, supplier: value }))} placeholder="اسم الجهة الموردة" required /></div><div className="grid gap-4 sm:grid-cols-2"><Field label="رقم المستند" name="receipt-document-number" value={draft.document_number} onChange={(value) => setDraft((current) => ({ ...current, document_number: value }))} placeholder="رقم فاتورة أو بوليصة" /><Field label="ملاحظات" name="receipt-notes" value={draft.notes} onChange={(value) => setDraft((current) => ({ ...current, notes: value }))} placeholder="معلومة يحتاجها الفريق" /></div><div className="space-y-4"><div className="flex items-center justify-between border-b border-border pb-3"><div><p className="text-sm font-bold">تفاصيل الاستلام</p><p className="mt-1 text-xs text-muted-foreground">أضف سطرًا لكل صنف وموقع مختلف.</p></div><span className="font-mono text-xs text-muted-foreground">{draft.details.length} سطور</span></div>{draft.details.map((detailDraft, index) => <DetailEditor key={index} detail={detailDraft} index={index} items={activeItems} warehouses={warehouses.data || []} onChange={(key, value) => updateDetail(index, key, value)} onRemove={() => removeDetail(index)} canRemove={draft.details.length > 1} />)}<button type="button" onClick={addDetail} data-testid="button-add-receipt-detail" className="flex w-full items-center justify-center gap-2 rounded-md border border-dashed border-primary/40 bg-primary/5 px-4 py-3 text-sm font-semibold text-primary transition-colors hover:bg-primary/10"><Plus className="h-4 w-4" /> إضافة تفصيل آخر</button></div><div className="flex flex-col-reverse gap-3 border-t border-border pt-4 sm:flex-row"><Button type="submit" testId="button-save-receipt" disabled={createReceipt.isPending || items.isLoading || warehouses.isLoading}>{createReceipt.isPending ? 'جارٍ ترحيل السند...' : 'حفظ وترحيل السند'}</Button><Button type="button" variant="secondary" testId="button-cancel-receipt" onClick={closeCreate}>إلغاء</Button></div></form></Modal>}

      {selectedReceiptId && <Modal title={detail.data?.receipt_number || 'تفاصيل سند الاستلام'} eyebrow="سجل الاستلام / عرض" onClose={() => setSelectedReceiptId(null)}>{detail.isLoading ? <LoadingRows count={3} /> : detail.isError ? <ErrorState onRetry={() => detail.refetch()} /> : detail.data ? <div className="space-y-6"><div className="grid gap-3 rounded-md border border-border bg-secondary/25 p-4 sm:grid-cols-3"><div><p className="text-[11px] text-muted-foreground">المورد</p><p className="mt-1 text-sm font-bold">{detail.data.supplier}</p></div><div><p className="text-[11px] text-muted-foreground">تاريخ الاستلام</p><p className="mt-1 text-sm font-semibold">{formatDate(detail.data.receipt_date)}</p></div><div><p className="text-[11px] text-muted-foreground">رقم المستند</p><p className="mt-1 font-mono text-sm">{detail.data.document_number || '—'}</p></div></div><div className="space-y-3">{detail.data.details.map((entry) => <div key={entry.id} className="rounded-md border border-border p-4" data-testid={`receipt-detail-view-${entry.id}`}><div className="flex items-start justify-between gap-4"><div><p className="font-mono text-[11px] text-primary">{entry.item_code}</p><p className="mt-1 text-sm font-bold">{entry.item_name}</p></div><p className="font-mono text-lg font-semibold">{entry.quantity.toLocaleString('ar')}</p></div><div className="mt-3 flex flex-wrap gap-x-4 gap-y-2 text-xs text-muted-foreground"><span className="inline-flex items-center gap-1"><Hash className="h-3.5 w-3.5" />{entry.serial_numbers.length ? `${entry.serial_numbers.length} أرقام تسلسلية` : 'بدون أرقام تسلسلية'}</span><span className="inline-flex items-center gap-1"><MapPin className="h-3.5 w-3.5" />{locationText(entry)}</span><span className="inline-flex items-center gap-1"><CalendarDays className="h-3.5 w-3.5" />{entry.expiry_date ? formatDate(entry.expiry_date) : 'بدون انتهاء'}</span></div>{entry.serial_numbers.length > 0 && <p className="mt-3 border-t border-border pt-3 font-mono text-[11px] leading-6 text-muted-foreground">{entry.serial_numbers.join(' · ')}</p>}</div>)}</div>{detail.data.notes && <div className="rounded-md border border-primary/20 bg-primary/5 p-4 text-sm leading-6"><p className="mb-1 text-xs font-bold text-primary">ملاحظات السند</p>{detail.data.notes}</div>}</div> : null}</Modal>}
    </div>
  );
}