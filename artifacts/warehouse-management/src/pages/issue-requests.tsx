import { useMemo, useState, type FormEvent } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { Link } from 'wouter';
import {
  Check,
  ClipboardCheck,
  ClipboardList,
  Eye,
  FilePlus2,
  PackageCheck,
  Send,
  ShieldAlert,
  X,
} from 'lucide-react';
import {
  getGetIssueRequestPreviewQueryKey,
  getGetIssueRequestQueryKey,
  getGetIssueVoucherQueryKey,
  getListInventoryBalancesQueryKey,
  getListInventoryMovementsQueryKey,
  getListIssueRequestsQueryKey,
  getListIssueVouchersQueryKey,
  useApproveIssueRequest,
  useCloseIssueRequest,
  useCreateIssueRequest,
  useGetIssueRequest,
  useGetIssueRequestPreview,
  useIssueRequest,
  useListDepartments,
  useListIssueRequests,
  useListItems,
  useRejectIssueRequest,
  useSubmitIssueRequest,
} from '@workspace/api-client-react';
import type { IssueRequest, IssueRequestPreview } from '@workspace/api-client-react';
import { Button, EmptyState, ErrorState, Field, LoadingRows, Modal, Notice, SelectField } from '@/components/ui';

type Props = { user: { permissions: string[] } };
type Draft = { department_id: string; request_date: string; reason: string; item_id: string; quantity: string; notes: string };

const today = () => new Date().toISOString().slice(0, 10);
const blankDraft = (): Draft => ({ department_id: '', request_date: today(), reason: '', item_id: '', quantity: '1', notes: '' });
const credentials = { credentials: 'include' as const };

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

function formatDateTime(value: string) {
  if (!value) return '—';
  return new Intl.DateTimeFormat('ar', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value));
}

const statusLabels: Record<string, string> = {
  draft: 'مسودة',
  sent: 'مرسل للمراجعة',
  approved: 'معتمد',
  rejected: 'مرفوض',
  issued: 'تم الصرف',
  closed: 'مغلق',
};

const statusStyles: Record<string, string> = {
  draft: 'border-border bg-secondary text-muted-foreground',
  sent: 'border-primary/25 bg-primary/10 text-primary',
  approved: 'border-accent/25 bg-accent/10 text-accent',
  rejected: 'border-destructive/25 bg-destructive/10 text-destructive',
  issued: 'border-sidebar/25 bg-sidebar/10 text-sidebar',
  closed: 'border-border bg-muted text-muted-foreground',
};

function StatusPill({ status, id }: { status: string; id?: number }) {
  return <span className={`inline-flex w-fit items-center rounded-full border px-2.5 py-1 text-[11px] font-semibold ${statusStyles[status] || statusStyles.draft}`} data-testid={`status-request-${status}${id === undefined ? '' : `-${id}`}`}>{statusLabels[status] || status}</span>;
}

function RequestRow({ request, onOpen }: { request: IssueRequest; onOpen: (id: number) => void }) {
  return (
    <button type="button" onClick={() => onOpen(request.id)} data-testid={`row-issue-request-${request.id}`} className="grid w-full gap-3 border-b border-border px-5 py-4 text-right transition-colors hover:bg-secondary/45 last:border-0 md:grid-cols-[120px_minmax(180px,1.25fr)_150px_120px_150px] md:items-center">
      <div><p className="font-mono text-xs font-semibold text-primary">{request.request_number}</p><p className="mt-1 text-[11px] text-muted-foreground">{formatDate(request.request_date)}</p></div>
      <div className="min-w-0"><p className="truncate text-sm font-bold">{request.item_name}</p><p className="mt-1 truncate text-xs text-muted-foreground">{request.item_code} · {request.department_name}</p></div>
      <div className="text-sm text-muted-foreground"><span className="mb-1 block text-[10px] text-muted-foreground/60 md:hidden">المخزن</span>{request.warehouse_name}</div>
      <div className="text-right md:text-left"><span className="mb-1 block text-[10px] text-muted-foreground/60 md:hidden">الكمية</span><span className="font-mono text-base font-semibold">{request.quantity.toLocaleString('ar')} <span className="text-xs font-normal text-muted-foreground">{request.item_unit}</span></span></div>
      <div className="md:text-left"><StatusPill status={request.status} id={request.id} /></div>
    </button>
  );
}

