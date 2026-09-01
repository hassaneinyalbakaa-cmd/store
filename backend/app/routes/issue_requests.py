from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
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
    User,
    Warehouse,
)
from ..schemas import (
    IssueRequest as IssueRequestSchema,
    IssueRequestInput,
    IssueRequestIssueInput,
    IssueRequestPreview as IssueRequestPreviewSchema,
    IssueRequestRejectionInput,
    IssueVoucher as IssueVoucherSchema,
)
from ..serializers import (
    to_issue_request,
    to_issue_request_preview,
    to_issue_voucher,
)

router = APIRouter(tags=["issue_requests", "issue_vouchers"])


def request_error(message: str) -> HTTPException:
    return HTTPException(status_code=400, detail=message)


def not_found(message: str) -> HTTPException:
    return HTTPException(status_code=404, detail=message)


async def load_issue_request(
    db: AsyncSession, request_id: int
) -> IssueRequest | None:
    result = await db.execute(
        select(IssueRequest)
        .options(
            selectinload(IssueRequest.department),
            selectinload(IssueRequest.item).selectinload(Item.warehouse),
            selectinload(IssueRequest.created_by),
            selectinload(IssueRequest.issue_voucher),
        )
        .where(IssueRequest.id == request_id)
    )
    return result.scalar_one_or_none()


async def load_issue_voucher(
    db: AsyncSession, voucher_id: int
) -> IssueVoucher | None:
    result = await db.execute(
        select(IssueVoucher)
        .options(
            selectinload(IssueVoucher.request).selectinload(IssueRequest.department),
            selectinload(IssueVoucher.request)
            .selectinload(IssueRequest.item)
            .selectinload(Item.warehouse),
            selectinload(IssueVoucher.item),
            selectinload(IssueVoucher.warehouse),
            selectinload(IssueVoucher.issued_by),
            selectinload(IssueVoucher.serials),
        )
        .where(IssueVoucher.id == voucher_id)
    )
    return result.scalar_one_or_none()


async def get_availability(
    db: AsyncSession, item_id: int, warehouse_id: int, requires_serial: bool
) -> tuple[float, float]:
    balance = await db.scalar(
        select(func.coalesce(func.sum(InventoryMovement.quantity), 0)).where(
            InventoryMovement.item_id == item_id,
            InventoryMovement.warehouse_id == warehouse_id,
        )
    )
    current_balance = float(balance or 0)
    if not requires_serial:
        return current_balance, max(current_balance, 0)
    serial_count = await db.scalar(
        select(func.count(InventorySerial.id)).where(
            InventorySerial.item_id == item_id,
            InventorySerial.warehouse_id == warehouse_id,
            InventorySerial.is_available.is_(True),
        )
    )
    return current_balance, float(serial_count or 0)


async def serialize_request(
    db: AsyncSession, request: IssueRequest
) -> IssueRequestSchema:
    current_balance, available_quantity = await get_availability(
        db,
        request.item_id,
        request.item.warehouse_id,
        request.item.requires_serial_number,
    )
    return to_issue_request(request, current_balance, available_quantity)


async def require_request(
    db: AsyncSession, request_id: int
) -> IssueRequest:
    request = await load_issue_request(db, request_id)
    if request is None:
        raise not_found("طلب الصرف غير موجود")
    return request


def require_status(request: IssueRequest, expected: str, target: str) -> None:
    if request.status != expected:
        raise request_error(
            f"لا يمكن نقل الطلب من حالة {request.status} إلى {target}"
        )


@router.get("/issue-requests", response_model=list[IssueRequestSchema])
async def list_issue_requests(
    _: User = Depends(require_permission("issue_requests:read")),
    db: AsyncSession = Depends(get_db),
) -> list[IssueRequestSchema]:
    result = await db.execute(
        select(IssueRequest)
        .options(
            selectinload(IssueRequest.department),
            selectinload(IssueRequest.item).selectinload(Item.warehouse),
            selectinload(IssueRequest.created_by),
            selectinload(IssueRequest.issue_voucher),
        )
        .order_by(IssueRequest.id.desc())
    )
    return [await serialize_request(db, request) for request in result.scalars().all()]


