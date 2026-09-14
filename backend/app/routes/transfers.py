from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..db import get_db
from ..audit import add_audit_log
from ..dependencies import require_permission
from ..inventory import lock_item_inventory
from ..models import (
    InventoryMovement,
    InventorySerial,
    Item,
    StockTransfer,
    TransferSerial,
    User,
    Warehouse,
)
from ..schemas import (
    StockTransfer as StockTransferSchema,
    StockTransferInput,
    StockTransferPreview,
    StockTransferReceiveInput,
)
from ..serializers import to_stock_transfer, to_stock_transfer_preview

router = APIRouter(tags=["transfers"])


def transfer_error(message: str) -> HTTPException:
    return HTTPException(status_code=400, detail=message)


async def load_transfer(
    db: AsyncSession, transfer_id: int
) -> StockTransfer | None:
    result = await db.execute(
        select(StockTransfer)
        .options(
            selectinload(StockTransfer.source_warehouse),
            selectinload(StockTransfer.destination_warehouse),
            selectinload(StockTransfer.item),
            selectinload(StockTransfer.created_by),
            selectinload(StockTransfer.received_by),
            selectinload(StockTransfer.completed_by),
            selectinload(StockTransfer.serials),
        )
        .where(StockTransfer.id == transfer_id)
    )
    return result.scalar_one_or_none()


