from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..db import get_db
from ..audit import add_audit_log
from ..dependencies import require_permission
from ..models import (
    InventoryMovement,
    InventorySerial,
    Item,
    Stocktake,
    StocktakeLine,
    User,
    Warehouse,
)
from ..schemas import (
    Stocktake as StocktakeSchema,
    StocktakeAdjustment as StocktakeAdjustmentSchema,
    StocktakeCountInput,
    StocktakeInput,
    StocktakeLine as StocktakeLineSchema,
)
from ..serializers import (
    to_stocktake,
    to_stocktake_adjustment,
    to_stocktake_line,
)

router = APIRouter(tags=["stocktakes"])


def stocktake_error(message: str) -> HTTPException:
    return HTTPException(status_code=400, detail=message)


async def stocktake_adjustment_ids(
    db: AsyncSession, stocktake_id: int
) -> dict[int, int]:
    result = await db.execute(
        select(InventoryMovement.stocktake_line_id, InventoryMovement.id)
        .join(
            StocktakeLine,
            StocktakeLine.id == InventoryMovement.stocktake_line_id,
        )
        .where(
            StocktakeLine.stocktake_id == stocktake_id,
            InventoryMovement.stocktake_line_id.is_not(None),
        )
    )
    return {line_id: movement_id for line_id, movement_id in result.all()}


async def load_stocktake(
    db: AsyncSession, stocktake_id: int
) -> Stocktake | None:
    result = await db.execute(
        select(Stocktake)
        .options(
            selectinload(Stocktake.warehouse),
            selectinload(Stocktake.created_by),
            selectinload(Stocktake.completed_by),
            selectinload(Stocktake.lines).selectinload(StocktakeLine.item),
            selectinload(Stocktake.lines).selectinload(StocktakeLine.warehouse),
        )
        .where(Stocktake.id == stocktake_id)
    )
    return result.scalar_one_or_none()


async def require_stocktake(db: AsyncSession, stocktake_id: int) -> Stocktake:
    stocktake = await load_stocktake(db, stocktake_id)
    if stocktake is None:
        raise HTTPException(status_code=404, detail="عملية الجرد غير موجودة")
    return stocktake


async def item_balance(
    db: AsyncSession, item_id: int, warehouse_id: int
) -> float:
    result = await db.scalar(
        select(func.coalesce(func.sum(InventoryMovement.quantity), 0)).where(
            InventoryMovement.item_id == item_id,
            InventoryMovement.warehouse_id == warehouse_id,
        )
    )
    return float(result or 0)


async def serialize_stocktake(
    db: AsyncSession, stocktake: Stocktake
) -> StocktakeSchema:
    return to_stocktake(
        stocktake, await stocktake_adjustment_ids(db, stocktake.id)
    )


@router.get("/stocktakes", response_model=list[StocktakeSchema])
async def list_stocktakes(
    _: User = Depends(require_permission("stocktakes:read")),
    db: AsyncSession = Depends(get_db),
) -> list[StocktakeSchema]:
    result = await db.execute(
        select(Stocktake)
        .options(
            selectinload(Stocktake.warehouse),
            selectinload(Stocktake.created_by),
            selectinload(Stocktake.completed_by),
            selectinload(Stocktake.lines).selectinload(StocktakeLine.item),
            selectinload(Stocktake.lines).selectinload(StocktakeLine.warehouse),
        )
        .order_by(Stocktake.id.desc())
    )
    return [
        await serialize_stocktake(db, stocktake)
        for stocktake in result.scalars().all()
    ]


@router.post(
    "/stocktakes",
    response_model=StocktakeSchema,
    status_code=status.HTTP_201_CREATED,
)
async def create_stocktake(
    payload: StocktakeInput,
    user: User = Depends(require_permission("stocktakes:write")),
    db: AsyncSession = Depends(get_db),
) -> StocktakeSchema:
    warehouse = await db.get(Warehouse, payload.warehouse_id)
    if warehouse is None or not warehouse.is_active:
        raise stocktake_error("المخزن غير موجود أو معطل")

    if payload.stocktake_type == "partial":
        item_ids = list(dict.fromkeys(payload.item_ids))
        if not item_ids:
            raise stocktake_error("الجرد الجزئي يحتاج إلى صنف واحد على الأقل")
        item_result = await db.execute(
            select(Item).where(Item.id.in_(item_ids), Item.is_active.is_(True))
        )
        items_by_id = {item.id: item for item in item_result.scalars().all()}
        if len(items_by_id) != len(item_ids):
            raise stocktake_error("يوجد صنف غير موجود أو معطل في قائمة الجرد")
        items = [items_by_id[item_id] for item_id in item_ids]
    else:
        item_result = await db.execute(
            select(Item)
            .where(Item.is_active.is_(True))
            .order_by(Item.name, Item.id)
        )
        items = list(item_result.scalars().all())

    stocktake = Stocktake(
        stocktake_number="PENDING",
        stocktake_type=payload.stocktake_type,
        warehouse_id=warehouse.id,
        stocktake_date=payload.stocktake_date,
        status="draft",
        notes=payload.notes.strip(),
        created_by_id=user.id,
    )
    db.add(stocktake)
    await db.flush()
    stocktake.stocktake_number = (
        f"STK-{datetime.now(timezone.utc).year}-{stocktake.id:06d}"
    )
    for item in items:
        db.add(
            StocktakeLine(
                stocktake_id=stocktake.id,
                item_id=item.id,
                warehouse_id=warehouse.id,
                system_quantity=await item_balance(db, item.id, warehouse.id),
            )
        )
    await db.commit()
    saved = await load_stocktake(db, stocktake.id)
    return await serialize_stocktake(db, saved)


