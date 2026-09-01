from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..db import get_db
from ..dependencies import require_permission
from ..models import (
    InventoryMovement,
    InventorySerial,
    Item,
    Receipt,
    ReceiptDetail,
    StorageLocation,
    User,
    Warehouse,
)
from ..schemas import (
    InventoryBalance as InventoryBalanceSchema,
    InventoryExpiry as InventoryExpirySchema,
    InventoryMovement as InventoryMovementSchema,
    OpeningBalanceInput,
    Receipt as ReceiptSchema,
    ReceiptInput,
)
from ..serializers import (
    to_inventory_balance,
    to_inventory_expiry,
    to_inventory_movement,
    to_receipt,
)

router = APIRouter(tags=["receipts", "inventory"])


def relation_error(message: str) -> HTTPException:
    return HTTPException(status_code=400, detail=message)


async def get_item(db: AsyncSession, item_id: int) -> Item | None:
    return await db.get(Item, item_id)


async def get_receipt(db: AsyncSession, receipt_id: int) -> Receipt | None:
    result = await db.execute(
        select(Receipt)
        .options(
            selectinload(Receipt.details).selectinload(ReceiptDetail.item),
            selectinload(Receipt.details).selectinload(ReceiptDetail.warehouse),
            selectinload(Receipt.details).selectinload(ReceiptDetail.storage_location),
            selectinload(Receipt.details).selectinload(ReceiptDetail.serials),
        )
        .where(Receipt.id == receipt_id)
    )
    return result.scalar_one_or_none()


async def get_movement(db: AsyncSession, movement_id: int) -> InventoryMovement | None:
    result = await db.execute(
        select(InventoryMovement)
        .options(
            selectinload(InventoryMovement.item),
            selectinload(InventoryMovement.warehouse),
            selectinload(InventoryMovement.storage_location),
            selectinload(InventoryMovement.receipt_detail).selectinload(
                ReceiptDetail.receipt
            ),
        )
        .where(InventoryMovement.id == movement_id)
    )
    return result.scalar_one_or_none()


async def validate_destination(
    db: AsyncSession,
    item_id: int,
    warehouse_id: int,
    location_payload,
) -> tuple[Item, StorageLocation | None]:
    item = await get_item(db, item_id)
    if item is None:
        raise relation_error("الصنف المحدد غير موجود")
    if not item.is_active:
        raise relation_error("لا يمكن استلام صنف معطل")
    warehouse = await db.get(Warehouse, warehouse_id)
    if warehouse is None:
        raise relation_error("المخزن المحدد غير موجود")
    if not warehouse.is_active:
        raise relation_error("لا يمكن إضافة مخزون إلى مخزن معطل")
    if item.warehouse_id != warehouse_id:
        raise relation_error("المخزن المحدد لا يطابق مخزن الصنف")

    if location_payload is None:
        return item, None
    values = {
        "area": location_payload.area.strip(),
        "shelf": location_payload.shelf.strip(),
        "bin": location_payload.bin.strip(),
    }
    result = await db.execute(
        select(StorageLocation).where(
            StorageLocation.warehouse_id == warehouse_id,
            StorageLocation.area == values["area"],
            StorageLocation.shelf == values["shelf"],
            StorageLocation.bin == values["bin"],
        )
    )
    location = result.scalar_one_or_none()
    if location is None:
        location = StorageLocation(warehouse_id=warehouse_id, **values)
        db.add(location)
        await db.flush()
    return item, location


async def validate_serials(
    db: AsyncSession,
    item: Item,
    quantity: float,
    expiry_date: date | None,
    serial_numbers: list[str],
) -> list[str]:
    serials = [serial.strip() for serial in serial_numbers if serial.strip()]
    if item.requires_serial_number:
        if not quantity.is_integer() or len(serials) != int(quantity):
            raise relation_error("هذا الصنف يتطلب رقمًا تسلسليًا لكل وحدة")
    elif serials:
        raise relation_error("هذا الصنف لا يتطلب أرقامًا تسلسلية")
    if item.requires_expiry_date and expiry_date is None:
        raise relation_error("هذا الصنف يتطلب تسجيل تاريخ انتهاء")
    if len(serials) != len(set(serials)):
        raise relation_error("لا يمكن تكرار الرقم التسلسلي داخل الحركة")
    if serials:
        existing = await db.execute(
            select(InventorySerial.serial_number).where(
                InventorySerial.serial_number.in_(serials)
            )
        )
        if existing.scalars().first() is not None:
            raise relation_error("الرقم التسلسلي مستخدم مسبقًا")
    return serials


