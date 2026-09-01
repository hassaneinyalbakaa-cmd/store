import { useMemo, useState, type FormEvent } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import {
  ArrowLeftRight,
  Check,
  FilePlus2,
  PackageCheck,
  Send,
  ShieldCheck,
} from 'lucide-react';
import {
  getGetTransferQueryKey,
  getGetTransferReceivePreviewQueryKey,
  getListInventoryBalancesQueryKey,
  getListInventoryMovementsQueryKey,
  getListTransfersQueryKey,
  useCreateTransfer,
  useGetTransfer,
  useGetTransferReceivePreview,
  useListItems,
  useListTransfers,
  useListWarehouses,
  useReceiveTransfer,
  useCompleteTransfer,
  useSendTransfer,
} from '@workspace/api-client-react';
import type { StockTransfer, StockTransferPreview } from '@workspace/api-client-react';
import { Button, EmptyState, ErrorState, Field, LoadingRows, Modal, Notice, SelectField } from '@/components/ui';

const credentials = { credentials: 'include' as const };
type Props = { user: { permissions: string[] } };
type Draft = { source: string; destination: string; item: string; quantity: string; reason: string; notes: string };
const blankDraft = (): Draft => ({ source: '', destination: '', item: '', quantity: '1', reason: '', notes: '' });