@router.post(
    "/issue-requests",
    response_model=IssueRequestSchema,
    status_code=status.HTTP_201_CREATED,
)
async def create_issue_request(
    payload: IssueRequestInput,
    user: User = Depends(require_permission("issue_requests:write")),
    db: AsyncSession = Depends(get_db),
) -> IssueRequestSchema:
    department = await db.get(Department, payload.department_id)
    if department is None or not department.is_active:
        raise request_error("القسم المحدد غير موجود أو معطل")
    item_result = await db.execute(
        select(Item)
        .options(selectinload(Item.warehouse))
        .where(Item.id == payload.item_id)
    )
    item = item_result.scalar_one_or_none()
    if item is None or not item.is_active:
        raise request_error("الصنف المحدد غير موجود أو معطل")
    if not item.warehouse.is_active:
        raise request_error("لا يمكن طلب صنف من مخزن معطل")
    if not payload.reason.strip():
        raise request_error("سبب الصرف مطلوب")

    issue_request = IssueRequest(
        request_number="PENDING",
        department_id=department.id,
        request_date=payload.request_date,
        reason=payload.reason.strip(),
        item_id=item.id,
        quantity=payload.quantity,
        notes=payload.notes.strip(),
        status="draft",
        created_by_id=user.id,
    )
    db.add(issue_request)
    await db.flush()
    issue_request.request_number = f"REQ-{payload.request_date.year}-{issue_request.id:06d}"
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise request_error("تعذر حفظ طلب الصرف")
    saved = await load_issue_request(db, issue_request.id)
    return await serialize_request(db, saved)


@router.get("/issue-requests/{request_id}", response_model=IssueRequestSchema)
async def get_issue_request(
    request_id: int,
    _: User = Depends(require_permission("issue_requests:read")),
    db: AsyncSession = Depends(get_db),
) -> IssueRequestSchema:
    request = await require_request(db, request_id)
    return await serialize_request(db, request)


@router.post("/issue-requests/{request_id}/submit", response_model=IssueRequestSchema)
async def submit_issue_request(
    request_id: int,
    _: User = Depends(require_permission("issue_requests:write")),
    db: AsyncSession = Depends(get_db),
) -> IssueRequestSchema:
    request = await require_request(db, request_id)
    require_status(request, "draft", "sent")
    request.status = "sent"
    await db.commit()
    saved = await load_issue_request(db, request.id)
    return await serialize_request(db, saved)


@router.post("/issue-requests/{request_id}/approve", response_model=IssueRequestSchema)
async def approve_issue_request(
    request_id: int,
    _: User = Depends(require_permission("issues:write")),
    db: AsyncSession = Depends(get_db),
) -> IssueRequestSchema:
    request = await require_request(db, request_id)
    require_status(request, "sent", "approved")
    request.status = "approved"
    request.rejection_reason = None
    await db.commit()
    saved = await load_issue_request(db, request.id)
    return await serialize_request(db, saved)


@router.post("/issue-requests/{request_id}/reject", response_model=IssueRequestSchema)
async def reject_issue_request(
    request_id: int,
    payload: IssueRequestRejectionInput,
    _: User = Depends(require_permission("issues:write")),
    db: AsyncSession = Depends(get_db),
) -> IssueRequestSchema:
    request = await require_request(db, request_id)
    require_status(request, "sent", "rejected")
    if not payload.rejection_reason.strip():
        raise request_error("سبب الرفض مطلوب")
    request.status = "rejected"
    request.rejection_reason = payload.rejection_reason.strip()
    await db.commit()
    saved = await load_issue_request(db, request.id)
    return await serialize_request(db, saved)


@router.get(
    "/issue-requests/{request_id}/issue-preview",
    response_model=IssueRequestPreviewSchema,
)
async def get_issue_request_preview(
    request_id: int,
    _: User = Depends(require_permission("issues:read")),
    db: AsyncSession = Depends(get_db),
) -> IssueRequestPreviewSchema:
    request = await require_request(db, request_id)
    require_status(request, "approved", "الصرف")
    current_balance, available_quantity = await get_availability(
        db,
        request.item_id,
        request.item.warehouse_id,
        request.item.requires_serial_number,
    )
    serial_result = await db.execute(
        select(InventorySerial.serial_number)
        .where(
            InventorySerial.item_id == request.item_id,
            InventorySerial.warehouse_id == request.item.warehouse_id,
            InventorySerial.is_available.is_(True),
        )
        .order_by(InventorySerial.serial_number)
    )
    return to_issue_request_preview(
        request,
        current_balance,
        available_quantity,
        list(serial_result.scalars().all()),
    )


