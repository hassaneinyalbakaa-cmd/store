from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from io import BytesIO
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFError, TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..db import get_db
from ..dependencies import require_permission
from ..models import (
    Department,
    InventoryMovement,
    InventorySerial,
    IssueRequest,
    IssueVoucher,
    Item,
    Receipt,
    ReceiptDetail,
    StockTransfer,
    Stocktake,
    StocktakeLine,
    User,
    Warehouse,
)
from ..schemas import ReportResponse, ReportColumn

router = APIRouter(tags=["reports"])

REPORTS: dict[str, tuple[str, list[tuple[str, str]]]] = {
    "inventory-balance": (
        "رصيد المخزون",
        [
            ("item_code", "رمز الصنف"),
            ("item_name", "الصنف"),
            ("warehouse_name", "المخزن"),
            ("quantity", "الرصيد"),
            ("unit", "الوحدة"),
        ],
    ),
    "item-movements": (
        "حركة صنف",
        [
            ("movement_date", "التاريخ"),
            ("movement_type", "نوع الحركة"),
            ("item_code", "رمز الصنف"),
            ("item_name", "الصنف"),
            ("warehouse_name", "المخزن"),
            ("quantity", "الكمية"),
            ("reference", "رقم المستند"),
            ("notes", "الملاحظات"),
        ],
    ),
    "receipts": (
        "الاستلامات",
        [
            ("receipt_number", "رقم الاستلام"),
            ("receipt_date", "التاريخ"),
            ("supplier", "المورد"),
            ("item_code", "رمز الصنف"),
            ("item_name", "الصنف"),
            ("warehouse_name", "المخزن"),
            ("quantity", "الكمية"),
        ],
    ),
    "issues": (
        "الصرف",
        [
            ("issue_number", "رقم الصرف"),
            ("issued_at", "التاريخ والوقت"),
            ("department_name", "القسم"),
            ("item_code", "رمز الصنف"),
            ("item_name", "الصنف"),
            ("warehouse_name", "المخزن"),
            ("quantity", "الكمية"),
        ],
    ),
    "transfers": (
        "التحويلات",
        [
            ("transfer_number", "رقم التحويل"),
            ("created_at", "تاريخ الإنشاء"),
            ("source_warehouse_name", "المصدر"),
            ("destination_warehouse_name", "الوجهة"),
            ("item_code", "رمز الصنف"),
            ("item_name", "الصنف"),
            ("quantity", "الكمية"),
            ("status", "الحالة"),
        ],
    ),
    "stocktakes": (
        "الجرد",
        [
            ("stocktake_number", "رقم الجرد"),
            ("stocktake_date", "التاريخ"),
            ("warehouse_name", "المخزن"),
            ("item_code", "رمز الصنف"),
            ("item_name", "الصنف"),
            ("system_quantity", "رصيد النظام"),
            ("actual_quantity", "الفعلي"),
            ("difference", "الفرق"),
            ("status", "الحالة"),
        ],
    ),
    "low-stock": (
        "الأصناف تحت الحد الأدنى",
        [
            ("item_code", "رمز الصنف"),
            ("item_name", "الصنف"),
            ("warehouse_name", "المخزن"),
            ("quantity", "الرصيد"),
            ("minimum_level", "الحد الأدنى"),
            ("shortage", "العجز"),
        ],
    ),
    "expiring": (
        "المواد القريبة من انتهاء الصلاحية",
        [
            ("item_code", "رمز الصنف"),
            ("item_name", "الصنف"),
            ("warehouse_name", "المخزن"),
            ("expiry_date", "انتهاء الصلاحية"),
            ("days_remaining", "الأيام المتبقية"),
            ("quantity", "الكمية"),
        ],
    ),
    "issues-by-department": (
        "الصرف حسب القسم",
        [
            ("department_name", "القسم"),
            ("voucher_count", "عدد السندات"),
            ("quantity", "إجمالي الكمية"),
        ],
    ),
}

MOVEMENT_LABELS = {
    "opening": "رصيد افتتاحي",
    "receipt": "استلام",
    "issue": "صرف",
    "transfer_out": "تحويل خارج",
    "transfer_in": "تحويل داخل",
    "adjustment": "تسوية",
}

STATUS_LABELS = {
    "draft": "مسودة",
    "sent": "مرسل",
    "received": "مستلم",
    "completed": "مكتمل",
}