async def source_availability(
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
    available = await db.scalar(
        select(func.count(InventorySerial.id)).where(
            InventorySerial.item_id == item_id,
            InventorySerial.warehouse_id == warehouse_id,
            InventorySerial.is_available.is_(True),
        )
    )
    return current_balance, float(available or 0)


async def serialize_transfer(
    db: AsyncSession, transfer: StockTransfer
) -> StockTransferSchema:
    current, available = await source_availability(
        db,
        transfer.item_id,
        transfer.source_warehouse_id,
        transfer.item.requires_serial_number,
    )
    return to_stock_transfer(transfer, current, available)


async def require_transfer(db: AsyncSession, transfer_id: int) -> StockTransfer:
    transfer = await load_transfer(db, transfer_id)
    if transfer is None:
        raise HTTPException(status_code=404, detail="التحويل غير موجود")
    return transfer


def require_status(transfer: StockTransfer, expected: str, target: str) -> None:
    if transfer.status != expected:
        raise transfer_error(
            f"لا يمكن نقل التحويل من حالة {transfer.status} إلى {target}"
        )


@router.get("/transfers", response_model=list[StockTransferSchema])
async def list_transfers(
    _: User = Depends(require_permission("transfers:read")),
    db: AsyncSession = Depends(get_db),
) -> list[StockTransferSchema]:
    result = await db.execute(
        select(StockTransfer)
        .options(
            selectinload(StockTransfer.source_warehouse),
            selectinload(StockTransfer.destination_warehouse),
            selectinload(StockTransfer.item),
            selectinload(StockTransfer.created_by),
            selectinload(StockTransfer.received_by),
            selectinload(StockTransfer.completed_by),
            selectinload(StockTransfer.serials),
        )
        .order_by(StockTransfer.id.desc())
    )
    return [
        await serialize_transfer(db, transfer)
        for transfer in result.scalars().all()
    ]


@router.post(
    "/transfers",
    response_model=StockTransferSchema,
    status_code=status.HTTP_201_CREATED,
)
async def create_transfer(
    payload: StockTransferInput,
    user: User = Depends(require_permission("transfers:write")),
    db: AsyncSession = Depends(get_db),
) -> StockTransferSchema:
    if payload.source_warehouse_id == payload.destination_warehouse_id:
        raise transfer_error("يجب أن يختلف المخزن المصدر عن المخزن المستلم")
    source = await db.get(Warehouse, payload.source_warehouse_id)
    destination = await db.get(Warehouse, payload.destination_warehouse_id)
    if source is None or not source.is_active:
        raise transfer_error("المخزن المصدر غير موجود أو معطل")
    if destination is None or not destination.is_active:
        raise transfer_error("المخزن المستلم غير موجود أو معطل")
    if source.warehouse_type == destination.warehouse_type:
        raise transfer_error("التحويل يجب أن يكون بين المخزن الرئيسي ومخزن فرعي")
    item = await db.get(Item, payload.item_id)
    if item is None or not item.is_active:
        raise transfer_error("الصنف المحدد غير موجود أو معطل")
    if not payload.reason.strip():
        raise transfer_error("سبب التحويل مطلوب")

    transfer = StockTransfer(
        transfer_number="PENDING",
        source_warehouse_id=source.id,
        destination_warehouse_id=destination.id,
        item_id=item.id,
        quantity=payload.quantity,
        reason=payload.reason.strip(),
        notes=payload.notes.strip(),
        status="draft",
        created_by_id=user.id,
    )
    db.add(transfer)
    await db.flush()
    transfer.transfer_number = f"TRF-{datetime.now(timezone.utc).year}-{transfer.id:06d}"
    try:
        add_audit_log(
            db,
            user=user,
            action="transfer",
            document_number=transfer.transfer_number,
            details=(
                f"استلام من {transfer.source_warehouse.name} إلى "
                f"{transfer.destination_warehouse.name}"
            ),
        )
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise transfer_error("تعذر حفظ مسودة التحويل")
    saved = await load_transfer(db, transfer.id)
    return await serialize_transfer(db, saved)


@router.get("/transfers/{transferId}", response_model=StockTransferSchema)
async def get_transfer(
    transferId: int,
    _: User = Depends(require_permission("transfers:read")),
    db: AsyncSession = Depends(get_db),
) -> StockTransferSchema:
    transfer = await require_transfer(db, transferId)
    return await serialize_transfer(db, transfer)


@router.post("/transfers/{transferId}/send", response_model=StockTransferSchema)
async def send_transfer(
    transferId: int,
    _: User = Depends(require_permission("transfers:write")),
    db: AsyncSession = Depends(get_db),
) -> StockTransferSchema:
    transfer = await require_transfer(db, transferId)
    require_status(transfer, "draft", "مرسل")
    transfer.status = "sent"
    transfer.sent_at = datetime.now(timezone.utc)
    await db.commit()
    saved = await load_transfer(db, transfer.id)
    return await serialize_transfer(db, saved)


@router.get(
    "/transfers/{transferId}/receive-preview",
    response_model=StockTransferPreview,
)
async def get_receive_preview(
    transferId: int,
    _: User = Depends(require_permission("transfers:read")),
    db: AsyncSession = Depends(get_db),
) -> StockTransferPreview:
    transfer = await require_transfer(db, transferId)
    require_status(transfer, "sent", "الاستلام")
    current, available = await source_availability(
        db,
        transfer.item_id,
        transfer.source_warehouse_id,
        transfer.item.requires_serial_number,
    )
    serial_result = await db.execute(
        select(InventorySerial.serial_number)
        .where(
            InventorySerial.item_id == transfer.item_id,
            InventorySerial.warehouse_id == transfer.source_warehouse_id,
            InventorySerial.is_available.is_(True),
        )
        .order_by(InventorySerial.serial_number)
    )
    return to_stock_transfer_preview(
        transfer,
        current,
        available,
        list(serial_result.scalars().all()),
    )


@router.post(
    "/transfers/{transferId}/receive",
    response_model=StockTransferSchema,
)
async def receive_transfer(
    transferId: int,
    payload: StockTransferReceiveInput,
    user: User = Depends(require_permission("transfers:receive")),
    db: AsyncSession = Depends(get_db),
) -> StockTransferSchema:
    await db.execute(
        select(StockTransfer.id)
        .where(StockTransfer.id == transferId)
        .with_for_update()
    )
    transfer = await require_transfer(db, transferId)
    require_status(transfer, "sent", "مستلم")
    item = transfer.item
    await lock_item_inventory(db, transfer.item_id)
    current, _ = await source_availability(
        db,
        transfer.item_id,
        transfer.source_warehouse_id,
        item.requires_serial_number,
    )
    if transfer.quantity > current:
        raise transfer_error(
            f"الرصيد المصدر غير كافٍ. المطلوب {transfer.quantity:g} والمتاح {max(current, 0):g}"
        )

    serial_numbers = [
        serial.strip() for serial in payload.serial_numbers if serial.strip()
    ]
    if item.requires_serial_number:
        if not transfer.quantity.is_integer() or len(serial_numbers) != int(
            transfer.quantity
        ):
            raise transfer_error("حدد رقمًا تسلسليًا لكل وحدة محولة")
        if len(serial_numbers) != len(set(serial_numbers)):
            raise transfer_error("لا يمكن تكرار الرقم التسلسلي داخل التحويل")
        serial_result = await db.execute(
            select(InventorySerial)
            .where(
                InventorySerial.item_id == transfer.item_id,
                InventorySerial.warehouse_id == transfer.source_warehouse_id,
                InventorySerial.serial_number.in_(serial_numbers),
                InventorySerial.is_available.is_(True),
            )
            .with_for_update()
        )
        available_serials = serial_result.scalars().all()
        if len(available_serials) != len(serial_numbers):
            raise transfer_error("يوجد رقم تسلسلي غير متاح أو غير موجود في المصدر")
    elif serial_numbers:
        raise transfer_error("هذا الصنف لا يتطلب أرقامًا تسلسلية")
    else:
        available_serials = []

    now = datetime.now(timezone.utc)
    transfer_out = InventoryMovement(
        movement_type="transfer_out",
        movement_date=now.date(),
        item_id=transfer.item_id,
        warehouse_id=transfer.source_warehouse_id,
        quantity=-transfer.quantity,
        transfer_id=transfer.id,
        notes=f"تحويل خارج {transfer.transfer_number}",
    )
    transfer_in = InventoryMovement(
        movement_type="transfer_in",
        movement_date=now.date(),
        item_id=transfer.item_id,
        warehouse_id=transfer.destination_warehouse_id,
        quantity=transfer.quantity,
        transfer_id=transfer.id,
        notes=f"تحويل داخل {transfer.transfer_number}",
    )
    db.add_all([transfer_out, transfer_in])
    await db.flush()
    for serial in available_serials:
        serial.warehouse_id = transfer.destination_warehouse_id
        serial.storage_location_id = None
        transfer.serials.append(
            TransferSerial(
                transfer_id=transfer.id,
                serial_id=serial.id,
                serial_number=serial.serial_number,
            )
        )
    transfer.status = "received"
    transfer.received_by_id = user.id
    transfer.received_by = user
    transfer.received_at = now
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise transfer_error("تعذر تأكيد استلام التحويل")
    saved = await load_transfer(db, transfer.id)
    return await serialize_transfer(db, saved)


@router.post("/transfers/{transferId}/complete", response_model=StockTransferSchema)
async def complete_transfer(
    transferId: int,
    user: User = Depends(require_permission("transfers:write")),
    db: AsyncSession = Depends(get_db),
) -> StockTransferSchema:
    transfer = await require_transfer(db, transferId)
    require_status(transfer, "received", "مكتمل")
    transfer.status = "completed"
    transfer.completed_by_id = user.id
    transfer.completed_by = user
    transfer.completed_at = datetime.now(timezone.utc)
    add_audit_log(
        db,
        user=user,
        action="transfer",
        document_number=transfer.transfer_number,
        details="تم إكمال دورة التحويل بعد تأكيد الاستلام",
    )
    await db.commit()
    saved = await load_transfer(db, transfer.id)
    return await serialize_transfer(db, saved)