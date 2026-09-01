from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..db import get_db
from ..dependencies import require_permission
from ..models import Department, Item, StorageLocation, User, Warehouse
from ..schemas import (
    Department as DepartmentSchema,
    DepartmentInput,
    DepartmentUpdate,
    Item as ItemSchema,
    ItemInput,
    ItemUpdate,
    StorageLocationInput,
    Warehouse as WarehouseSchema,
    WarehouseInput,
    WarehouseUpdate,
)
from ..serializers import to_department, to_item, to_warehouse

router = APIRouter(tags=["warehouses", "departments", "items"])


async def get_warehouse(db: AsyncSession, warehouse_id: int) -> Warehouse | None:
    return await db.get(Warehouse, warehouse_id)


async def get_department(db: AsyncSession, department_id: int) -> Department | None:
    return await db.get(Department, department_id)


async def get_item(db: AsyncSession, item_id: int) -> Item | None:
    result = await db.execute(
        select(Item)
        .options(selectinload(Item.warehouse), selectinload(Item.storage_location))
        .where(Item.id == item_id)
    )
    return result.scalar_one_or_none()


async def require_warehouse(db: AsyncSession, warehouse_id: int) -> Warehouse:
    warehouse = await get_warehouse(db, warehouse_id)
    if warehouse is None:
        raise HTTPException(status_code=400, detail="المخزن المحدد غير موجود")
    return warehouse


async def resolve_location(
    db: AsyncSession,
    warehouse_id: int,
    payload: StorageLocationInput,
) -> StorageLocation:
    values = {
        "area": payload.area.strip(),
        "shelf": payload.shelf.strip(),
        "bin": payload.bin.strip(),
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
    if location is not None:
        return location
    location = StorageLocation(warehouse_id=warehouse_id, **values)
    db.add(location)
    await db.flush()
    return location


@router.get("/warehouses", response_model=list[WarehouseSchema])
async def list_warehouses(
    _: User = Depends(require_permission("warehouses:read")),
    db: AsyncSession = Depends(get_db),
) -> list[WarehouseSchema]:
    result = await db.execute(select(Warehouse).order_by(Warehouse.id))
    return [to_warehouse(warehouse) for warehouse in result.scalars().all()]


@router.post(
    "/warehouses",
    response_model=WarehouseSchema,
    status_code=status.HTTP_201_CREATED,
)
async def create_warehouse(
    payload: WarehouseInput,
    _: User = Depends(require_permission("warehouses:write")),
    db: AsyncSession = Depends(get_db),
) -> WarehouseSchema:
    warehouse = Warehouse(
        name=payload.name.strip(),
        code=payload.code.strip().upper(),
        description=payload.description.strip(),
        warehouse_type=payload.warehouse_type,
        is_active=payload.is_active,
    )
    db.add(warehouse)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=400, detail="رمز المخزن مستخدم مسبقًا")
    return to_warehouse(warehouse)


@router.patch("/warehouses/{warehouse_id}", response_model=WarehouseSchema)
async def update_warehouse(
    warehouse_id: int,
    payload: WarehouseUpdate,
    _: User = Depends(require_permission("warehouses:write")),
    db: AsyncSession = Depends(get_db),
) -> WarehouseSchema:
    warehouse = await get_warehouse(db, warehouse_id)
    if warehouse is None:
        raise HTTPException(status_code=404, detail="المخزن غير موجود")
    if payload.name is not None:
        warehouse.name = payload.name.strip()
    if payload.code is not None:
        warehouse.code = payload.code.strip().upper()
    if payload.description is not None:
        warehouse.description = payload.description.strip()
    if payload.warehouse_type is not None:
        warehouse.warehouse_type = payload.warehouse_type
    if payload.is_active is not None:
        warehouse.is_active = payload.is_active
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=400, detail="رمز المخزن مستخدم مسبقًا")
    return to_warehouse(warehouse)


@router.get("/departments", response_model=list[DepartmentSchema])
async def list_departments(
    _: User = Depends(require_permission("departments:read")),
    db: AsyncSession = Depends(get_db),
) -> list[DepartmentSchema]:
    result = await db.execute(select(Department).order_by(Department.id))
    return [to_department(department) for department in result.scalars().all()]


@router.post(
    "/departments",
    response_model=DepartmentSchema,
    status_code=status.HTTP_201_CREATED,
)
async def create_department(
    payload: DepartmentInput,
    _: User = Depends(require_permission("departments:write")),
    db: AsyncSession = Depends(get_db),
) -> DepartmentSchema:
    department = Department(
        name=payload.name.strip(),
        code=payload.code.strip().upper(),
        is_active=payload.is_active,
    )
    db.add(department)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=400, detail="رمز القسم مستخدم مسبقًا")
    return to_department(department)