@router.get("/receipts", response_model=list[ReceiptSchema])
async def list_receipts(
    _: User = Depends(require_permission("receipts:read")),
    db: AsyncSession = Depends(get_db),
) -> list[ReceiptSchema]:
    result = await db.execute(
        select(Receipt)
        .options(
            selectinload(Receipt.details).selectinload(ReceiptDetail.item),
            selectinload(Receipt.details).selectinload(ReceiptDetail.warehouse),
            selectinload(Receipt.details).selectinload(ReceiptDetail.storage_location),
            selectinload(Receipt.details).selectinload(ReceiptDetail.serials),
        )
        .order_by(Receipt.id.desc())
    )
    return [to_receipt(receipt) for receipt in result.scalars().all()]


@router.get("/receipts/{receipt_id}", response_model=ReceiptSchema)
async def get_receipt_route(
    receipt_id: int,
    _: User = Depends(require_permission("receipts:read")),
    db: AsyncSession = Depends(get_db),
) -> ReceiptSchema:
    receipt = await get_receipt(db, receipt_id)
    if receipt is None:
        raise HTTPException(status_code=404, detail="سند الاستلام غير موجود")
    return to_receipt(receipt)


@router.post(
    "/receipts",
    response_model=ReceiptSchema,
    status_code=status.HTTP_201_CREATED,
)
async def create_receipt(
    payload: ReceiptInput,
    _: User = Depends(require_permission("receipts:write")),
    db: AsyncSession = Depends(get_db),
) -> ReceiptSchema:
    validated_details = []
    all_serials: list[str] = []
    for detail_payload in payload.details:
        item, location = await validate_destination(
            db,
            detail_payload.item_id,
            detail_payload.warehouse_id,
            detail_payload.storage_location,
        )
        serials = await validate_serials(
            db,
            item,
            detail_payload.quantity,
            detail_payload.expiry_date,
            detail_payload.serial_numbers,
        )
        validated_details.append((detail_payload, item, location, serials))
        all_serials.extend(serials)
    if len(all_serials) != len(set(all_serials)):
        raise relation_error("لا يمكن تكرار الرقم التسلسلي داخل سند الاستلام")

    receipt = Receipt(
        receipt_number="PENDING",
        receipt_date=payload.receipt_date,
        supplier=payload.supplier.strip(),
        document_number=payload.document_number.strip(),
        notes=payload.notes.strip(),
    )
    db.add(receipt)
    await db.flush()
    receipt.receipt_number = f"REC-{payload.receipt_date.year}-{receipt.id:06d}"

    for detail_payload, item, location, serials in validated_details:
        detail = ReceiptDetail(
            receipt_id=receipt.id,
            item_id=item.id,
            warehouse_id=detail_payload.warehouse_id,
            storage_location_id=location.id if location else None,
            quantity=detail_payload.quantity,
            expiry_date=detail_payload.expiry_date,
        )
        db.add(detail)
        await db.flush()
        movement = InventoryMovement(
            movement_type="receipt",
            movement_date=payload.receipt_date,
            item_id=item.id,
            warehouse_id=detail_payload.warehouse_id,
            storage_location_id=location.id if location else None,
            quantity=detail_payload.quantity,
            expiry_date=detail_payload.expiry_date,
            receipt_detail_id=detail.id,
            notes=payload.notes.strip(),
        )
        db.add(movement)
        await db.flush()
        for serial_number in serials:
            db.add(
                InventorySerial(
                    serial_number=serial_number,
                    item_id=item.id,
                    warehouse_id=detail_payload.warehouse_id,
                    storage_location_id=location.id if location else None,
                    movement_id=movement.id,
                    receipt_detail_id=detail.id,
                    expiry_date=detail_payload.expiry_date,
                )
            )
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise relation_error("تعذر حفظ السند؛ تحقق من الأرقام التسلسلية وعدم تكرارها")
    saved = await get_receipt(db, receipt.id)
    return to_receipt(saved)