def report_error(message: str) -> HTTPException:
    return HTTPException(status_code=400, detail=message)


def serialize_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, float):
        return round(value, 4)
    return value


def text_matches(row: dict[str, Any], search: str | None) -> bool:
    if not search or not search.strip():
        return True
    needle = search.strip().casefold()
    return needle in " ".join(
        str(value) for value in row.values() if value is not None
    ).casefold()


def date_filters(
    field, date_from: date | None, date_to: date | None
) -> list[Any]:
    filters = []
    if date_from:
        filters.append(field >= date_from)
    if date_to:
        filters.append(field < date_to + timedelta(days=1))
    return filters


async def inventory_balance_rows(
    db: AsyncSession, warehouse_id: int | None, item_id: int | None
) -> list[dict[str, Any]]:
    result = await db.execute(
        select(
            Item.code,
            Item.name,
            Item.unit,
            Warehouse.name.label("warehouse_name"),
            func.coalesce(func.sum(InventoryMovement.quantity), 0).label("quantity"),
        )
        .join(Item, Item.id == InventoryMovement.item_id)
        .join(Warehouse, Warehouse.id == InventoryMovement.warehouse_id)
        .where(Item.is_active.is_(True), Warehouse.is_active.is_(True))
        .where(
            *(
                [InventoryMovement.warehouse_id == warehouse_id]
                if warehouse_id
                else []
            ),
            *([InventoryMovement.item_id == item_id] if item_id else []),
        )
        .group_by(Item.code, Item.name, Item.unit, Warehouse.name)
        .order_by(Item.name, Warehouse.name)
    )
    return [
        {
            "item_code": row.code,
            "item_name": row.name,
            "warehouse_name": row.warehouse_name,
            "quantity": float(row.quantity or 0),
            "unit": row.unit,
        }
        for row in result.all()
    ]


async def movement_rows(
    db: AsyncSession,
    warehouse_id: int | None,
    item_id: int | None,
    date_from: date | None,
    date_to: date | None,
) -> list[dict[str, Any]]:
    filters = [
        *(date_filters(InventoryMovement.movement_date, date_from, date_to)),
        *(
            [InventoryMovement.warehouse_id == warehouse_id]
            if warehouse_id
            else []
        ),
        *([InventoryMovement.item_id == item_id] if item_id else []),
    ]
    result = await db.execute(
        select(InventoryMovement)
        .options(
            selectinload(InventoryMovement.item),
            selectinload(InventoryMovement.warehouse),
            selectinload(InventoryMovement.receipt_detail).selectinload(
                ReceiptDetail.receipt
            ),
            selectinload(InventoryMovement.issue_voucher),
            selectinload(InventoryMovement.transfer),
            selectinload(InventoryMovement.stocktake_line).selectinload(
                StocktakeLine.stocktake
            ),
        )
        .where(*filters)
        .order_by(InventoryMovement.movement_date.desc(), InventoryMovement.id.desc())
    )
    rows = []
    for movement in result.scalars().all():
        reference = None
        if movement.receipt_detail and movement.receipt_detail.receipt:
            reference = movement.receipt_detail.receipt.receipt_number
        elif movement.issue_voucher:
            reference = movement.issue_voucher.issue_number
        elif movement.transfer:
            reference = movement.transfer.transfer_number
        elif movement.stocktake_line and movement.stocktake_line.stocktake:
            reference = movement.stocktake_line.stocktake.stocktake_number
        rows.append(
            {
                "movement_date": movement.movement_date,
                "movement_type": MOVEMENT_LABELS.get(
                    movement.movement_type, movement.movement_type
                ),
                "item_code": movement.item.code,
                "item_name": movement.item.name,
                "warehouse_name": movement.warehouse.name,
                "quantity": movement.quantity,
                "reference": reference,
                "notes": movement.notes,
            }
        )
    return rows