@router.patch("/departments/{department_id}", response_model=DepartmentSchema)
async def update_department(
    department_id: int,
    payload: DepartmentUpdate,
    _: User = Depends(require_permission("departments:write")),
    db: AsyncSession = Depends(get_db),
) -> DepartmentSchema:
    department = await get_department(db, department_id)
    if department is None:
        raise HTTPException(status_code=404, detail="القسم غير موجود")
    if payload.name is not None:
        department.name = payload.name.strip()
    if payload.code is not None:
        department.code = payload.code.strip().upper()
    if payload.is_active is not None:
        department.is_active = payload.is_active
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=400, detail="رمز القسم مستخدم مسبقًا")
    return to_department(department)


@router.get("/items", response_model=list[ItemSchema])
async def list_items(
    search: str | None = Query(default=None),
    warehouse_id: int | None = Query(default=None, alias="warehouseId"),
    is_active: bool | None = Query(default=None, alias="isActive"),
    _: User = Depends(require_permission("items:read")),
    db: AsyncSession = Depends(get_db),
) -> list[ItemSchema]:
    query = (
        select(Item)
        .options(selectinload(Item.warehouse), selectinload(Item.storage_location))
        .order_by(Item.id)
    )
    if search and search.strip():
        needle = f"%{search.strip()}%"
        query = query.where(
            or_(
                Item.code.ilike(needle),
                Item.name.ilike(needle),
                Item.category.ilike(needle),
                Item.part_number.ilike(needle),
            )
        )
    if warehouse_id is not None:
        query = query.where(Item.warehouse_id == warehouse_id)
    if is_active is not None:
        query = query.where(Item.is_active == is_active)
    result = await db.execute(query)
    return [to_item(item) for item in result.scalars().all()]


@router.post("/items", response_model=ItemSchema, status_code=status.HTTP_201_CREATED)
async def create_item(
    payload: ItemInput,
    _: User = Depends(require_permission("items:write")),
    db: AsyncSession = Depends(get_db),
) -> ItemSchema:
    await require_warehouse(db, payload.warehouse_id)
    location = (
        await resolve_location(db, payload.warehouse_id, payload.storage_location)
        if payload.storage_location is not None
        else None
    )
    item = Item(
        code=payload.code.strip().upper(),
        name=payload.name.strip(),
        description=payload.description.strip(),
        category=payload.category.strip(),
        unit=payload.unit.strip(),
        part_number=payload.part_number.strip() if payload.part_number else None,
        minimum_level=payload.minimum_level,
        warehouse_id=payload.warehouse_id,
        storage_location_id=location.id if location else None,
        requires_serial_number=payload.requires_serial_number,
        requires_expiry_date=payload.requires_expiry_date,
        is_active=payload.is_active,
    )
    db.add(item)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=400, detail="كود الصنف مستخدم مسبقًا أو موقع التخزين مكرر")
    saved = await get_item(db, item.id)
    return to_item(saved)


@router.patch("/items/{item_id}", response_model=ItemSchema)
async def update_item(
    item_id: int,
    payload: ItemUpdate,
    _: User = Depends(require_permission("items:write")),
    db: AsyncSession = Depends(get_db),
) -> ItemSchema:
    item = await get_item(db, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="الصنف غير موجود")

    new_warehouse_id = payload.warehouse_id or item.warehouse_id
    await require_warehouse(db, new_warehouse_id)
    if payload.code is not None:
        item.code = payload.code.strip().upper()
    if payload.name is not None:
        item.name = payload.name.strip()
    if payload.description is not None:
        item.description = payload.description.strip()
    if payload.category is not None:
        item.category = payload.category.strip()
    if payload.unit is not None:
        item.unit = payload.unit.strip()
    if "part_number" in payload.model_fields_set:
        item.part_number = payload.part_number.strip() if payload.part_number else None
    if payload.minimum_level is not None:
        item.minimum_level = payload.minimum_level
    if payload.requires_serial_number is not None:
        item.requires_serial_number = payload.requires_serial_number
    if payload.requires_expiry_date is not None:
        item.requires_expiry_date = payload.requires_expiry_date
    if payload.is_active is not None:
        item.is_active = payload.is_active
    if payload.warehouse_id is not None:
        item.warehouse_id = new_warehouse_id

    if "storage_location" in payload.model_fields_set:
        if payload.storage_location is None:
            item.storage_location_id = None
        else:
            location = await resolve_location(
                db, new_warehouse_id, payload.storage_location
            )
            item.storage_location_id = location.id
    elif payload.warehouse_id is not None and item.storage_location is not None:
        item.storage_location_id = None

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=400, detail="كود الصنف مستخدم مسبقًا أو موقع التخزين مكرر")
    saved = await get_item(db, item.id)
    return to_item(saved)