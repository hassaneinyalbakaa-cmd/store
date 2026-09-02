from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class HealthStatus(BaseModel):
    status: str


class ErrorResponse(BaseModel):
    detail: str


class MessageResponse(BaseModel):
    message: str


class LoginInput(BaseModel):
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)


class SessionUser(BaseModel):
    id: int
    username: str
    display_name: str
    role_id: int
    role_name: str
    permissions: list[str]
    is_active: bool


class User(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    display_name: str
    role_id: int
    role_name: str
    is_active: bool
    created_at: datetime


class UserInput(BaseModel):
    username: str = Field(min_length=3, max_length=80)
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(min_length=1, max_length=160)
    role_id: int
    is_active: bool = True


class UserUpdate(BaseModel):
    password: str | None = Field(default=None, min_length=8, max_length=128)
    display_name: str | None = Field(default=None, min_length=1, max_length=160)
    role_id: int | None = None
    is_active: bool | None = None


class Role(BaseModel):
    id: int
    name: str
    display_name: str
    description: str
    permissions: list[str]


class Permission(BaseModel):
    code: str
    display_name: str
    description: str


class DashboardSummary(BaseModel):
    users_total: int
    active_users: int
    roles_total: int
    permissions_total: int


class Warehouse(BaseModel):
    id: int
    name: str
    code: str
    description: str
    warehouse_type: str
    is_active: bool


class WarehouseInput(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    code: str = Field(min_length=1, max_length=40)
    description: str = Field(default="", max_length=255)
    warehouse_type: str = Field(default="branch", pattern="^(main|branch)$")
    is_active: bool = True


class WarehouseUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    code: str | None = Field(default=None, min_length=1, max_length=40)
    description: str | None = Field(default=None, max_length=255)
    warehouse_type: str | None = Field(default=None, pattern="^(main|branch)$")
    is_active: bool | None = None


class Department(BaseModel):
    id: int
    name: str
    code: str
    is_active: bool


class DepartmentInput(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    code: str = Field(min_length=1, max_length=40)
    is_active: bool = True


class DepartmentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    code: str | None = Field(default=None, min_length=1, max_length=40)
    is_active: bool | None = None


class StorageLocation(BaseModel):
    id: int
    warehouse_id: int
    area: str
    shelf: str
    bin: str


class StorageLocationInput(BaseModel):
    area: str = Field(min_length=1, max_length=80)
    shelf: str = Field(min_length=1, max_length=80)
    bin: str = Field(min_length=1, max_length=80)


class Item(BaseModel):
    id: int
    code: str
    name: str
    description: str
    category: str
    unit: str
    part_number: str | None
    minimum_level: float
    warehouse_id: int
    warehouse_name: str
    storage_location: StorageLocation | None
    requires_serial_number: bool
    requires_expiry_date: bool
    is_active: bool
    created_at: datetime


class ItemInput(BaseModel):
    code: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=160)
    description: str = Field(default="", max_length=255)
    category: str = Field(default="", max_length=120)
    unit: str = Field(min_length=1, max_length=60)
    part_number: str | None = Field(default=None, max_length=120)
    minimum_level: float = Field(default=0, ge=0)
    warehouse_id: int
    storage_location: StorageLocationInput | None = None
    requires_serial_number: bool = False
    requires_expiry_date: bool = False
    is_active: bool = True


class ItemUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=80)
    name: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=255)
    category: str | None = Field(default=None, max_length=120)
    unit: str | None = Field(default=None, min_length=1, max_length=60)
    part_number: str | None = Field(default=None, max_length=120)
    minimum_level: float | None = Field(default=None, ge=0)
    warehouse_id: int | None = None
    storage_location: StorageLocationInput | None = None
    requires_serial_number: bool | None = None
    requires_expiry_date: bool | None = None
    is_active: bool | None = None


class ReceiptDetail(BaseModel):
    id: int
    item_id: int
    item_code: str
    item_name: str
    quantity: float
    warehouse_id: int
    warehouse_name: str
    storage_location: StorageLocation | None
    expiry_date: date | None
    serial_numbers: list[str]


class Receipt(BaseModel):
    id: int
    receipt_number: str
    receipt_date: date
    supplier: str
    document_number: str
    notes: str
    details: list[ReceiptDetail]
    created_at: datetime


class ReceiptDetailInput(BaseModel):
    item_id: int
    quantity: float = Field(gt=0)
    warehouse_id: int
    storage_location: StorageLocationInput | None = None
    expiry_date: date | None = None
    serial_numbers: list[str] = Field(default_factory=list)


class ReceiptInput(BaseModel):
    receipt_date: date
    supplier: str = Field(min_length=1, max_length=160)
    document_number: str = Field(default="", max_length=80)
    notes: str = Field(default="", max_length=500)
    details: list[ReceiptDetailInput] = Field(min_length=1)


class InventoryMovement(BaseModel):
    id: int
    movement_type: str
    movement_date: date
    item_id: int
    item_code: str
    item_name: str
    warehouse_id: int
    warehouse_name: str
    storage_location: StorageLocation | None
    quantity: float
    expiry_date: date | None
    receipt_id: int | None
    receipt_number: str | None
    notes: str
    created_at: datetime


class InventoryBalance(BaseModel):
    item_id: int
    item_code: str
    item_name: str
    warehouse_id: int
    warehouse_name: str
    storage_location: StorageLocation | None
    quantity: float


class InventoryExpiry(BaseModel):
    item_id: int
    item_code: str
    item_name: str
    warehouse_id: int
    warehouse_name: str
    storage_location: StorageLocation | None
    expiry_date: date
    quantity: float
    days_remaining: int
    bucket: str