function RequestForm({ draft, setDraft, departments, items, onSubmit, isPending, error }: { draft: Draft; setDraft: (value: Draft) => void; departments: { id: number; name: string; code: string; is_active: boolean }[]; items: { id: number; code: string; name: string; unit: string; is_active: boolean }[]; onSubmit: (event: FormEvent<HTMLFormElement>) => void; isPending: boolean; error: string }) {
  return (
    <form onSubmit={onSubmit} className="space-y-5">
      {error && <Notice>{error}</Notice>}
      <Notice tone="info">احفظ الطلب كمسودة أولًا. لن يظهر للمراجعة حتى يتم إرساله صراحة.</Notice>
      <div className="grid gap-4 sm:grid-cols-2">
        <SelectField label="القسم الطالب" name="issue-request-department" value={draft.department_id} onChange={(value) => setDraft({ ...draft, department_id: value })} required options={departments.filter((entry) => entry.is_active).map((entry) => ({ value: String(entry.id), label: `${entry.name} (${entry.code})` }))} />
        <Field label="تاريخ الطلب" name="issue-request-date" type="date" value={draft.request_date} onChange={(value) => setDraft({ ...draft, request_date: value })} required />
      </div>
      <SelectField label="الصنف المطلوب" name="issue-request-item" value={draft.item_id} onChange={(value) => setDraft({ ...draft, item_id: value })} required options={items.filter((entry) => entry.is_active).map((entry) => ({ value: String(entry.id), label: `${entry.code} — ${entry.name} (${entry.unit})` }))} />
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="الكمية" name="issue-request-quantity" type="number" value={draft.quantity} onChange={(value) => setDraft({ ...draft, quantity: value })} required hint="يجب أن تكون أكبر من صفر." />
        <Field label="سبب الصرف" name="issue-request-reason" value={draft.reason} onChange={(value) => setDraft({ ...draft, reason: value })} required placeholder="مثال: احتياج تشغيل يومي" />
      </div>
      <Field label="ملاحظات إضافية" name="issue-request-notes" value={draft.notes} onChange={(value) => setDraft({ ...draft, notes: value })} placeholder="مرجع داخلي أو تعليمات التسليم (اختياري)" />
      <Button type="submit" testId="button-save-issue-request" disabled={isPending}><FilePlus2 className="h-4 w-4" />{isPending ? 'جارٍ حفظ المسودة...' : 'حفظ كمسودة'}</Button>
    </form>
  );
}

function Metric({ label, value, unit, tone = 'default' }: { label: string; value: number; unit?: string; tone?: 'default' | 'accent' | 'primary' | 'danger' }) {
  const tones = { default: 'text-foreground', accent: 'text-accent', primary: 'text-primary', danger: 'text-destructive' };
  return <div className="rounded-md border border-border bg-secondary/35 p-4"><p className="text-[11px] font-semibold text-muted-foreground">{label}</p><p className={`mt-2 font-mono text-2xl font-semibold ${tones[tone]}`}>{value.toLocaleString('ar')} <span className="text-xs font-sans font-normal text-muted-foreground">{unit}</span></p></div>;
}