@router.post(
    "/issue-requests/{request_id}/issue",
    response_model=IssueVoucherSchema,
    status_code=status.HTTP_201_CREATED,
)
async def issue_request(
    request_id: int,
    payload: IssueRequestIssueInput,
    user: User = Depends(require_permission("issues:write")),
    db: AsyncSession = Depends(get_db),
) -> IssueVoucherSchema:
    request = await require_request(db, request_id)
    require_status(request, "approved", "تم الصرف")
    item = request.item
    warehouse_id = item.warehouse_id

    balance_result = await db.execute(
        select(InventoryMovement.quantity).where(
            InventoryMovement.item_id == request.item_id,
            InventoryMovement.warehouse_id == warehouse_id,
        )
    )
    current_balance = sum(float(value) for value in balance_result.scalars().all())
    if request.quantity > current_balance:
        raise request_error(
            f"الرصيد غير كافٍ. المطلوب {request.quantity:g} والمتاح {max(current_balance, 0):g}"
        )

    serials = [serial.strip() for serial in payload.serial_numbers if serial.strip()]
    if item.requires_serial_number:
        if not request.quantity.is_integer() or len(serials) != int(request.quantity):
            raise request_error("حدد رقمًا تسلسليًا لكل وحدة مصروفة")
        if len(serials) != len(set(serials)):
            raise request_error("لا يمكن تكرار الرقم التسلسلي داخل سند الصرف")
        serial_result = await db.execute(
            select(InventorySerial)
            .where(
                InventorySerial.item_id == request.item_id,
                InventorySerial.warehouse_id == warehouse_id,
                InventorySerial.serial_number.in_(serials),
                InventorySerial.is_available.is_(True),
            )
            .with_for_update()
        )
        available_serials = serial_result.scalars().all()
        if len(available_serials) != len(serials):
            raise request_error("يوجد رقم تسلسلي غير متاح أو غير موجود في الرصيد")
    elif serials:
        raise request_error("هذا الصنف لا يتطلب أرقامًا تسلسلية")
    else:
        available_serials = []

    voucher = IssueVoucher(
        issue_number="PENDING",
        request_id=request.id,
        item_id=item.id,
        warehouse_id=warehouse_id,
        quantity=request.quantity,
        issued_by_id=user.id,
        issued_at=datetime.now(timezone.utc),
    )
    db.add(voucher)
    await db.flush()
    voucher.issue_number = f"ISS-{voucher.issued_at.year}-{voucher.id:06d}"
    movement = InventoryMovement(
        movement_type="issue",
        movement_date=date.today(),
        item_id=item.id,
        warehouse_id=warehouse_id,
        storage_location_id=item.storage_location_id,
        quantity=-request.quantity,
        issue_voucher_id=voucher.id,
        notes=f"سند صرف {voucher.issue_number}",
    )
    db.add(movement)
    request.status = "issued"
    request.rejection_reason = None
    await db.flush()
    for serial in available_serials:
        serial.is_available = False
        serial.issue_voucher_id = voucher.id
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise request_error("تعذر إتمام الصرف؛ ربما تم صرف الطلب مسبقًا")
    saved = await load_issue_voucher(db, voucher.id)
    return to_issue_voucher(saved)


@router.post("/issue-requests/{request_id}/close", response_model=IssueRequestSchema)
async def close_issue_request(
    request_id: int,
    _: User = Depends(require_permission("issues:write")),
    db: AsyncSession = Depends(get_db),
) -> IssueRequestSchema:
    request = await require_request(db, request_id)
    require_status(request, "issued", "مغلق")
    request.status = "closed"
    await db.commit()
    saved = await load_issue_request(db, request.id)
    return await serialize_request(db, saved)


@router.get("/issue-vouchers", response_model=list[IssueVoucherSchema])
async def list_issue_vouchers(
    _: User = Depends(require_permission("issues:read")),
    db: AsyncSession = Depends(get_db),
) -> list[IssueVoucherSchema]:
    result = await db.execute(
        select(IssueVoucher)
        .options(
            selectinload(IssueVoucher.request).selectinload(IssueRequest.department),
            selectinload(IssueVoucher.item),
            selectinload(IssueVoucher.warehouse),
            selectinload(IssueVoucher.issued_by),
            selectinload(IssueVoucher.serials),
        )
        .order_by(IssueVoucher.id.desc())
    )
    return [to_issue_voucher(voucher) for voucher in result.scalars().all()]


@router.get("/issue-vouchers/{voucher_id}", response_model=IssueVoucherSchema)
async def get_issue_voucher(
    voucher_id: int,
    _: User = Depends(require_permission("issues:read")),
    db: AsyncSession = Depends(get_db),
) -> IssueVoucherSchema:
    voucher = await load_issue_voucher(db, voucher_id)
    if voucher is None:
        raise not_found("سند الصرف غير موجود")
    return to_issue_voucher(voucher)