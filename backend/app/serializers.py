from .models import (
    Department,
    IssueRequest,
    IssueVoucher,
    InventoryMovement,
    Item,
    Receipt,
    ReceiptDetail,
    Role,
    StorageLocation,
    User,
    Warehouse,
)
from .schemas import Role as RoleSchema
from .schemas import (
    Department as DepartmentSchema,
    Item as ItemSchema,
    InventoryBalance as InventoryBalanceSchema,
    InventoryExpiry as InventoryExpirySchema,
    InventoryMovement as InventoryMovementSchema,
    IssueRequest as IssueRequestSchema,
    IssueRequestPreview as IssueRequestPreviewSchema,
    IssueVoucher as IssueVoucherSchema,
    Receipt as ReceiptSchema,
    ReceiptDetail as ReceiptDetailSchema,
    SessionUser,
    StorageLocation as StorageLocationSchema,
    User as UserSchema,
    Warehouse as WarehouseSchema,
)


def to_session_user(user: User) -> SessionUser:
    return SessionUser(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
        role_id=user.role_id,
        role_name=user.role.display_name,
        permissions=sorted(permission.code for permission in user.role.permissions),
        is_active=user.is_active,
    )


def to_user(user: User) -> UserSchema:
    return UserSchema(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
        role_id=user.role_id,
        role_name=user.role.display_name,
        is_active=user.is_active,
        created_at=user.created_at,
    )


def to_role(role: Role) -> RoleSchema:
    return RoleSchema(
        id=role.id,
        name=role.name,
        display_name=role.display_name,
        description=role.description,
        permissions=sorted(permission.code for permission in role.permissions),
    )


def to_warehouse(warehouse: Warehouse) -> WarehouseSchema:
    return WarehouseSchema(
        id=warehouse.id,
        name=warehouse.name,
        code=warehouse.code,
        description=warehouse.description,
        warehouse_type=warehouse.warehouse_type,
        is_active=warehouse.is_active,
    )


def to_department(department: Department) -> DepartmentSchema:
    return DepartmentSchema(
        id=department.id,
        name=department.name,
        code=department.code,
        is_active=department.is_active,
    )


def to_storage_location(location: StorageLocation | None) -> StorageLocationSchema | None:
    if location is None:
        return None
    return StorageLocationSchema(
        id=location.id,
        warehouse_id=location.warehouse_id,
        area=location.area,
        shelf=location.shelf,
        bin=location.bin,
    )


def to_item(item: Item) -> ItemSchema:
    return ItemSchema(
        id=item.id,
        code=item.code,
        name=item.name,
        description=item.description,
        category=item.category,
        unit=item.unit,
        part_number=item.part_number,
        minimum_level=item.minimum_level,
        warehouse_id=item.warehouse_id,
        warehouse_name=item.warehouse.name,
        storage_location=to_storage_location(item.storage_location),
        requires_serial_number=item.requires_serial_number,
        requires_expiry_date=item.requires_expiry_date,
        is_active=item.is_active,
        created_at=item.created_at,
    )


def to_receipt_detail(detail: ReceiptDetail) -> ReceiptDetailSchema:
    return ReceiptDetailSchema(
        id=detail.id,
        item_id=detail.item_id,
        item_code=detail.item.code,
        item_name=detail.item.name,
        quantity=detail.quantity,
        warehouse_id=detail.warehouse_id,
        warehouse_name=detail.warehouse.name,
        storage_location=to_storage_location(detail.storage_location),
        expiry_date=detail.expiry_date,
        serial_numbers=[serial.serial_number for serial in detail.serials],
    )


def to_receipt(receipt: Receipt) -> ReceiptSchema:
    return ReceiptSchema(
        id=receipt.id,
        receipt_number=receipt.receipt_number,
        receipt_date=receipt.receipt_date,
        supplier=receipt.supplier,
        document_number=receipt.document_number,
        notes=receipt.notes,
        details=[to_receipt_detail(detail) for detail in receipt.details],
        created_at=receipt.created_at,
    )