function DetailModal({ request, onClose, onSubmit, onApprove, onReject, onPreview, onCloseRequest, canWrite, canManage, isPending, error }: { request: IssueRequest; onClose: () => void; onSubmit: () => void; onApprove: () => void; onReject: () => void; onPreview: () => void; onCloseRequest: () => void; canWrite: boolean; canManage: boolean; isPending: boolean; error: string }) {
  return (
    <Modal title={request.request_number} eyebrow="سجل طلب الصرف" onClose={onClose}>
      <div className="space-y-5">
        {error && <Notice>{error}</Notice>}
        <div className="flex flex-wrap items-center justify-between gap-3"><StatusPill status={request.status} id={request.id} /><span className="font-mono text-xs text-muted-foreground">{formatDateTime(request.created_at)}</span></div>
        <div className="grid gap-3 sm:grid-cols-2">
          <div className="rounded-md border border-border bg-secondary/35 p-4"><p className="text-[11px] text-muted-foreground">الصنف</p><p className="mt-2 text-sm font-bold">{request.item_name}</p><p className="mt-1 font-mono text-[11px] text-primary">{request.item_code}</p></div>
          <div className="rounded-md border border-border bg-secondary/35 p-4"><p className="text-[11px] text-muted-foreground">القسم الطالب</p><p className="mt-2 text-sm font-bold">{request.department_name}</p><p className="mt-1 text-xs text-muted-foreground">{request.created_by_name}</p></div>
        </div>
        <div className="grid gap-3 sm:grid-cols-3"><Metric label="الكمية المطلوبة" value={request.quantity} unit={request.item_unit} tone="primary" /><Metric label="الرصيد الحالي" value={request.current_balance} unit={request.item_unit} /><Metric label="المتاح للصرف" value={request.available_quantity} unit={request.item_unit} tone={request.available_quantity < request.quantity ? 'danger' : 'accent'} /></div>
        <dl className="grid gap-x-6 gap-y-4 border-y border-border py-4 text-sm sm:grid-cols-2"><div><dt className="text-xs text-muted-foreground">تاريخ الطلب</dt><dd className="mt-1 font-medium">{formatDate(request.request_date)}</dd></div><div><dt className="text-xs text-muted-foreground">المخزن</dt><dd className="mt-1 font-medium">{request.warehouse_name}</dd></div><div className="sm:col-span-2"><dt className="text-xs text-muted-foreground">السبب</dt><dd className="mt-1 leading-6">{request.reason}</dd></div>{request.notes && <div className="sm:col-span-2"><dt className="text-xs text-muted-foreground">ملاحظات</dt><dd className="mt-1 leading-6">{request.notes}</dd></div>}{request.rejection_reason && <div className="sm:col-span-2"><dt className="text-xs text-destructive">سبب الرفض</dt><dd className="mt-1 leading-6 text-destructive">{request.rejection_reason}</dd></div>}</dl>
        {request.issue_number && <div className="flex items-center justify-between rounded-md border border-accent/25 bg-accent/8 px-4 py-3 text-sm"><span className="text-muted-foreground">سند الصرف الناتج</span><Link href={`/issue-vouchers/${request.issue_voucher_id}`} className="font-mono font-semibold text-accent hover:underline" data-testid={`link-issue-voucher-${request.id}`}>{request.issue_number}</Link></div>}
        <div className="flex flex-wrap gap-2 border-t border-border pt-4">
          {request.status === 'draft' && canWrite && <Button testId={`button-submit-issue-request-${request.id}`} onClick={onSubmit} disabled={isPending}><Send className="h-4 w-4" /> إرسال للمراجعة</Button>}
          {request.status === 'sent' && canManage && <><Button testId={`button-approve-issue-request-${request.id}`} onClick={onApprove} disabled={isPending}><Check className="h-4 w-4" /> اعتماد الطلب</Button><Button testId={`button-reject-issue-request-${request.id}`} variant="danger" onClick={onReject} disabled={isPending}><X className="h-4 w-4" /> رفض الطلب</Button></>}
          {request.status === 'approved' && canManage && <Button testId={`button-preview-issue-request-${request.id}`} onClick={onPreview}><PackageCheck className="h-4 w-4" /> فتح معاينة الصرف</Button>}
          {request.status === 'issued' && canManage && <Button testId={`button-close-issue-request-${request.id}`} variant="secondary" onClick={onCloseRequest} disabled={isPending}><ClipboardCheck className="h-4 w-4" /> إغلاق الطلب</Button>}
          {request.status === 'closed' && <span className="inline-flex items-center gap-2 rounded-md bg-secondary px-3 py-2 text-xs font-semibold text-muted-foreground"><ShieldAlert className="h-4 w-4" /> سجل مكتمل وغير قابل لإجراء إضافي</span>}
        </div>
      </div>
    </Modal>
  );
}

