import { useMemo, useState, type FormEvent } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import {
  BarChart3,
  CalendarDays,
  Download,
  FileSpreadsheet,
  FileText,
  Filter,
  Printer,
  RefreshCw,
  Search,
} from 'lucide-react';
import {
  getGetReportQueryKey,
  exportReport,
  useGetReport,
  useListDepartments,
  useListItems,
  useListWarehouses,
} from '@workspace/api-client-react';
import type { ExportReportParams, GetReportParams, ReportResponse, ReportType } from '@workspace/api-client-react';
import { Button, EmptyState, ErrorState, LoadingRows, SelectField } from '@/components/ui';

const credentials = { credentials: 'include' as const };
const reportOptions: { value: ReportType; label: string; short: string; description: string }[] = [
  { value: 'inventory-balance', label: 'رصيد المخزون', short: 'الأرصدة', description: 'الكميات الحالية حسب الصنف والمخزن.' },
  { value: 'item-movements', label: 'حركة الأصناف', short: 'الحركات', description: 'سجل الاستلام والصرف والتحويلات خلال الفترة.' },
  { value: 'receipts', label: 'سندات الاستلام', short: 'الاستلام', description: 'كل المواد التي دخلت إلى المخازن.' },
  { value: 'issues', label: 'سندات الصرف', short: 'الصرف', description: 'السندات المنفذة والمواد المصروفة.' },
  { value: 'transfers', label: 'التحويلات', short: 'التحويلات', description: 'حركة المواد بين المخازن.' },
  { value: 'stocktakes', label: 'الجرد الفعلي', short: 'الجرد', description: 'أوراق الجرد والفروقات المسجلة.' },
  { value: 'low-stock', label: 'الأصناف منخفضة المخزون', short: 'منخفض المخزون', description: 'الأصناف التي وصلت إلى حد إعادة الطلب أو أقل.' },
  { value: 'expiring', label: 'المواد قاربت الانتهاء', short: 'الانتهاء', description: 'مواد تنتهي خلال عدد الأيام المحدد.' },
  { value: 'issues-by-department', label: 'الصرف حسب القسم', short: 'حسب القسم', description: 'ملخص الكميات المصروفة لكل قسم.' },
];

type Filters = {
  search: string;
  warehouse: string;
  item: string;
  department: string;
  from: string;
  to: string;
  expiryDays: string;
};

const initialFilters: Filters = { search: '', warehouse: '', item: '', department: '', from: '', to: '', expiryDays: '30' };

function errorMessage(error: unknown) {
  const typed = error as { status?: number; detail?: string; response?: { data?: { detail?: string } } };
  if (typed?.status === 401) return 'انتهت الجلسة. سجّل الدخول من جديد للمتابعة.';
  if (typed?.status === 403) return 'لا تملك صلاحية عرض التقارير.';
  return typed?.detail || typed?.response?.data?.detail || 'تعذر تحميل التقرير من الخادم المحلي.';
}