def to_inventory_movement(movement: InventoryMovement) -> InventoryMovementSchema:
    receipt = movement.receipt_detail.receipt if movement.receipt_detail else None
    return InventoryMovementSchema(
        id=movement.id,
        movement_type=movement.movement_type,
        movement_date=movement.movement_date,
        item_id=movement.item_id,
        item_code=movement.item.code,
        item_name=movement.item.name,
        warehouse_id=movement.warehouse_id,
        warehouse_name=movement.warehouse.name,
        storage_location=to_storage_location(movement.storage_location),
        quantity=movement.quantity,
        expiry_date=movement.expiry_date,
        receipt_id=receipt.id if receipt else None,
        receipt_number=receipt.receipt_number if receipt else None,
        notes=movement.notes,
        created_at=movement.created_at,
    )


def to_inventory_balance(row: tuple) -> InventoryBalanceSchema:
    item, warehouse, location, quantity = row
    return InventoryBalanceSchema(
        item_id=item.id,
        item_code=item.code,
        item_name=item.name,
        warehouse_id=warehouse.id,
        warehouse_name=warehouse.name,
        storage_location=to_storage_location(location),
        quantity=quantity,
    )


def to_inventory_expiry(row: tuple, days_remaining: int, bucket: str) -> InventoryExpirySchema:
    item, warehouse, location, expiry_date, quantity = row
    return InventoryExpirySchema(
        item_id=item.id,
        item_code=item.code,
        item_name=item.name,
        warehouse_id=warehouse.id,
        warehouse_name=warehouse.name,
        storage_location=to_storage_location(location),
        expiry_date=expiry_date,
        quantity=quantity,
        days_remaining=days_remaining,
        bucket=bucket,
    )


def to_issue_request(
    request: IssueRequest,
    current_balance: float,
    available_quantity: float,
) -> IssueRequestSchema:
    voucher = request.issue_voucher
    return IssueRequestSchema(
        id=request.id,
        request_number=request.request_number,
        department_id=request.department_id,
        department_name=request.department.name,
        request_date=request.request_date,
        reason=request.reason,
        item_id=request.item_id,
        item_code=request.item.code,
        item_name=request.item.name,
        item_unit=request.item.unit,
        warehouse_id=request.item.warehouse_id,
        warehouse_name=request.item.warehouse.name,
        quantity=request.quantity,
        current_balance=current_balance,
        available_quantity=available_quantity,
        notes=request.notes,
        status=request.status,
        rejection_reason=request.rejection_reason,
        created_by_id=request.created_by_id,
        created_by_name=request.created_by.display_name,
        issue_voucher_id=voucher.id if voucher else None,
        issue_number=voucher.issue_number if voucher else None,
        created_at=request.created_at,
    )


def to_issue_request_preview(
    request: IssueRequest,
    current_balance: float,
    available_quantity: float,
    available_serial_numbers: list[str],
) -> IssueRequestPreviewSchema:
    return IssueRequestPreviewSchema(
        request_id=request.id,
        request_number=request.request_number,
        item_id=request.item_id,
        item_name=request.item.name,
        item_unit=request.item.unit,
        warehouse_id=request.item.warehouse_id,
        warehouse_name=request.item.warehouse.name,
        requested_quantity=request.quantity,
        current_balance=current_balance,
        available_quantity=available_quantity,
        requires_serial_number=request.item.requires_serial_number,
        available_serial_numbers=available_serial_numbers,
    )


def to_issue_voucher(voucher: IssueVoucher) -> IssueVoucherSchema:
    request = voucher.request
    return IssueVoucherSchema(
        id=voucher.id,
        issue_number=voucher.issue_number,
        request_id=voucher.request_id,
        request_number=request.request_number,
        department_id=request.department_id,
        department_name=request.department.name,
        item_id=voucher.item_id,
        item_code=voucher.item.code,
        item_name=voucher.item.name,
        item_unit=voucher.item.unit,
        warehouse_id=voucher.warehouse_id,
        warehouse_name=voucher.warehouse.name,
        quantity=voucher.quantity,
        serial_numbers=[serial.serial_number for serial in voucher.serials],
        issued_by_id=voucher.issued_by_id,
        issued_by_name=voucher.issued_by.display_name,
        issued_at=voucher.issued_at,
    )