function PreviewModal({ preview, selectedSerials, setSelectedSerials, onClose, onIssue, isPending, error }: { preview: IssueRequestPreview; selectedSerials: string[]; setSelectedSerials: (value: string[]) => void; onClose: () => void; onIssue: () => void; isPending: boolean; error: string }) {
  const required = preview.requested_quantity;
  const serialReady = !preview.requires_serial_number || (selectedSerials.length === required && new Set(selectedSerials).size === selectedSerials.length);
  const toggleSerial = (serial: string) => setSelectedSerials(selectedSerials.includes(serial) ? selectedSerials.filter((entry) => entry !== serial) : [...selectedSerials, serial]);
  return (
    <Modal title={`معاينة صرف ${preview.request_number}`} eyebrow="تحقق قبل الخصم من المخزون" onClose={onClose}>
      <div className="space-y-5">
        {error && <Notice>{error}</Notice>}
        <div className="grid gap-3 sm:grid-cols-3"><Metric label="الرصيد الحالي" value={preview.current_balance} unit={preview.item_unit} /><Metric label="الكمية المطلوبة" value={preview.requested_quantity} unit={preview.item_unit} tone="primary" /><Metric label="المتاح للصرف" value={preview.available_quantity} unit={preview.item_unit} tone={preview.available_quantity < required ? 'danger' : 'accent'} /></div>
        <div className="rounded-md border border-border bg-secondary/35 p-4 text-sm"><p className="font-bold">{preview.item_name}</p><p className="mt-1 text-xs text-muted-foreground">{preview.warehouse_name} · {preview.item_unit}</p></div>
        {preview.requires_serial_number ? <div className="space-y-3"><div className="flex items-center justify-between"><p className="text-sm font-bold">اختيار الأرقام التسلسلية</p><span className={`font-mono text-xs ${serialReady ? 'text-accent' : 'text-destructive'}`}>{selectedSerials.length} / {required}</span></div><p className="text-xs leading-5 text-muted-foreground">اختر أرقامًا متاحة مساوية تمامًا للكمية المطلوبة. لن يمكن إتمام الصرف قبل اكتمال الاختيار.</p><div className="grid max-h-56 gap-2 overflow-y-auto rounded-md border border-border p-3 sm:grid-cols-2">{preview.available_serial_numbers.map((serial) => <label key={serial} className={`flex cursor-pointer items-center gap-3 rounded-md border px-3 py-2 text-sm transition-colors ${selectedSerials.includes(serial) ? 'border-primary bg-primary/8' : 'border-border bg-card hover:bg-secondary'}`}><input type="checkbox" checked={selectedSerials.includes(serial)} onChange={() => toggleSerial(serial)} data-testid={`checkbox-serial-${serial}`} className="h-4 w-4 accent-[hsl(var(--primary))]" /><span className="font-mono">{serial}</span></label>)}</div></div> : <Notice tone="info">هذا الصنف غير متتبع بالأرقام التسلسلية. سيتم صرف الكمية المطلوبة من الرصيد المتاح.</Notice>}
        <div className="flex flex-wrap items-center justify-between gap-3 border-t border-border pt-4"><p className="text-xs text-muted-foreground">ينشئ هذا الإجراء سند صرف وحركة سالبة في دفتر المخزون.</p><Button testId={`button-confirm-issue-${preview.request_id}`} onClick={onIssue} disabled={!serialReady || isPending}><PackageCheck className="h-4 w-4" />{isPending ? 'جارٍ تنفيذ الصرف...' : 'تنفيذ الصرف'}</Button></div>
      </div>
    </Modal>
  );
}