async def receipt_rows(
    db: AsyncSession,
    warehouse_id: int | None,
    item_id: int | None,
    date_from: date | None,
    date_to: date | None,
) -> list[dict[str, Any]]:
    filters = date_filters(Receipt.receipt_date, date_from, date_to)
    result = await db.execute(
        select(Receipt)
        .options(
            selectinload(Receipt.details).selectinload(ReceiptDetail.item),
            selectinload(Receipt.details).selectinload(ReceiptDetail.warehouse),
        )
        .where(*filters)
        .order_by(Receipt.receipt_date.desc(), Receipt.id.desc())
    )
    rows = []
    for receipt in result.scalars().all():
        for detail in receipt.details:
            if warehouse_id and detail.warehouse_id != warehouse_id:
                continue
            if item_id and detail.item_id != item_id:
                continue
            rows.append(
                {
                    "receipt_number": receipt.receipt_number,
                    "receipt_date": receipt.receipt_date,
                    "supplier": receipt.supplier,
                    "item_code": detail.item.code,
                    "item_name": detail.item.name,
                    "warehouse_name": detail.warehouse.name,
                    "quantity": detail.quantity,
                }
            )
    return rows


async def issue_rows(
    db: AsyncSession,
    warehouse_id: int | None,
    department_id: int | None,
    item_id: int | None,
    date_from: date | None,
    date_to: date | None,
) -> list[dict[str, Any]]:
    filters = date_filters(func.date(IssueVoucher.issued_at), date_from, date_to)
    if warehouse_id:
        filters.append(IssueVoucher.warehouse_id == warehouse_id)
    if item_id:
        filters.append(IssueVoucher.item_id == item_id)
    result = await db.execute(
        select(IssueVoucher)
        .options(
            selectinload(IssueVoucher.request).selectinload(IssueRequest.department),
            selectinload(IssueVoucher.item),
            selectinload(IssueVoucher.warehouse),
        )
        .where(*filters)
        .order_by(IssueVoucher.issued_at.desc(), IssueVoucher.id.desc())
    )
    rows = []
    for voucher in result.scalars().all():
        if department_id and voucher.request.department_id != department_id:
            continue
        rows.append(
            {
                "issue_number": voucher.issue_number,
                "issued_at": voucher.issued_at,
                "department_name": voucher.request.department.name,
                "item_code": voucher.item.code,
                "item_name": voucher.item.name,
                "warehouse_name": voucher.warehouse.name,
                "quantity": voucher.quantity,
            }
        )
    return rows


async def transfer_rows(
    db: AsyncSession,
    warehouse_id: int | None,
    item_id: int | None,
    date_from: date | None,
    date_to: date | None,
) -> list[dict[str, Any]]:
    filters = date_filters(func.date(StockTransfer.created_at), date_from, date_to)
    if warehouse_id:
        filters.append(
            or_(
                StockTransfer.source_warehouse_id == warehouse_id,
                StockTransfer.destination_warehouse_id == warehouse_id,
            )
        )
    if item_id:
        filters.append(StockTransfer.item_id == item_id)
    result = await db.execute(
        select(StockTransfer)
        .options(
            selectinload(StockTransfer.source_warehouse),
            selectinload(StockTransfer.destination_warehouse),
            selectinload(StockTransfer.item),
        )
        .where(*filters)
        .order_by(StockTransfer.created_at.desc(), StockTransfer.id.desc())
    )
    return [
        {
            "transfer_number": transfer.transfer_number,
            "created_at": transfer.created_at,
            "source_warehouse_name": transfer.source_warehouse.name,
            "destination_warehouse_name": transfer.destination_warehouse.name,
            "item_code": transfer.item.code,
            "item_name": transfer.item.name,
            "quantity": transfer.quantity,
            "status": STATUS_LABELS.get(transfer.status, transfer.status),
        }
        for transfer in result.scalars().all()
    ]


async def stocktake_rows(
    db: AsyncSession,
    warehouse_id: int | None,
    item_id: int | None,
    date_from: date | None,
    date_to: date | None,
) -> list[dict[str, Any]]:
    filters = date_filters(Stocktake.stocktake_date, date_from, date_to)
    if warehouse_id:
        filters.append(Stocktake.warehouse_id == warehouse_id)
    if item_id:
        filters.append(StocktakeLine.item_id == item_id)
    result = await db.execute(
        select(StocktakeLine)
        .join(Stocktake, Stocktake.id == StocktakeLine.stocktake_id)
        .options(
            selectinload(StocktakeLine.stocktake),
            selectinload(StocktakeLine.item),
            selectinload(StocktakeLine.warehouse),
        )
        .where(*filters)
        .order_by(Stocktake.stocktake_date.desc(), StocktakeLine.id.desc())
    )
    return [
        {
            "stocktake_number": line.stocktake.stocktake_number,
            "stocktake_date": line.stocktake.stocktake_date,
            "warehouse_name": line.warehouse.name,
            "item_code": line.item.code,
            "item_name": line.item.name,
            "system_quantity": line.system_quantity,
            "actual_quantity": line.actual_quantity,
            "difference": line.difference,
            "status": STATUS_LABELS.get(
                line.stocktake.status, line.stocktake.status
            ),
        }
        for line in result.scalars().all()
    ]