function displayValue(value: unknown): string {
  if (value === null || value === undefined || value === '') return '—';
  if (typeof value === 'boolean') return value ? 'نعم' : 'لا';
  if (typeof value === 'number') return value.toLocaleString('ar');
  if (typeof value === 'string') {
    const date = /^\d{4}-\d{2}-\d{2}(T.*)?$/.test(value) ? new Date(value) : null;
    return date && !Number.isNaN(date.getTime()) ? new Intl.DateTimeFormat('ar', { dateStyle: 'medium', timeStyle: value.includes('T') ? 'short' : undefined }).format(date) : value;
  }
  if (Array.isArray(value)) return value.map((entry) => displayValue(entry)).join('، ');
  try { return JSON.stringify(value); } catch { return String(value); }
}

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function ReportTable({ report }: { report: ReportResponse }) {
  if (!report.rows.length) return <EmptyState title="لا توجد نتائج" description="لم يعثر التقرير على سجلات تطابق الفلاتر الحالية." />;
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[680px] border-collapse text-right" data-testid="table-report">
        <thead className="bg-secondary/60 text-[11px] font-semibold text-muted-foreground">
          <tr>{report.columns.map((column) => <th scope="col" className="whitespace-nowrap border-b border-border px-4 py-3" key={column.key}>{column.label || column.key}</th>)}</tr>
        </thead>
        <tbody>
          {report.rows.map((row, index) => (
            <tr className="border-b border-border last:border-0 hover:bg-secondary/35" data-testid={`row-report-${index}`} key={index}>
              {report.columns.map((column) => <td className="max-w-[280px] px-4 py-3 text-sm align-top" key={column.key}>{displayValue(row[column.key])}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function ReportsPage() {
  const queryClient = useQueryClient();
  const warehouses = useListWarehouses({ request: credentials });
  const items = useListItems({ isActive: true }, { request: credentials });
  const departments = useListDepartments({ request: credentials });
  const [reportType, setReportType] = useState<ReportType>('inventory-balance');
  const [filters, setFilters] = useState<Filters>(initialFilters);
  const [applied, setApplied] = useState<Filters>(initialFilters);
  const [exporting, setExporting] = useState<'pdf' | 'xlsx' | null>(null);
  const [exportError, setExportError] = useState('');
  const selected = reportOptions.find((report) => report.value === reportType) || reportOptions[0];
  const params = useMemo<GetReportParams>(() => ({
    search: applied.search || undefined,
    warehouse_id: applied.warehouse ? Number(applied.warehouse) : undefined,
    item_id: applied.item ? Number(applied.item) : undefined,
    department_id: applied.department ? Number(applied.department) : undefined,
    date_from: applied.from || undefined,
    date_to: applied.to || undefined,
    expiry_days: reportType === 'expiring' && applied.expiryDays ? Number(applied.expiryDays) : undefined,
    limit: 5000,
  }), [applied, reportType]);
  const report = useGetReport(reportType, params, { request: credentials, query: { queryKey: getGetReportQueryKey(reportType, params) } });
  const setFilter = (key: keyof Filters, value: string) => setFilters((current) => ({ ...current, [key]: value }));

  const applyFilters = (event: FormEvent) => { event.preventDefault(); setApplied({ ...filters }); };
  const refresh = () => { queryClient.invalidateQueries({ queryKey: getGetReportQueryKey(reportType, params) }); };
  const doExport = async (format: 'pdf' | 'xlsx') => {
    setExporting(format);
    setExportError('');
    try {
      const exportParams: ExportReportParams = { ...params, format };
      const blob = await exportReport(reportType, exportParams, credentials);
      const safeName = report.data?.title?.replace(/[^\p{L}\p{N}_-]+/gu, '-').replace(/^-|-$/g, '') || selected.short;
      downloadBlob(blob, `${safeName}.${format}`);
    } catch {
      setExportError(`تعذر تجهيز ملف ${format === 'pdf' ? 'PDF' : 'Excel'} من الخادم.`);
    } finally { setExporting(null); }
  };

  return (
    <div className="space-y-7">
      <header className="flex flex-col justify-between gap-5 border-b border-border pb-7 sm:flex-row sm:items-end">
        <div>
          <p className="mb-3 font-mono text-[10px] tracking-[0.18em] text-primary">مركز التحليل / 12</p>
          <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">التقارير</h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">لقطة تشغيلية قابلة للطباعة من دفتر المخزون. اختر تقريرًا، ثبّت الفلاتر، ثم صدّر النسخة التي يحتاجها فريقك.</p>
        </div>
        <div className="flex items-center gap-2 rounded-md border border-sidebar-border bg-sidebar px-4 py-3 text-sidebar-foreground">
          <BarChart3 className="h-5 w-5 text-sidebar-primary" />
          <div><p className="font-mono text-[10px] tracking-[0.16em] text-sidebar-primary">REPORT WORKSPACE</p><p className="mt-1 text-xs text-sidebar-foreground/70">مصدر واحد للبيانات</p></div>
        </div>
      </header>

      <section className="grid gap-3 lg:grid-cols-[1.15fr_0.85fr]">
        <div className="rounded-lg border border-border bg-card p-5">
          <div className="mb-4 flex items-center gap-2"><FileText className="h-4 w-4 text-primary" /><p className="text-xs font-bold">نوع التقرير</p></div>
          <div data-testid="report-selector"><SelectField label="اختر تقريرًا" name="report-type" value={reportType} onChange={(value) => { setReportType(value as ReportType); setApplied({ ...filters }); }} options={reportOptions.map((option) => ({ value: option.value, label: option.label }))} /></div>
          <p className="mt-3 text-xs leading-5 text-muted-foreground">{selected.description}</p>
        </div>
        <div className="rounded-lg border border-primary/20 bg-primary/5 p-5">
          <p className="font-mono text-[10px] tracking-[0.16em] text-primary">CURRENT VIEW</p>
          <p className="mt-2 text-xl font-bold">{selected.label}</p>
          <div className="mt-4 flex items-end justify-between"><span className="text-xs text-muted-foreground">عدد السجلات</span><span className="font-mono text-3xl font-semibold text-primary">{report.data?.row_count?.toLocaleString('ar') || '—'}</span></div>
        </div>
      </section>

      <form onSubmit={applyFilters} className="rounded-lg border border-border bg-card p-5" data-testid="report-filters">
        <div className="mb-4 flex items-center gap-2"><Filter className="h-4 w-4 text-primary" /><p className="text-sm font-bold">تصفية النتائج</p><span className="mr-auto text-[11px] text-muted-foreground">تُطبّق عند الضغط على عرض التقرير</span></div>
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <label className="block space-y-2 text-right xl:col-span-2"><span className="text-sm font-semibold">بحث</span><span className="relative block"><Search className="pointer-events-none absolute right-3 top-3 h-4 w-4 text-muted-foreground" /><input type="search" value={filters.search} onChange={(event) => setFilter('search', event.target.value)} placeholder="رقم السند أو اسم الصنف..." data-testid="input-report-search" className="h-11 w-full rounded-md border border-input bg-card px-10 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/20" /></span></label>
          <SelectField label="المخزن" name="report-warehouse" value={filters.warehouse} onChange={(value) => setFilter('warehouse', value)} options={(warehouses.data || []).map((warehouse) => ({ value: String(warehouse.id), label: `${warehouse.name} (${warehouse.code})` }))} />
          <SelectField label="الصنف" name="report-item" value={filters.item} onChange={(value) => setFilter('item', value)} options={(items.data || []).map((item) => ({ value: String(item.id), label: `${item.code} — ${item.name}` }))} />
          <SelectField label="القسم" name="report-department" value={filters.department} onChange={(value) => setFilter('department', value)} options={(departments.data || []).map((department) => ({ value: String(department.id), label: `${department.code} — ${department.name}` }))} />
          <label className="block space-y-2 text-right"><span className="text-sm font-semibold">من تاريخ</span><input type="date" value={filters.from} onChange={(event) => setFilter('from', event.target.value)} data-testid="input-report-date-from" className="h-11 w-full rounded-md border border-input bg-card px-3 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/20" /></label>
          <label className="block space-y-2 text-right"><span className="text-sm font-semibold">إلى تاريخ</span><input type="date" value={filters.to} onChange={(event) => setFilter('to', event.target.value)} data-testid="input-report-date-to" className="h-11 w-full rounded-md border border-input bg-card px-3 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/20" /></label>
          {reportType === 'expiring' && <label className="block space-y-2 text-right"><span className="text-sm font-semibold">أيام الانتهاء</span><input type="number" min="1" max="3650" value={filters.expiryDays} onChange={(event) => setFilter('expiryDays', event.target.value)} data-testid="input-report-expiry-days" className="h-11 w-full rounded-md border border-input bg-card px-3 font-mono text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/20" /></label>}
        </div>
        <div className="mt-5 flex flex-wrap gap-2">
          <Button type="submit" testId="button-apply-report-filters"><Filter className="h-4 w-4" /> عرض التقرير</Button>
          <Button type="button" variant="secondary" testId="button-refresh-report" onClick={refresh} disabled={report.isFetching}><RefreshCw className={`h-4 w-4 ${report.isFetching ? 'animate-spin' : ''}`} /> تحديث</Button>
        </div>
      </form>

      <section className="print-report overflow-hidden rounded-lg border border-border bg-card" data-testid="report-print-area">
        <div className="flex flex-col justify-between gap-4 border-b border-border px-5 py-5 sm:flex-row sm:items-start">
          <div><p className="font-mono text-[10px] tracking-[0.16em] text-primary">OPERATIONAL REPORT</p><h2 className="mt-1 text-xl font-bold">{report.data?.title || selected.label}</h2><p className="mt-1 text-xs text-muted-foreground">{report.data ? `أنشئ في ${displayValue(report.data.generated_at)} · ${report.data.row_count.toLocaleString('ar')} سجل` : selected.description}</p></div>
          <div className="no-print flex flex-wrap gap-2">
            <Button type="button" variant="secondary" testId="button-print-report" onClick={() => window.print()}><Printer className="h-4 w-4" /> طباعة</Button>
            <Button type="button" variant="secondary" testId="button-export-pdf" onClick={() => doExport('pdf')} disabled={exporting !== null}><Download className="h-4 w-4" />{exporting === 'pdf' ? 'جارٍ تجهيز PDF...' : 'PDF'}</Button>
            <Button type="button" variant="secondary" testId="button-export-excel" onClick={() => doExport('xlsx')} disabled={exporting !== null}><FileSpreadsheet className="h-4 w-4" />{exporting === 'xlsx' ? 'جارٍ تجهيز Excel...' : 'Excel'}</Button>
          </div>
        </div>
        {exportError && <div className="border-b border-destructive/20 bg-destructive/8 px-5 py-3 text-sm text-destructive" role="alert">{exportError}</div>}
        {report.isLoading ? <LoadingRows count={7} /> : report.isError ? <ErrorState onRetry={() => report.refetch()} message={errorMessage(report.error)} /> : !report.data ? <EmptyState title="اختر تقريرًا" description="سيظهر التقرير هنا بعد تحميل البيانات." /> : <ReportTable report={report.data} />}
      </section>
    </div>
  );
}