function errorMessage(error: unknown, fallback: string) {
  const typed = error as { status?: number; detail?: string; response?: { data?: { detail?: string } } };
  if (typed?.status === 401) return 'انتهت الجلسة. سجّل الدخول من جديد للمتابعة.';
  if (typed?.status === 403) return 'لا تملك صلاحية تنفيذ هذا الإجراء.';
  return typed?.detail || typed?.response?.data?.detail || fallback;
}
function dateTime(value: string | null) {
  return value ? new Intl.DateTimeFormat('ar', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value)) : '—';
}
const statusLabels: Record<string, string> = { draft: 'مسودة', sent: 'في الطريق', received: 'تم الاستلام', completed: 'مكتمل' };
const statusStyles: Record<string, string> = {
  draft: 'border-border bg-secondary text-muted-foreground',
  sent: 'border-primary/25 bg-primary/10 text-primary',
  received: 'border-accent/25 bg-accent/10 text-accent',
  completed: 'border-sidebar-primary/30 bg-sidebar/10 text-sidebar',
};
function StatusPill({ status }: { status: string }) {
  return <span className={`inline-flex w-fit rounded-full border px-2.5 py-1 text-[11px] font-semibold ${statusStyles[status] || statusStyles.draft}`} data-testid={`status-transfer-${status}`}>{statusLabels[status] || status}</span>;
}
function TransferRow({ transfer, onOpen }: { transfer: StockTransfer; onOpen: (id: number) => void }) {
  return <button type="button" onClick={() => onOpen(transfer.id)} data-testid={`row-transfer-${transfer.id}`} className="grid w-full gap-3 border-b border-border px-5 py-4 text-right transition-colors hover:bg-secondary/45 last:border-0 md:grid-cols-[145px_minmax(170px,1.25fr)_180px_100px_125px] md:items-center">
    <div><p className="font-mono text-xs font-semibold text-primary">{transfer.transfer_number}</p><p className="mt-1 text-[11px] text-muted-foreground">{dateTime(transfer.created_at)}</p></div>
    <div className="min-w-0"><p className="truncate text-sm font-bold">{transfer.item_name}</p><p className="mt-1 truncate text-xs text-muted-foreground">{transfer.item_code} · {transfer.reason}</p></div>
    <div className="text-sm text-muted-foreground"><span className="mb-1 block text-[10px] text-muted-foreground/60 md:hidden">المسار</span><span>{transfer.source_warehouse_name}</span><span className="mx-2 text-primary">←</span><span>{transfer.destination_warehouse_name}</span></div>
    <div className="font-mono text-base font-semibold">{transfer.quantity.toLocaleString('ar')} <span className="font-sans text-xs font-normal text-muted-foreground">{transfer.item_unit}</span></div>
    <div><StatusPill status={transfer.status} /></div>
  </button>;
}
function TransferForm({ draft, setDraft, warehouses, items, onSubmit, isPending, error }: { draft: Draft; setDraft: (value: Draft) => void; warehouses: { id: number; name: string; code: string; is_active: boolean }[]; items: { id: number; code: string; name: string; unit: string; is_active: boolean }[]; onSubmit: (event: FormEvent<HTMLFormElement>) => void; isPending: boolean; error: string }) {
  return <form onSubmit={onSubmit} className="space-y-5">
    {error && <Notice>{error}</Notice>}
    <Notice tone="info">ستُحفظ الحركة كمسودة. لا يتغير رصيد أي مخزن حتى يؤكد المخزن الوجهة الاستلام.</Notice>
    <div className="grid gap-4 sm:grid-cols-2">
      <SelectField label="المخزن المصدر" name="transfer-source" value={draft.source} onChange={(value) => setDraft({ ...draft, source: value })} required options={warehouses.filter((warehouse) => warehouse.is_active).map((warehouse) => ({ value: String(warehouse.id), label: `${warehouse.name} (${warehouse.code})` }))} />
      <SelectField label="المخزن الوجهة" name="transfer-destination" value={draft.destination} onChange={(value) => setDraft({ ...draft, destination: value })} required options={warehouses.filter((warehouse) => warehouse.is_active).map((warehouse) => ({ value: String(warehouse.id), label: `${warehouse.name} (${warehouse.code})` }))} />
    </div>
    <SelectField label="الصنف" name="transfer-item" value={draft.item} onChange={(value) => setDraft({ ...draft, item: value })} required options={items.filter((item) => item.is_active).map((item) => ({ value: String(item.id), label: `${item.code} — ${item.name} (${item.unit})` }))} />
    <div className="grid gap-4 sm:grid-cols-2">
      <Field label="الكمية" name="transfer-quantity" type="number" value={draft.quantity} onChange={(value) => setDraft({ ...draft, quantity: value })} required hint="يجب أن تكون أكبر من صفر." />
      <Field label="سبب النقل" name="transfer-reason" value={draft.reason} onChange={(value) => setDraft({ ...draft, reason: value })} required placeholder="مثال: تغذية مخزون الفرع" />
    </div>
    <Field label="ملاحظات" name="transfer-notes" value={draft.notes} onChange={(value) => setDraft({ ...draft, notes: value })} placeholder="مرجع أو تعليمات التسليم (اختياري)" />
    <Button type="submit" testId="button-save-transfer" disabled={isPending}><FilePlus2 className="h-4 w-4" />{isPending ? 'جارٍ حفظ المسودة...' : 'حفظ كمسودة'}</Button>
  </form>;
}
function Metric({ label, value, unit, tone = 'default' }: { label: string; value: number; unit?: string; tone?: 'default' | 'primary' | 'accent' | 'danger' }) {
  const color = { default: 'text-foreground', primary: 'text-primary', accent: 'text-accent', danger: 'text-destructive' }[tone];
  return <div className="rounded-md border border-border bg-secondary/35 p-4"><p className="text-[11px] text-muted-foreground">{label}</p><p className={`mt-2 font-mono text-2xl font-semibold ${color}`}>{value.toLocaleString('ar')} <span className="font-sans text-xs font-normal text-muted-foreground">{unit}</span></p></div>;
}
function DetailModal({ transfer, onClose, onSend, onReceive, onComplete, canWrite, canReceive, pending, error }: { transfer: StockTransfer; onClose: () => void; onSend: () => void; onReceive: () => void; onComplete: () => void; canWrite: boolean; canReceive: boolean; pending: boolean; error: string }) {
  return <Modal title={transfer.transfer_number} eyebrow="سجل حركة بين المخازن" onClose={onClose}><div className="space-y-5">
    {error && <Notice>{error}</Notice>}
    <div className="flex flex-wrap items-center justify-between gap-3"><StatusPill status={transfer.status} /><span className="font-mono text-xs text-muted-foreground">{dateTime(transfer.created_at)}</span></div>
    <div className="grid gap-3 sm:grid-cols-2"><div className="rounded-md border border-border bg-secondary/35 p-4"><p className="text-[11px] text-muted-foreground">المسار المصدر</p><p className="mt-2 text-sm font-bold">{transfer.source_warehouse_name}</p><p className="mt-1 text-xs text-muted-foreground">الرصيد الحالي: {transfer.current_source_balance.toLocaleString('ar')} {transfer.item_unit}</p></div><div className="rounded-md border border-border bg-secondary/35 p-4"><p className="text-[11px] text-muted-foreground">المسار الوجهة</p><p className="mt-2 text-sm font-bold">{transfer.destination_warehouse_name}</p><p className="mt-1 text-xs text-muted-foreground">لا يضاف شيء قبل تأكيد الاستلام</p></div></div>
    <div className="grid gap-3 sm:grid-cols-3"><Metric label="الصنف" value={transfer.quantity} unit={transfer.item_name} tone="primary" /><Metric label="الكمية" value={transfer.quantity} unit={transfer.item_unit} /><Metric label="المتاح من المصدر" value={transfer.available_quantity} unit={transfer.item_unit} tone={transfer.available_quantity < transfer.quantity ? 'danger' : 'accent'} /></div>
    <dl className="grid gap-4 border-y border-border py-4 text-sm sm:grid-cols-2"><div><dt className="text-xs text-muted-foreground">السبب</dt><dd className="mt-1 font-medium">{transfer.reason}</dd></div><div><dt className="text-xs text-muted-foreground">أنشأها</dt><dd className="mt-1 font-medium">{transfer.created_by_name}</dd></div>{transfer.notes && <div className="sm:col-span-2"><dt className="text-xs text-muted-foreground">ملاحظات</dt><dd className="mt-1 leading-6">{transfer.notes}</dd></div>}<div><dt className="text-xs text-muted-foreground">وقت الإرسال</dt><dd className="mt-1">{dateTime(transfer.sent_at)}</dd></div><div><dt className="text-xs text-muted-foreground">وقت الاستلام</dt><dd className="mt-1">{dateTime(transfer.received_at)}</dd></div></dl>
    {transfer.serial_numbers.length > 0 && <div className="rounded-md border border-accent/25 bg-accent/5 p-4"><p className="text-xs font-bold text-accent">الأرقام التسلسلية المسجلة</p><div className="mt-3 flex flex-wrap gap-2">{transfer.serial_numbers.map((serial) => <span className="rounded bg-card px-2 py-1 font-mono text-xs" key={serial} data-testid={`text-transfer-serial-${serial}`}>{serial}</span>)}</div></div>}
    <div className="flex flex-wrap gap-2 border-t border-border pt-4">{transfer.status === 'draft' && canWrite && <Button testId={`button-send-transfer-${transfer.id}`} onClick={onSend} disabled={pending}><Send className="h-4 w-4" /> إرسال للمخزن الوجهة</Button>}{transfer.status === 'sent' && canReceive && <Button testId={`button-receive-transfer-${transfer.id}`} onClick={onReceive} disabled={pending}><PackageCheck className="h-4 w-4" /> تأكيد الاستلام</Button>}{transfer.status === 'received' && canReceive && <Button testId={`button-complete-transfer-${transfer.id}`} onClick={onComplete} disabled={pending}><Check className="h-4 w-4" /> إكمال الحركة</Button>}{transfer.status === 'completed' && <span className="inline-flex items-center gap-2 rounded-md bg-secondary px-3 py-2 text-xs font-semibold text-muted-foreground"><ShieldCheck className="h-4 w-4 text-accent" /> حركة مكتملة وموثقة</span>}</div>
  </div></Modal>;
}
function ReceiveModal({ preview, selected, setSelected, onClose, onConfirm, pending, error }: { preview: StockTransferPreview; selected: string[]; setSelected: (value: string[]) => void; onClose: () => void; onConfirm: () => void; pending: boolean; error: string }) {
  const required = preview.quantity;
  const ready = !preview.requires_serial_number || (selected.length === required && new Set(selected).size === selected.length);
  const toggle = (serial: string) => setSelected(selected.includes(serial) ? selected.filter((entry) => entry !== serial) : [...selected, serial]);
  return <Modal title={`استلام ${preview.transfer_number}`} eyebrow="تحقق قبل تحديث أرصدة المخزون" onClose={onClose}><div className="space-y-5">
    {error && <Notice>{error}</Notice>}
    <Notice tone="info">تأكيد الاستلام هو الخطوة الوحيدة التي تسجل خصمًا من المصدر وإضافة إلى الوجهة. راجع الكمية قبل المتابعة.</Notice>
    <div className="grid gap-3 sm:grid-cols-3"><Metric label="الرصيد الحالي" value={preview.current_source_balance} unit={preview.item_unit} /><Metric label="الكمية المنقولة" value={preview.quantity} unit={preview.item_unit} tone="primary" /><Metric label="المتاح" value={preview.available_quantity} unit={preview.item_unit} tone={preview.available_quantity < required ? 'danger' : 'accent'} /></div>
    <div className="rounded-md border border-border bg-secondary/35 p-4"><p className="font-bold">{preview.item_name}</p><p className="mt-1 text-xs text-muted-foreground">{preview.source_warehouse_name} ← {preview.destination_warehouse_name} · {preview.item_code}</p></div>
    {preview.requires_serial_number ? <div className="space-y-3"><div className="flex items-center justify-between"><p className="text-sm font-bold">الأرقام التسلسلية المتاحة</p><span className={`font-mono text-xs ${ready ? 'text-accent' : 'text-destructive'}`}>{selected.length} / {required}</span></div><p className="text-xs leading-5 text-muted-foreground">اختر عددًا مساويًا تمامًا لكمية النقل، ومن القائمة المتاحة في المخزن المصدر.</p><div className="grid max-h-56 gap-2 overflow-y-auto rounded-md border border-border p-3 sm:grid-cols-2">{preview.available_serial_numbers.map((serial) => <label key={serial} className={`flex cursor-pointer items-center gap-3 rounded-md border px-3 py-2 text-sm ${selected.includes(serial) ? 'border-primary bg-primary/8' : 'border-border bg-card'}`}><input type="checkbox" checked={selected.includes(serial)} onChange={() => toggle(serial)} data-testid={`checkbox-transfer-serial-${serial}`} className="h-4 w-4 accent-[hsl(var(--primary))]" /><span className="font-mono">{serial}</span></label>)}</div></div> : <Notice tone="success">هذا الصنف لا يحتاج أرقامًا تسلسلية. يمكن تأكيد الكمية المعروضة.</Notice>}
    <Button testId={`button-confirm-receive-transfer-${preview.transfer_id}`} onClick={onConfirm} disabled={!ready || pending}><PackageCheck className="h-4 w-4" />{pending ? 'جارٍ تسجيل الاستلام...' : 'تأكيد الاستلام وتحديث المخزون'}</Button>
  </div></Modal>;
}
export default function TransfersPage({ user }: Props) {
  const queryClient = useQueryClient();
  const transfers = useListTransfers({ request: credentials });
  const warehouses = useListWarehouses({ request: credentials });
  const items = useListItems({ isActive: true }, { request: credentials });
  const create = useCreateTransfer({ request: credentials });
  const send = useSendTransfer({ request: credentials });
  const receive = useReceiveTransfer({ request: credentials });
  const complete = useCompleteTransfer({ request: credentials });
  const [createOpen, setCreateOpen] = useState(false);
  const [draft, setDraft] = useState<Draft>(blankDraft);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [receiveId, setReceiveId] = useState<number | null>(null);
  const [selectedSerials, setSelectedSerials] = useState<string[]>([]);
  const [error, setError] = useState('');
  const [formError, setFormError] = useState('');
  const detail = useGetTransfer(selectedId ?? 0, { request: credentials, query: { enabled: selectedId !== null, queryKey: getGetTransferQueryKey(selectedId ?? 0) } });
  const preview = useGetTransferReceivePreview(receiveId ?? 0, { request: credentials, query: { enabled: receiveId !== null, queryKey: getGetTransferReceivePreviewQueryKey(receiveId ?? 0) } });
  const counts = useMemo(() => (transfers.data || []).reduce<Record<string, number>>((result, transfer) => { result[transfer.status] = (result[transfer.status] || 0) + 1; return result; }, {}), [transfers.data]);
  const invalidate = (id?: number) => { queryClient.invalidateQueries({ queryKey: getListTransfersQueryKey() }); queryClient.invalidateQueries({ queryKey: getListInventoryBalancesQueryKey() }); queryClient.invalidateQueries({ queryKey: getListInventoryMovementsQueryKey() }); if (id !== undefined) { queryClient.invalidateQueries({ queryKey: getGetTransferQueryKey(id) }); queryClient.invalidateQueries({ queryKey: getGetTransferReceivePreviewQueryKey(id) }); } };
  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); setFormError('');
    const quantity = Number(draft.quantity);
    if (!draft.source || !draft.destination || draft.source === draft.destination || !draft.item || !draft.reason.trim() || !Number.isFinite(quantity) || quantity <= 0) { setFormError('أكمل الحقول المطلوبة، وتأكد من اختلاف المصدر عن الوجهة والكمية الأكبر من صفر.'); return; }
    create.mutate({ data: { source_warehouse_id: Number(draft.source), destination_warehouse_id: Number(draft.destination), item_id: Number(draft.item), quantity, reason: draft.reason.trim(), notes: draft.notes.trim() } }, { onSuccess: (created) => { invalidate(created.id); setCreateOpen(false); setDraft(blankDraft()); setSelectedId(created.id); }, onError: (reason) => setFormError(errorMessage(reason, 'تعذر حفظ مسودة النقل.')) });
  };
  const action = (kind: 'send' | 'complete', id: number) => { setError(''); const mutation = kind === 'send' ? send : complete; mutation.mutate(kind === 'send' ? { transferId: id } : { transferId: id }, { onSuccess: () => invalidate(id), onError: (reason) => setError(errorMessage(reason, kind === 'send' ? 'تعذر إرسال النقل.' : 'تعذر إكمال النقل.')) }); };
  const selectedTransfer = detail.data;
  return <div className="space-y-7">
    <header className="flex flex-col justify-between gap-5 border-b border-border pb-7 sm:flex-row sm:items-end"><div><p className="mb-3 font-mono text-[10px] tracking-[0.18em] text-primary">حركة بين المخازن / 09</p><h1 className="text-3xl font-bold tracking-tight sm:text-4xl">تحويلات المخزون</h1><p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">مسار مرئي من مخزن المصدر إلى الوجهة. الإرسال لا يخصم، والاستلام المؤكد وحده يحدث دفتر المخزون.</p></div>{user.permissions.includes('transfers:write') && <Button testId="button-create-transfer" onClick={() => { setDraft(blankDraft()); setFormError(''); setCreateOpen(true); }}><FilePlus2 className="h-4 w-4" /> تحويل جديد</Button>}</header>
    <div className="grid gap-3 sm:grid-cols-4"><div className="rounded-lg border border-border bg-card p-4"><p className="text-xs text-muted-foreground">كل التحويلات</p><p className="mt-3 font-mono text-3xl font-semibold">{transfers.isLoading ? '—' : (transfers.data?.length || 0).toLocaleString('ar')}</p></div><div className="rounded-lg border border-primary/20 bg-primary/5 p-4"><p className="text-xs text-primary">في الطريق</p><p className="mt-3 font-mono text-3xl font-semibold text-primary">{transfers.isLoading ? '—' : (counts.sent || 0).toLocaleString('ar')}</p></div><div className="rounded-lg border border-accent/20 bg-accent/5 p-4"><p className="text-xs text-accent">بانتظار الإكمال</p><p className="mt-3 font-mono text-3xl font-semibold text-accent">{transfers.isLoading ? '—' : (counts.received || 0).toLocaleString('ar')}</p></div><div className="rounded-lg border border-sidebar-border bg-sidebar p-4 text-sidebar-foreground"><div className="flex items-center gap-2 text-sidebar-primary"><ShieldCheck className="h-4 w-4" /><span className="font-mono text-[10px] tracking-[0.16em]">RECEIPT GATE</span></div><p className="mt-3 text-sm leading-6 text-sidebar-foreground/75">الاستلام المؤكد هو نقطة تحديث الأرصدة.</p></div></div>
    <section className="overflow-hidden rounded-lg border border-border bg-card"><div className="flex items-start justify-between border-b border-border px-5 py-5"><div><p className="font-mono text-[10px] tracking-[0.16em] text-primary">TRANSFER REGISTER</p><h2 className="mt-1 text-lg font-bold">سجل التحويلات</h2></div><ArrowLeftRight className="h-5 w-5 text-muted-foreground" /></div><div className="hidden grid-cols-[145px_minmax(170px,1.25fr)_180px_100px_125px] gap-3 border-b border-border bg-secondary/50 px-5 py-3 text-[11px] font-semibold text-muted-foreground md:grid"><span>المرجع / التاريخ</span><span>الصنف / السبب</span><span>المسار</span><span>الكمية</span><span>الحالة</span></div>{transfers.isLoading ? <LoadingRows count={6} /> : transfers.isError ? <ErrorState onRetry={() => transfers.refetch()} message="تعذر تحميل سجل التحويلات." /> : !transfers.data?.length ? <EmptyState title="لا توجد تحويلات" description="أنشئ مسودة تحويل لبدء حركة موثقة بين المخازن." action={user.permissions.includes('transfers:write') ? <Button testId="button-empty-create-transfer" onClick={() => setCreateOpen(true)}><FilePlus2 className="h-4 w-4" /> إنشاء تحويل</Button> : undefined} /> : transfers.data.map((transfer) => <TransferRow key={transfer.id} transfer={transfer} onOpen={(id) => { setError(''); setSelectedId(id); }} />)}</section>
    {createOpen && <Modal title="تحويل مخزون جديد" eyebrow="مسودة / لا تخصم من المخزون" onClose={() => !create.isPending && setCreateOpen(false)}><TransferForm draft={draft} setDraft={setDraft} warehouses={warehouses.data || []} items={items.data || []} onSubmit={submit} isPending={create.isPending} error={formError || (warehouses.isError || items.isError ? 'تعذر تحميل المخازن أو الأصناف.' : '')} /></Modal>}
    {selectedId !== null && (detail.isLoading ? <Modal title="تفاصيل التحويل" eyebrow="جاري التحميل" onClose={() => setSelectedId(null)}><LoadingRows count={4} /></Modal> : detail.isError || !selectedTransfer ? <Modal title="تعذر عرض التحويل" onClose={() => setSelectedId(null)}><ErrorState onRetry={() => detail.refetch()} message="تعذر تحميل تفاصيل التحويل." /></Modal> : <DetailModal transfer={selectedTransfer} onClose={() => setSelectedId(null)} onSend={() => action('send', selectedId)} onReceive={() => { setError(''); setSelectedSerials([]); setReceiveId(selectedId); }} onComplete={() => action('complete', selectedId)} canWrite={user.permissions.includes('transfers:write')} canReceive={user.permissions.includes('transfers:receive') || user.permissions.includes('transfers:write')} pending={send.isPending || complete.isPending} error={error} />)}
    {receiveId !== null && (preview.isLoading ? <Modal title="معاينة الاستلام" eyebrow="جاري التحقق" onClose={() => setReceiveId(null)}><LoadingRows count={4} /></Modal> : preview.isError || !preview.data ? <Modal title="تعذر فتح المعاينة" onClose={() => setReceiveId(null)}><ErrorState onRetry={() => preview.refetch()} message="تعذر تحميل الرصيد والأرقام التسلسلية المتاحة." /></Modal> : <ReceiveModal preview={preview.data} selected={selectedSerials} setSelected={setSelectedSerials} onClose={() => setReceiveId(null)} onConfirm={() => { receive.mutate({ transferId: receiveId, data: { serial_numbers: selectedSerials } }, { onSuccess: () => { invalidate(receiveId); setReceiveId(null); setSelectedSerials([]); setSelectedId(receiveId); }, onError: (reason) => setError(errorMessage(reason, 'تعذر تسجيل الاستلام.')) }); }} pending={receive.isPending} error={error} />)}
  </div>;
}