@router.get("/inventory/movements", response_model=list[InventoryMovementSchema])
async def list_inventory_movements(
    _: User = Depends(require_permission("inventory:read")),
    db: AsyncSession = Depends(get_db),
) -> list[InventoryMovementSchema]:
    result = await db.execute(
        select(InventoryMovement)
        .options(
            selectinload(InventoryMovement.item),
            selectinload(InventoryMovement.warehouse),
            selectinload(InventoryMovement.storage_location),
            selectinload(InventoryMovement.receipt_detail).selectinload(
                ReceiptDetail.receipt
            ),
        )
        .order_by(InventoryMovement.id.desc())
    )
    return [to_inventory_movement(movement) for movement in result.scalars().all()]


@router.get("/inventory/balances", response_model=list[InventoryBalanceSchema])
async def list_inventory_balances(
    _: User = Depends(require_permission("inventory:read")),
    db: AsyncSession = Depends(get_db),
) -> list[InventoryBalanceSchema]:
    result = await db.execute(
        select(
            Item,
            Warehouse,
            StorageLocation,
            func.sum(InventoryMovement.quantity),
        )
        .join(Item, Item.id == InventoryMovement.item_id)
        .join(Warehouse, Warehouse.id == InventoryMovement.warehouse_id)
        .outerjoin(
            StorageLocation,
            StorageLocation.id == InventoryMovement.storage_location_id,
        )
        .group_by(Item.id, Warehouse.id, StorageLocation.id)
        .order_by(Item.code, Warehouse.code)
    )
    return [to_inventory_balance(row) for row in result.all()]


@router.get("/inventory/expiry", response_model=list[InventoryExpirySchema])
async def list_inventory_expiry(
    within_days: int | None = Query(default=None, alias="withinDays", ge=0, le=90),
    _: User = Depends(require_permission("inventory:read")),
    db: AsyncSession = Depends(get_db),
) -> list[InventoryExpirySchema]:
    today = date.today()
    horizon = today + timedelta(days=within_days if within_days is not None else 90)
    result = await db.execute(
        select(
            Item,
            Warehouse,
            StorageLocation,
            InventoryMovement.expiry_date,
            func.sum(InventoryMovement.quantity),
        )
        .join(Item, Item.id == InventoryMovement.item_id)
        .join(Warehouse, Warehouse.id == InventoryMovement.warehouse_id)
        .outerjoin(
            StorageLocation,
            StorageLocation.id == InventoryMovement.storage_location_id,
        )
        .where(
            InventoryMovement.expiry_date.is_not(None),
            InventoryMovement.expiry_date <= horizon,
        )
        .group_by(Item.id, Warehouse.id, StorageLocation.id, InventoryMovement.expiry_date)
        .order_by(InventoryMovement.expiry_date, Item.code)
    )
    rows = []
    for row in result.all():
        expiry_date = row[3]
        days_remaining = (expiry_date - today).days
        if days_remaining < 0:
            bucket = "expired"
        elif days_remaining <= 30:
            bucket = "within_30"
        elif days_remaining <= 60:
            bucket = "within_60"
        else:
            bucket = "within_90"
        rows.append(to_inventory_expiry(row, days_remaining, bucket))
    return rows


@router.post(
    "/inventory/opening-balances",
    response_model=InventoryMovementSchema,
    status_code=status.HTTP_201_CREATED,
)
async def create_opening_balance(
    payload: OpeningBalanceInput,
    _: User = Depends(require_permission("inventory:write")),
    db: AsyncSession = Depends(get_db),
) -> InventoryMovementSchema:
    item, location = await validate_destination(
        db, payload.item_id, payload.warehouse_id, payload.storage_location
    )
    serials = await validate_serials(
        db, item, payload.quantity, payload.expiry_date, payload.serial_numbers
    )
    movement = InventoryMovement(
        movement_type="opening",
        movement_date=payload.movement_date,
        item_id=item.id,
        warehouse_id=payload.warehouse_id,
        storage_location_id=location.id if location else None,
        quantity=payload.quantity,
        expiry_date=payload.expiry_date,
        notes=payload.notes.strip(),
    )
    db.add(movement)
    await db.flush()
    for serial_number in serials:
        db.add(
            InventorySerial(
                serial_number=serial_number,
                item_id=item.id,
                warehouse_id=payload.warehouse_id,
                storage_location_id=location.id if location else None,
                movement_id=movement.id,
                expiry_date=payload.expiry_date,
            )
        )
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise relation_error("تعذر حفظ الرصيد الافتتاحي؛ الرقم التسلسلي مستخدم مسبقًا")
    saved = await get_movement(db, movement.id)
    return to_inventory_movement(saved)