class OpeningBalanceInput(BaseModel):
    movement_date: date
    item_id: int
    quantity: float = Field(gt=0)
    warehouse_id: int
    storage_location: StorageLocationInput | None = None
    expiry_date: date | None = None
    serial_numbers: list[str] = Field(default_factory=list)
    notes: str = Field(default="", max_length=500)


class IssueRequest(BaseModel):
    id: int
    request_number: str
    department_id: int
    department_name: str
    request_date: date
    reason: str
    item_id: int
    item_code: str
    item_name: str
    item_unit: str
    warehouse_id: int
    warehouse_name: str
    quantity: float
    current_balance: float
    available_quantity: float
    notes: str
    status: str
    rejection_reason: str | None
    created_by_id: int
    created_by_name: str
    issue_voucher_id: int | None
    issue_number: str | None
    created_at: datetime


class IssueRequestInput(BaseModel):
    department_id: int
    request_date: date
    reason: str = Field(min_length=1, max_length=255)
    item_id: int
    quantity: float = Field(gt=0)
    notes: str = Field(default="", max_length=500)


class IssueRequestRejectionInput(BaseModel):
    rejection_reason: str = Field(min_length=1, max_length=500)


class IssueRequestIssueInput(BaseModel):
    serial_numbers: list[str] = Field(default_factory=list)


class IssueRequestPreview(BaseModel):
    request_id: int
    request_number: str
    item_id: int
    item_name: str
    item_unit: str
    warehouse_id: int
    warehouse_name: str
    requested_quantity: float
    current_balance: float
    available_quantity: float
    requires_serial_number: bool
    available_serial_numbers: list[str]


class IssueVoucher(BaseModel):
    id: int
    issue_number: str
    request_id: int
    request_number: str
    department_id: int
    department_name: str
    item_id: int
    item_code: str
    item_name: str
    item_unit: str
    warehouse_id: int
    warehouse_name: str
    quantity: float
    serial_numbers: list[str]
    issued_by_id: int
    issued_by_name: str
    issued_at: datetime


class StockTransfer(BaseModel):
    id: int
    transfer_number: str
    source_warehouse_id: int
    source_warehouse_name: str
    destination_warehouse_id: int
    destination_warehouse_name: str
    item_id: int
    item_code: str
    item_name: str
    item_unit: str
    quantity: float
    reason: str
    notes: str
    status: str
    serial_numbers: list[str]
    current_source_balance: float
    available_quantity: float
    created_by_id: int
    created_by_name: str
    sent_at: datetime | None
    received_by_id: int | None
    received_by_name: str | None
    received_at: datetime | None
    completed_by_id: int | None
    completed_by_name: str | None
    completed_at: datetime | None
    created_at: datetime


class StockTransferInput(BaseModel):
    source_warehouse_id: int
    destination_warehouse_id: int
    item_id: int
    quantity: float = Field(gt=0)
    reason: str = Field(min_length=1, max_length=255)
    notes: str = Field(default="", max_length=500)


class StockTransferReceiveInput(BaseModel):
    serial_numbers: list[str] = Field(default_factory=list)


class StockTransferPreview(BaseModel):
    transfer_id: int
    transfer_number: str
    source_warehouse_id: int
    source_warehouse_name: str
    destination_warehouse_id: int
    destination_warehouse_name: str
    item_id: int
    item_code: str
    item_name: str
    item_unit: str
    quantity: float
    current_source_balance: float
    available_quantity: float
    requires_serial_number: bool
    available_serial_numbers: list[str]


class StocktakeLine(BaseModel):
    id: int
    stocktake_id: int
    item_id: int
    item_code: str
    item_name: str
    item_unit: str
    warehouse_id: int
    warehouse_name: str
    system_quantity: float
    actual_quantity: float | None
    difference: float | None
    adjustment_movement_id: int | None


class Stocktake(BaseModel):
    id: int
    stocktake_number: str
    stocktake_type: str
    warehouse_id: int
    warehouse_name: str
    stocktake_date: date
    status: str
    notes: str
    lines: list[StocktakeLine]
    created_by_id: int
    created_by_name: str
    completed_by_id: int | None
    completed_by_name: str | None
    completed_at: datetime | None
    created_at: datetime


class StocktakeInput(BaseModel):
    stocktake_type: str = Field(pattern="^(full|partial)$")
    warehouse_id: int
    stocktake_date: date
    item_ids: list[int] = Field(default_factory=list)
    notes: str = Field(default="", max_length=500)


class StocktakeCountInput(BaseModel):
    actual_quantity: float = Field(ge=0)


class StocktakeAdjustment(BaseModel):
    movement_id: int
    stocktake_id: int
    stocktake_number: str
    stocktake_line_id: int
    item_id: int
    item_code: str
    item_name: str
    warehouse_id: int
    warehouse_name: str
    quantity: float
    movement_date: date
    created_at: datetime


class ReportColumn(BaseModel):
    key: str
    label: str


class ReportResponse(BaseModel):
    report_type: str
    title: str
    columns: list[ReportColumn]
    rows: list[dict[str, object]]
    generated_at: datetime
    row_count: int


class AuditLog(BaseModel):
    id: int
    user_id: int | None
    username: str
    user_name: str
    action: str
    action_label: str
    document_number: str | None
    details: str
    created_at: datetime


class BackupInfo(BaseModel):
    id: int
    filename: str
    size_bytes: int
    created_by_id: int
    created_by_name: str
    created_at: datetime
    download_url: str