async def low_stock_rows(
    db: AsyncSession, warehouse_id: int | None, item_id: int | None
) -> list[dict[str, Any]]:
    filters = [Item.is_active.is_(True), Item.minimum_level > 0]
    if warehouse_id:
        filters.append(Item.warehouse_id == warehouse_id)
    if item_id:
        filters.append(Item.id == item_id)
    result = await db.execute(
        select(
            Item,
            Warehouse,
            func.coalesce(func.sum(InventoryMovement.quantity), 0).label("quantity"),
        )
        .join(Warehouse, Warehouse.id == Item.warehouse_id)
        .outerjoin(
            InventoryMovement,
            (InventoryMovement.item_id == Item.id)
            & (InventoryMovement.warehouse_id == Item.warehouse_id),
        )
        .where(*filters)
        .group_by(Item.id, Warehouse.id)
        .order_by(Item.name)
    )
    rows = []
    for item, warehouse, quantity in result.all():
        current = float(quantity or 0)
        if current < item.minimum_level:
            rows.append(
                {
                    "item_code": item.code,
                    "item_name": item.name,
                    "warehouse_name": warehouse.name,
                    "quantity": current,
                    "minimum_level": item.minimum_level,
                    "shortage": item.minimum_level - current,
                }
            )
    return rows


async def expiring_rows(
    db: AsyncSession,
    warehouse_id: int | None,
    item_id: int | None,
    date_from: date | None,
    date_to: date | None,
    expiry_days: int,
) -> list[dict[str, Any]]:
    start = date_from or date.today()
    end = date_to or (start + timedelta(days=expiry_days))
    rows: dict[tuple[int, int, date], float] = defaultdict(float)
    serial_result = await db.execute(
        select(
            InventorySerial.item_id,
            InventorySerial.warehouse_id,
            InventorySerial.expiry_date,
            func.count(InventorySerial.id),
        )
        .where(
            InventorySerial.is_available.is_(True),
            InventorySerial.expiry_date.is_not(None),
            InventorySerial.expiry_date >= start,
            InventorySerial.expiry_date <= end,
            *(
                [InventorySerial.warehouse_id == warehouse_id]
                if warehouse_id
                else []
            ),
            *([InventorySerial.item_id == item_id] if item_id else []),
        )
        .group_by(
            InventorySerial.item_id,
            InventorySerial.warehouse_id,
            InventorySerial.expiry_date,
        )
    )
    for item_id_value, warehouse_id_value, expiry, quantity in serial_result.all():
        rows[(item_id_value, warehouse_id_value, expiry)] += float(quantity)

    movement_result = await db.execute(
        select(
            InventoryMovement.item_id,
            InventoryMovement.warehouse_id,
            InventoryMovement.expiry_date,
            func.sum(InventoryMovement.quantity),
        )
        .join(Item, Item.id == InventoryMovement.item_id)
        .where(
            Item.requires_serial_number.is_(False),
            InventoryMovement.expiry_date.is_not(None),
            InventoryMovement.expiry_date >= start,
            InventoryMovement.expiry_date <= end,
            *(
                [InventoryMovement.warehouse_id == warehouse_id]
                if warehouse_id
                else []
            ),
            *([InventoryMovement.item_id == item_id] if item_id else []),
        )
        .group_by(
            InventoryMovement.item_id,
            InventoryMovement.warehouse_id,
            InventoryMovement.expiry_date,
        )
    )
    for item_id_value, warehouse_id_value, expiry, quantity in movement_result.all():
        if quantity and quantity > 0:
            rows[(item_id_value, warehouse_id_value, expiry)] += float(quantity)

    if not rows:
        return []
    item_ids = {key[0] for key in rows}
    warehouse_ids = {key[1] for key in rows}
    items = {
        item.id: item
        for item in (
            await db.scalars(select(Item).where(Item.id.in_(item_ids)))
        ).all()
    }
    warehouses = {
        warehouse.id: warehouse
        for warehouse in (
            await db.scalars(select(Warehouse).where(Warehouse.id.in_(warehouse_ids)))
        ).all()
    }
    return [
        {
            "item_code": items[item_id_value].code,
            "item_name": items[item_id_value].name,
            "warehouse_name": warehouses[warehouse_id_value].name,
            "expiry_date": expiry,
            "days_remaining": (expiry - date.today()).days,
            "quantity": quantity,
        }
        for (item_id_value, warehouse_id_value, expiry), quantity in sorted(
            rows.items(), key=lambda pair: pair[0][2]
        )
        if quantity > 0
    ]