@router.get("/stocktakes/{stocktakeId}", response_model=StocktakeSchema)
async def get_stocktake(
    stocktakeId: int,
    _: User = Depends(require_permission("stocktakes:read")),
    db: AsyncSession = Depends(get_db),
) -> StocktakeSchema:
    stocktake = await require_stocktake(db, stocktakeId)
    return await serialize_stocktake(db, stocktake)


@router.post(
    "/stocktakes/{stocktakeId}/lines/{lineId}/count",
    response_model=StocktakeLineSchema,
)
async def count_stocktake_line(
    stocktakeId: int,
    lineId: int,
    payload: StocktakeCountInput,
    _: User = Depends(require_permission("stocktakes:write")),
    db: AsyncSession = Depends(get_db),
) -> StocktakeLineSchema:
    result = await db.execute(
        select(StocktakeLine)
        .options(
            selectinload(StocktakeLine.item),
            selectinload(StocktakeLine.warehouse),
        )
        .where(
            StocktakeLine.id == lineId,
            StocktakeLine.stocktake_id == stocktakeId,
        )
    )
    line = result.scalar_one_or_none()
    if line is None:
        raise HTTPException(status_code=404, detail="سطر الجرد غير موجود")
    stocktake = await require_stocktake(db, stocktakeId)
    if stocktake.status != "draft":
        raise stocktake_error("لا يمكن تعديل جرد مكتمل")
    line.actual_quantity = payload.actual_quantity
    line.difference = payload.actual_quantity - line.system_quantity
    await db.commit()
    adjustment_ids = await stocktake_adjustment_ids(db, stocktakeId)
    return to_stocktake_line(line, adjustment_ids.get(line.id))


@router.post("/stocktakes/{stocktakeId}/complete", response_model=StocktakeSchema)
async def complete_stocktake(
    stocktakeId: int,
    user: User = Depends(require_permission("stocktakes:write")),
    db: AsyncSession = Depends(get_db),
) -> StocktakeSchema:
    stocktake = await require_stocktake(db, stocktakeId)
    if stocktake.status != "draft":
        raise stocktake_error("عملية الجرد مكتملة مسبقًا")
    if any(line.actual_quantity is None for line in stocktake.lines):
        raise stocktake_error("يجب إدخال العد الفعلي لكل سطور الجرد")

    for line in stocktake.lines:
        line.difference = line.actual_quantity - line.system_quantity
        if not line.difference:
            continue
        if line.item.requires_serial_number:
            raise stocktake_error(
                f"لا يمكن تسوية صنف رقميًا بالتسويات الكمية فقط: {line.item.name}. "
                "أدخل أرقامًا تسلسلية أو اترك الفرق صفرًا."
            )
        db.add(
            InventoryMovement(
                movement_type="adjustment",
                movement_date=stocktake.stocktake_date,
                item_id=line.item_id,
                warehouse_id=line.warehouse_id,
                quantity=line.difference,
                stocktake_line_id=line.id,
                notes=f"تسوية مرتبطة بالجرد {stocktake.stocktake_number}",
            )
        )
        add_audit_log(
            db,
            user=user,
            action="adjustment",
            document_number=stocktake.stocktake_number,
            details=f"الصنف: {line.item.name}، الفرق: {line.difference:g}",
        )
    stocktake.status = "completed"
    stocktake.completed_by_id = user.id
    stocktake.completed_at = datetime.now(timezone.utc)
    add_audit_log(
        db,
        user=user,
        action="stocktake",
        document_number=stocktake.stocktake_number,
        details=f"عدد البنود: {len(stocktake.lines)}",
    )
    await db.commit()
    saved = await load_stocktake(db, stocktake.id)
    return await serialize_stocktake(db, saved)


@router.get(
    "/stocktake-adjustments",
    response_model=list[StocktakeAdjustmentSchema],
)
async def list_stocktake_adjustments(
    _: User = Depends(require_permission("stocktakes:read")),
    db: AsyncSession = Depends(get_db),
) -> list[StocktakeAdjustmentSchema]:
    result = await db.execute(
        select(InventoryMovement, Stocktake, StocktakeLine)
        .join(
            StocktakeLine,
            StocktakeLine.id == InventoryMovement.stocktake_line_id,
        )
        .join(Stocktake, Stocktake.id == StocktakeLine.stocktake_id)
        .options(
            selectinload(InventoryMovement.item),
            selectinload(InventoryMovement.warehouse),
        )
        .where(InventoryMovement.movement_type == "adjustment")
        .order_by(InventoryMovement.id.desc())
    )
    return [to_stocktake_adjustment(row) for row in result.all()]