export default function IssueRequestsPage({ user }: Props) {
  const queryClient = useQueryClient();
  const requests = useListIssueRequests({ request: credentials });
  const departments = useListDepartments({ request: credentials });
  const items = useListItems({ isActive: true }, { request: credentials });
  const createRequest = useCreateIssueRequest({ request: credentials });
  const submitRequest = useSubmitIssueRequest({ request: credentials });
  const approveRequest = useApproveIssueRequest({ request: credentials });
  const rejectRequest = useRejectIssueRequest({ request: credentials });
  const issueRequest = useIssueRequest({ request: credentials });
  const closeRequest = useCloseIssueRequest({ request: credentials });
  const canWrite = user.permissions.includes('issue_requests:write');
  const canManage = user.permissions.includes('issues:write');
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [draft, setDraft] = useState<Draft>(blankDraft);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [previewId, setPreviewId] = useState<number | null>(null);
  const [rejectId, setRejectId] = useState<number | null>(null);
  const [rejectionReason, setRejectionReason] = useState('');
  const [selectedSerials, setSelectedSerials] = useState<string[]>([]);
  const [formError, setFormError] = useState('');
  const [actionError, setActionError] = useState('');

  const detail = useGetIssueRequest(selectedId ?? 0, { request: credentials, query: { enabled: selectedId !== null, queryKey: getGetIssueRequestQueryKey(selectedId ?? 0) } });
  const preview = useGetIssueRequestPreview(previewId ?? 0, { request: credentials, query: { enabled: previewId !== null, queryKey: getGetIssueRequestPreviewQueryKey(previewId ?? 0) } });
  const counts = useMemo(() => (requests.data || []).reduce<Record<string, number>>((acc, request) => { acc[request.status] = (acc[request.status] || 0) + 1; return acc; }, {}), [requests.data]);

  const invalidate = (requestId?: number, voucherId?: number) => {
    queryClient.invalidateQueries({ queryKey: getListIssueRequestsQueryKey() });
    queryClient.invalidateQueries({ queryKey: getListIssueVouchersQueryKey() });
    queryClient.invalidateQueries({ queryKey: getListInventoryBalancesQueryKey() });
    queryClient.invalidateQueries({ queryKey: getListInventoryMovementsQueryKey() });
    if (requestId !== undefined) {
      queryClient.invalidateQueries({ queryKey: getGetIssueRequestQueryKey(requestId) });
      queryClient.invalidateQueries({ queryKey: getGetIssueRequestPreviewQueryKey(requestId) });
    }
    if (voucherId !== undefined) queryClient.invalidateQueries({ queryKey: getGetIssueVoucherQueryKey(voucherId) });
  };

  const handleCreate = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); setFormError('');
    const quantity = Number(draft.quantity);
    if (!draft.department_id || !draft.request_date || !draft.reason.trim() || !draft.item_id || !Number.isFinite(quantity) || quantity <= 0) { setFormError('أكمل الحقول المطلوبة وأدخل كمية أكبر من صفر.'); return; }
    createRequest.mutate({ data: { department_id: Number(draft.department_id), request_date: draft.request_date, reason: draft.reason.trim(), item_id: Number(draft.item_id), quantity, notes: draft.notes.trim() } }, {
      onSuccess: (created) => { invalidate(created.id); setIsCreateOpen(false); setDraft(blankDraft()); setSelectedId(created.id); },
      onError: (error) => setFormError(errorMessage(error, 'تعذر حفظ مسودة طلب الصرف.')),
    });
  };

  const runAction = (action: { mutate: (variables: { requestId: number }, options?: { onSuccess?: (data: IssueRequest) => void; onError?: (error: unknown) => void }) => void }, id: number, fallback: string) => {
    setActionError('');
    action.mutate({ requestId: id }, { onSuccess: (updated) => { invalidate(id, updated.issue_voucher_id || undefined); }, onError: (error) => setActionError(errorMessage(error, fallback)) });
  };

  const selectedRequest = detail.data;
  return (
    <div className="space-y-7">
      <header className="flex flex-col justify-between gap-5 border-b border-border pb-7 sm:flex-row sm:items-end">
        <div><p className="mb-3 font-mono text-[10px] tracking-[0.18em] text-primary">دورة الصرف / 04</p><h1 className="text-3xl font-bold tracking-tight sm:text-4xl">طلبات الصرف</h1><p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">مسار واضح من طلب القسم إلى اعتماد المخزن، ثم خصم موثق وسند صرف قابل للمراجعة.</p></div>
        {canWrite && <Button testId="button-create-issue-request" onClick={() => { setDraft(blankDraft()); setFormError(''); setIsCreateOpen(true); }}><FilePlus2 className="h-4 w-4" /> طلب صرف جديد</Button>}
      </header>
      <div className="grid gap-3 sm:grid-cols-4"><div className="rounded-lg border border-border bg-card p-4"><p className="text-xs text-muted-foreground">كل الطلبات</p><p className="mt-3 font-mono text-3xl font-semibold" data-testid="text-issue-request-total">{requests.isLoading ? '—' : (requests.data?.length || 0).toLocaleString('ar')}</p></div><div className="rounded-lg border border-primary/20 bg-primary/5 p-4"><p className="text-xs text-primary">بانتظار المراجعة</p><p className="mt-3 font-mono text-3xl font-semibold text-primary" data-testid="text-issue-request-sent">{requests.isLoading ? '—' : (counts.sent || 0).toLocaleString('ar')}</p></div><div className="rounded-lg border border-accent/20 bg-accent/5 p-4"><p className="text-xs text-accent">معتمدة للصرف</p><p className="mt-3 font-mono text-3xl font-semibold text-accent" data-testid="text-issue-request-approved">{requests.isLoading ? '—' : (counts.approved || 0).toLocaleString('ar')}</p></div><div className="rounded-lg border border-sidebar-border bg-sidebar p-4 text-sidebar-foreground"><p className="font-mono text-[10px] tracking-[0.16em] text-sidebar-primary">AUDIT TRAIL</p><p className="mt-3 text-sm leading-6 text-sidebar-foreground/75">كل انتقال حالة يحتاج فعلًا صريحًا وصلاحية مناسبة.</p></div></div>
      <section className="overflow-hidden rounded-lg border border-border bg-card">
        <div className="flex items-start justify-between border-b border-border px-5 py-5"><div><p className="font-mono text-[10px] tracking-[0.16em] text-primary">REQUEST REGISTER</p><h2 className="mt-1 text-lg font-bold">سجل الطلبات</h2></div><ClipboardList className="h-5 w-5 text-muted-foreground" /></div>
        <div className="hidden grid-cols-[120px_minmax(180px,1.25fr)_150px_120px_150px] gap-3 border-b border-border bg-secondary/50 px-5 py-3 text-[11px] font-semibold text-muted-foreground md:grid"><span>المرجع / التاريخ</span><span>الصنف / القسم</span><span>المخزن</span><span>الكمية</span><span>الحالة</span></div>
        {requests.isLoading ? <LoadingRows count={6} /> : requests.isError ? <ErrorState onRetry={() => requests.refetch()} message="تعذر تحميل سجل طلبات الصرف." /> : !requests.data?.length ? <EmptyState title="لا توجد طلبات صرف" description="أنشئ أول مسودة لبدء دورة الصرف الموثقة." action={canWrite ? <Button testId="button-empty-create-issue-request" onClick={() => setIsCreateOpen(true)}><FilePlus2 className="h-4 w-4" /> إنشاء مسودة</Button> : undefined} /> : requests.data.map((request) => <RequestRow key={request.id} request={request} onOpen={(id) => { setActionError(''); setSelectedId(id); }} />)}
      </section>
      {isCreateOpen && <Modal title="طلب صرف جديد" eyebrow="مسودة / لا تخصم من المخزون" onClose={() => !createRequest.isPending && setIsCreateOpen(false)}><RequestForm draft={draft} setDraft={setDraft} departments={departments.data || []} items={items.data || []} onSubmit={handleCreate} isPending={createRequest.isPending} error={formError || (departments.isError || items.isError ? 'تعذر تحميل الأقسام أو الأصناف. أعد المحاولة ثم افتح النموذج مجددًا.' : '')} /></Modal>}
      {selectedId !== null && (detail.isLoading ? <Modal title="تفاصيل الطلب" eyebrow="جاري التحميل" onClose={() => setSelectedId(null)}><LoadingRows count={4} /></Modal> : detail.isError || !selectedRequest ? <Modal title="تعذر عرض الطلب" onClose={() => setSelectedId(null)}><ErrorState onRetry={() => detail.refetch()} message="تعذر تحميل تفاصيل طلب الصرف." /></Modal> : <DetailModal request={selectedRequest} onClose={() => setSelectedId(null)} onSubmit={() => runAction(submitRequest, selectedId, 'تعذر إرسال الطلب للمراجعة.')} onApprove={() => runAction(approveRequest, selectedId, 'تعذر اعتماد الطلب.')} onReject={() => { setRejectionReason(''); setActionError(''); setRejectId(selectedId); }} onPreview={() => { setSelectedSerials([]); setActionError(''); setPreviewId(selectedId); }} onCloseRequest={() => runAction(closeRequest, selectedId, 'تعذر إغلاق الطلب.')} canWrite={canWrite} canManage={canManage} isPending={submitRequest.isPending || approveRequest.isPending || closeRequest.isPending} error={actionError} />)}
      {rejectId !== null && <Modal title="رفض طلب الصرف" eyebrow="سبب الرفض إلزامي" onClose={() => !rejectRequest.isPending && setRejectId(null)}><form className="space-y-5" onSubmit={(event) => { event.preventDefault(); if (!rejectionReason.trim()) { setActionError('اكتب سببًا واضحًا قبل رفض الطلب.'); return; } rejectRequest.mutate({ requestId: rejectId, data: { rejection_reason: rejectionReason.trim() } }, { onSuccess: (updated) => { invalidate(rejectId); setRejectId(null); setRejectionReason(''); setActionError(''); }, onError: (error) => setActionError(errorMessage(error, 'تعذر رفض الطلب.')) }); }}><p className="text-sm leading-6 text-muted-foreground">سيظهر السبب لمقدم الطلب ويبقى جزءًا من السجل.</p>{actionError && <Notice>{actionError}</Notice>}<label className="block space-y-2 text-right"><span className="flex items-center justify-between text-sm font-semibold"><span>سبب الرفض</span><span className="font-mono text-[10px] text-muted-foreground">مطلوب</span></span><textarea value={rejectionReason} onChange={(event) => setRejectionReason(event.target.value)} required rows={4} data-testid="input-rejection-reason" className="w-full resize-y rounded-md border border-input bg-card px-3 py-2 text-sm outline-none focus:border-destructive focus:ring-2 focus:ring-destructive/20" placeholder="اذكر ما يلزم تعديله أو سبب عدم الاعتماد" /></label><Button type="submit" variant="danger" testId="button-confirm-reject-issue-request" disabled={rejectRequest.isPending}><X className="h-4 w-4" />{rejectRequest.isPending ? 'جارٍ رفض الطلب...' : 'تأكيد الرفض'}</Button></form></Modal>}
      {previewId !== null && (preview.isLoading ? <Modal title="معاينة الصرف" eyebrow="جاري التحقق" onClose={() => setPreviewId(null)}><LoadingRows count={4} /></Modal> : preview.isError || !preview.data ? <Modal title="تعذر فتح المعاينة" onClose={() => setPreviewId(null)}><ErrorState onRetry={() => preview.refetch()} message="تعذر تحميل الرصيد والأرقام التسلسلية المتاحة." /></Modal> : <PreviewModal preview={preview.data} selectedSerials={selectedSerials} setSelectedSerials={setSelectedSerials} onClose={() => setPreviewId(null)} onIssue={() => { issueRequest.mutate({ requestId: previewId, data: { serial_numbers: selectedSerials } }, { onSuccess: (voucher) => { invalidate(previewId, voucher.id); setPreviewId(null); setSelectedSerials([]); setSelectedId(previewId); setActionError(''); }, onError: (error) => setActionError(errorMessage(error, 'تعذر تنفيذ الصرف.')) }); }} isPending={issueRequest.isPending} error={actionError} />)}
    </div>
  );
}