async def department_issue_rows(
    db: AsyncSession,
    warehouse_id: int | None,
    department_id: int | None,
    item_id: int | None,
    date_from: date | None,
    date_to: date | None,
) -> list[dict[str, Any]]:
    filters = date_filters(func.date(IssueVoucher.issued_at), date_from, date_to)
    if warehouse_id:
        filters.append(IssueVoucher.warehouse_id == warehouse_id)
    if department_id:
        filters.append(IssueRequest.department_id == department_id)
    if item_id:
        filters.append(IssueVoucher.item_id == item_id)
    result = await db.execute(
        select(
            Department.name,
            func.count(IssueVoucher.id),
            func.coalesce(func.sum(IssueVoucher.quantity), 0),
        )
        .join(IssueRequest, IssueRequest.department_id == Department.id)
        .join(IssueVoucher, IssueVoucher.request_id == IssueRequest.id)
        .where(*filters)
        .group_by(Department.id, Department.name)
        .order_by(Department.name)
    )
    return [
        {
            "department_name": name,
            "voucher_count": count,
            "quantity": float(quantity or 0),
        }
        for name, count, quantity in result.all()
    ]


async def build_report(
    db: AsyncSession,
    report_type: str,
    search: str | None,
    warehouse_id: int | None,
    department_id: int | None,
    item_id: int | None,
    date_from: date | None,
    date_to: date | None,
    expiry_days: int,
    limit: int,
) -> dict[str, Any]:
    if report_type not in REPORTS:
        raise report_error("نوع التقرير غير مدعوم")
    if date_from and date_to and date_from > date_to:
        raise report_error("بداية الفترة يجب أن تسبق نهايتها")
    title, column_definitions = REPORTS[report_type]
    if report_type == "inventory-balance":
        rows = await inventory_balance_rows(db, warehouse_id, item_id)
    elif report_type == "item-movements":
        rows = await movement_rows(db, warehouse_id, item_id, date_from, date_to)
    elif report_type == "receipts":
        rows = await receipt_rows(db, warehouse_id, item_id, date_from, date_to)
    elif report_type == "issues":
        rows = await issue_rows(
            db, warehouse_id, department_id, item_id, date_from, date_to
        )
    elif report_type == "transfers":
        rows = await transfer_rows(db, warehouse_id, item_id, date_from, date_to)
    elif report_type == "stocktakes":
        rows = await stocktake_rows(db, warehouse_id, item_id, date_from, date_to)
    elif report_type == "low-stock":
        rows = await low_stock_rows(db, warehouse_id, item_id)
    elif report_type == "expiring":
        rows = await expiring_rows(
            db, warehouse_id, item_id, date_from, date_to, expiry_days
        )
    else:
        rows = await department_issue_rows(
            db,
            warehouse_id,
            department_id,
            item_id,
            date_from,
            date_to,
        )
    rows = [row for row in rows if text_matches(row, search)][:limit]
    return {
        "report_type": report_type,
        "title": title,
        "columns": [
            {"key": key, "label": label} for key, label in column_definitions
        ],
        "rows": [
            {key: serialize_value(value) for key, value in row.items()}
            for row in rows
        ],
        "generated_at": datetime.now(UTC),
        "row_count": len(rows),
    }


def xlsx_bytes(report: dict[str, Any]) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = str(report["title"])[:31]
    sheet.sheet_view.rightToLeft = True
    columns = report["columns"]
    sheet.append([column["label"] for column in columns])
    for cell in sheet[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="17343A")
    for row in report["rows"]:
        sheet.append([row.get(column["key"], "") for column in columns])
    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = sheet.dimensions
    for column_cells in sheet.columns:
        width = min(max(max(len(str(cell.value or "")) for cell in column_cells) + 2, 12), 36)
        sheet.column_dimensions[column_cells[0].column_letter].width = width
    output = BytesIO()
    workbook.save(output)
    return output.getvalue()


def pdf_bytes(report: dict[str, Any]) -> bytes:
    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    font_name = "Helvetica"
    try:
        pdfmetrics.registerFont(TTFont("WarehouseDejaVu", font_path))
        font_name = "WarehouseDejaVu"
    except (OSError, TTFError):
        pass
    styles = getSampleStyleSheet()
    body = ParagraphStyle(
        "ArabicBody",
        parent=styles["BodyText"],
        fontName=font_name,
        fontSize=7,
        leading=9,
        alignment=TA_RIGHT,
    )
    title_style = ParagraphStyle(
        "ArabicTitle",
        parent=styles["Title"],
        fontName=font_name,
        fontSize=15,
        leading=18,
        alignment=TA_RIGHT,
    )
    columns = report["columns"]
    data = [[Paragraph(str(column["label"]), body) for column in columns]]
    for row in report["rows"]:
        data.append(
            [
                Paragraph(str(row.get(column["key"], "") or ""), body)
                for column in columns
            ]
        )
    output = BytesIO()
    document = SimpleDocTemplate(
        output,
        pagesize=landscape(A4),
        rightMargin=10 * mm,
        leftMargin=10 * mm,
        topMargin=10 * mm,
        bottomMargin=10 * mm,
    )
    story = [
        Paragraph(str(report["title"]), title_style),
        Spacer(1, 5 * mm),
        Table(
            data,
            repeatRows=1,
            hAlign="RIGHT",
            style=TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#17343A")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#CBD5D7")),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                    ("LEFTPADDING", (0, 0), (-1, -1), 5),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            ),
        ),
    ]
    document.build(story)
    return output.getvalue()


def query_params(
    search: str | None,
    warehouse_id: int | None,
    department_id: int | None,
    item_id: int | None,
    date_from: date | None,
    date_to: date | None,
    expiry_days: int,
    limit: int,
) -> dict[str, Any]:
    return {
        "search": search,
        "warehouse_id": warehouse_id,
        "department_id": department_id,
        "item_id": item_id,
        "date_from": date_from,
        "date_to": date_to,
        "expiry_days": expiry_days,
        "limit": limit,
    }


@router.get("/reports/{reportType}", response_model=ReportResponse)
async def get_report(
    reportType: str,
    search: str | None = Query(default=None, max_length=120),
    warehouse_id: int | None = None,
    department_id: int | None = None,
    item_id: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    expiry_days: int = Query(default=30, ge=1, le=3650),
    limit: int = Query(default=1000, ge=1, le=5000),
    _: User = Depends(require_permission("reports:read")),
    db: AsyncSession = Depends(get_db),
) -> ReportResponse:
    report = await build_report(
        db, reportType, **query_params(
            search,
            warehouse_id,
            department_id,
            item_id,
            date_from,
            date_to,
            expiry_days,
            limit,
        )
    )
    return ReportResponse.model_validate(report)


@router.get("/reports/{reportType}/export")
async def export_report(
    reportType: str,
    format: str = Query(pattern="^(pdf|xlsx)$"),
    search: str | None = Query(default=None, max_length=120),
    warehouse_id: int | None = None,
    department_id: int | None = None,
    item_id: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    expiry_days: int = Query(default=30, ge=1, le=3650),
    limit: int = Query(default=1000, ge=1, le=5000),
    _: User = Depends(require_permission("reports:read")),
    db: AsyncSession = Depends(get_db),
) -> Response:
    report = await build_report(
        db, reportType, **query_params(
            search,
            warehouse_id,
            department_id,
            item_id,
            date_from,
            date_to,
            expiry_days,
            limit,
        )
    )
    if format == "xlsx":
        content = xlsx_bytes(report)
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    else:
        content = pdf_bytes(report)
        media_type = "application/pdf"
    return Response(
        content=content,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="report-{reportType}.{format}"'
        },
    )