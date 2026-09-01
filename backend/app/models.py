from datetime import date, datetime
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, String, Table, Column, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column("role_id", ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    Column(
        "permission_id",
        ForeignKey("permissions.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(60), unique=True)
    display_name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(String(255), default="")
    users: Mapped[list["User"]] = relationship(back_populates="role")
    permissions: Mapped[list["Permission"]] = relationship(
        secondary=role_permissions,
        back_populates="roles",
        lazy="selectin",
    )


class Permission(Base):
    __tablename__ = "permissions"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(80), unique=True)
    display_name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(String(255), default="")
    roles: Mapped[list[Role]] = relationship(
        secondary=role_permissions,
        back_populates="permissions",
    )


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True)
    display_name: Mapped[str] = mapped_column(String(160))
    password_hash: Mapped[str] = mapped_column(String(255))
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id"), index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    role: Mapped[Role] = relationship(back_populates="users", lazy="selectin")
    sessions: Mapped[list["UserSession"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class UserSession(Base):
    __tablename__ = "user_sessions"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    user: Mapped[User] = relationship(back_populates="sessions")


class Warehouse(Base):
    __tablename__ = "warehouses"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    code: Mapped[str] = mapped_column(String(40), unique=True)
    description: Mapped[str] = mapped_column(String(255), default="")
    warehouse_type: Mapped[str] = mapped_column(String(20), default="branch", server_default="branch")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    locations: Mapped[list["StorageLocation"]] = relationship(
        back_populates="warehouse", cascade="all, delete-orphan"
    )
    items: Mapped[list["Item"]] = relationship(back_populates="warehouse")


class Department(Base):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    code: Mapped[str] = mapped_column(String(40), unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")


class StorageLocation(Base):
    __tablename__ = "storage_locations"
    __table_args__ = (
        UniqueConstraint("warehouse_id", "area", "shelf", "bin", name="uq_storage_location_coordinates"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    warehouse_id: Mapped[int] = mapped_column(
        ForeignKey("warehouses.id", ondelete="CASCADE"), index=True
    )
    area: Mapped[str] = mapped_column(String(80))
    shelf: Mapped[str] = mapped_column(String(80))
    bin: Mapped[str] = mapped_column(String(80))
    warehouse: Mapped[Warehouse] = relationship(back_populates="locations")
    items: Mapped[list["Item"]] = relationship(back_populates="storage_location")


class Item(Base):
    __tablename__ = "items"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(80), unique=True)
    name: Mapped[str] = mapped_column(String(160))
    description: Mapped[str] = mapped_column(String(255), default="")
    category: Mapped[str] = mapped_column(String(120), default="")
    unit: Mapped[str] = mapped_column(String(60))
    part_number: Mapped[str | None] = mapped_column(String(120), nullable=True)
    minimum_level: Mapped[float] = mapped_column(Float, default=0, server_default="0")
    warehouse_id: Mapped[int] = mapped_column(
        ForeignKey("warehouses.id"), index=True
    )
    storage_location_id: Mapped[int | None] = mapped_column(
        ForeignKey("storage_locations.id"), nullable=True, index=True
    )
    requires_serial_number: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )
    requires_expiry_date: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    warehouse: Mapped[Warehouse] = relationship(back_populates="items", lazy="selectin")
    storage_location: Mapped[StorageLocation | None] = relationship(
        back_populates="items", lazy="selectin"
    )


class Receipt(Base):
    __tablename__ = "receipts"

    id: Mapped[int] = mapped_column(primary_key=True)
    receipt_number: Mapped[str] = mapped_column(String(40), unique=True)
    receipt_date: Mapped[date] = mapped_column(Date, nullable=False)
    supplier: Mapped[str] = mapped_column(String(160))
    document_number: Mapped[str] = mapped_column(String(80), default="")
    notes: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    details: Mapped[list["ReceiptDetail"]] = relationship(
        back_populates="receipt", cascade="all, delete-orphan", lazy="selectin"
    )


class ReceiptDetail(Base):
    __tablename__ = "receipt_details"

    id: Mapped[int] = mapped_column(primary_key=True)
    receipt_id: Mapped[int] = mapped_column(
        ForeignKey("receipts.id", ondelete="CASCADE"), index=True
    )
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id"), index=True)
    warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id"), index=True)
    storage_location_id: Mapped[int | None] = mapped_column(
        ForeignKey("storage_locations.id"), nullable=True, index=True
    )
    quantity: Mapped[float] = mapped_column(Float)
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    receipt: Mapped[Receipt] = relationship(back_populates="details")
    item: Mapped[Item] = relationship(lazy="selectin")
    warehouse: Mapped[Warehouse] = relationship(lazy="selectin")
    storage_location: Mapped[StorageLocation | None] = relationship(lazy="selectin")
    serials: Mapped[list["InventorySerial"]] = relationship(
        back_populates="receipt_detail", cascade="all, delete-orphan", lazy="selectin"
    )
    movement: Mapped["InventoryMovement"] = relationship(
        back_populates="receipt_detail", uselist=False, cascade="all, delete-orphan"
    )


class InventoryMovement(Base):
    __tablename__ = "inventory_movements"

    id: Mapped[int] = mapped_column(primary_key=True)
    movement_type: Mapped[str] = mapped_column(String(20), index=True)
    movement_date: Mapped[date] = mapped_column(Date, nullable=False)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id"), index=True)
    warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id"), index=True)
    storage_location_id: Mapped[int | None] = mapped_column(
        ForeignKey("storage_locations.id"), nullable=True, index=True
    )
    quantity: Mapped[float] = mapped_column(Float)
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    receipt_detail_id: Mapped[int | None] = mapped_column(
        ForeignKey("receipt_details.id"), nullable=True, unique=True
    )
    issue_voucher_id: Mapped[int | None] = mapped_column(
        ForeignKey("issue_vouchers.id"), nullable=True, unique=True
    )
    transfer_id: Mapped[int | None] = mapped_column(
        ForeignKey("stock_transfers.id"), nullable=True, index=True
    )
    stocktake_line_id: Mapped[int | None] = mapped_column(
        ForeignKey("stocktake_lines.id"), nullable=True, unique=True, index=True
    )
    notes: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    item: Mapped[Item] = relationship(lazy="selectin")
    warehouse: Mapped[Warehouse] = relationship(lazy="selectin")
    storage_location: Mapped[StorageLocation | None] = relationship(lazy="selectin")
    receipt_detail: Mapped[ReceiptDetail | None] = relationship(back_populates="movement")
    issue_voucher: Mapped["IssueVoucher | None"] = relationship(
        back_populates="movement"
    )
    transfer: Mapped["StockTransfer | None"] = relationship(
        back_populates="movements"
    )
    serials: Mapped[list["InventorySerial"]] = relationship(
        back_populates="movement", cascade="all, delete-orphan", lazy="selectin"
    )


class InventorySerial(Base):
    __tablename__ = "inventory_serials"

    id: Mapped[int] = mapped_column(primary_key=True)
    serial_number: Mapped[str] = mapped_column(String(160), unique=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id"), index=True)
    warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id"), index=True)
    storage_location_id: Mapped[int | None] = mapped_column(
        ForeignKey("storage_locations.id"), nullable=True, index=True
    )
    movement_id: Mapped[int] = mapped_column(
        ForeignKey("inventory_movements.id", ondelete="CASCADE"), index=True
    )
    receipt_detail_id: Mapped[int | None] = mapped_column(
        ForeignKey("receipt_details.id", ondelete="CASCADE"), nullable=True, index=True
    )
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_available: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true", index=True
    )
    issue_voucher_id: Mapped[int | None] = mapped_column(
        ForeignKey("issue_vouchers.id"), nullable=True, index=True
    )
    movement: Mapped[InventoryMovement] = relationship(back_populates="serials")
    receipt_detail: Mapped[ReceiptDetail | None] = relationship(
        back_populates="serials", foreign_keys=[receipt_detail_id]
    )
    issue_voucher: Mapped["IssueVoucher | None"] = relationship(
        back_populates="serials", foreign_keys=[issue_voucher_id]
    )


class IssueRequest(Base):
    __tablename__ = "issue_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    request_number: Mapped[str] = mapped_column(String(40), unique=True)
    department_id: Mapped[int] = mapped_column(
        ForeignKey("departments.id"), index=True
    )
    request_date: Mapped[date] = mapped_column(Date, nullable=False)
    reason: Mapped[str] = mapped_column(String(255))
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id"), index=True)
    quantity: Mapped[float] = mapped_column(Float)
    notes: Mapped[str] = mapped_column(String(500), default="")
    status: Mapped[str] = mapped_column(
        String(20), default="draft", server_default="draft", index=True
    )
    rejection_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    department: Mapped[Department] = relationship(lazy="selectin")
    item: Mapped[Item] = relationship(lazy="selectin")
    created_by: Mapped[User] = relationship(lazy="selectin")
    issue_voucher: Mapped["IssueVoucher | None"] = relationship(
        back_populates="request", uselist=False
    )


class IssueVoucher(Base):
    __tablename__ = "issue_vouchers"

    id: Mapped[int] = mapped_column(primary_key=True)
    issue_number: Mapped[str] = mapped_column(String(40), unique=True)
    request_id: Mapped[int] = mapped_column(
        ForeignKey("issue_requests.id"), unique=True
    )
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id"), index=True)
    warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id"), index=True)
    quantity: Mapped[float] = mapped_column(Float)
    issued_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    issued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    request: Mapped[IssueRequest] = relationship(back_populates="issue_voucher")
    item: Mapped[Item] = relationship(lazy="selectin")
    warehouse: Mapped[Warehouse] = relationship(lazy="selectin")
    issued_by: Mapped[User] = relationship(lazy="selectin")
    movement: Mapped[InventoryMovement | None] = relationship(
        back_populates="issue_voucher", uselist=False
    )
    serials: Mapped[list[InventorySerial]] = relationship(
        back_populates="issue_voucher"
    )


class StockTransfer(Base):
    __tablename__ = "stock_transfers"

    id: Mapped[int] = mapped_column(primary_key=True)
    transfer_number: Mapped[str] = mapped_column(String(40), unique=True)
    source_warehouse_id: Mapped[int] = mapped_column(
        ForeignKey("warehouses.id"), index=True
    )
    destination_warehouse_id: Mapped[int] = mapped_column(
        ForeignKey("warehouses.id"), index=True
    )
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id"), index=True)
    quantity: Mapped[float] = mapped_column(Float)
    reason: Mapped[str] = mapped_column(String(255))
    notes: Mapped[str] = mapped_column(String(500), default="")
    status: Mapped[str] = mapped_column(
        String(20), default="draft", server_default="draft", index=True
    )
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    received_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True, index=True
    )
    received_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True, index=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    source_warehouse: Mapped[Warehouse] = relationship(
        foreign_keys=[source_warehouse_id], lazy="selectin"
    )
    destination_warehouse: Mapped[Warehouse] = relationship(
        foreign_keys=[destination_warehouse_id], lazy="selectin"
    )
    item: Mapped[Item] = relationship(lazy="selectin")
    created_by: Mapped[User] = relationship(
        foreign_keys=[created_by_id], lazy="selectin"
    )
    received_by: Mapped[User | None] = relationship(
        foreign_keys=[received_by_id], lazy="selectin"
    )
    completed_by: Mapped[User | None] = relationship(
        foreign_keys=[completed_by_id], lazy="selectin"
    )
    movements: Mapped[list[InventoryMovement]] = relationship(
        back_populates="transfer"
    )
    serials: Mapped[list["TransferSerial"]] = relationship(
        back_populates="transfer", cascade="all, delete-orphan", lazy="selectin"
    )


class TransferSerial(Base):
    __tablename__ = "transfer_serials"
    __table_args__ = (
        UniqueConstraint("transfer_id", "serial_id", name="uq_transfer_serial"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    transfer_id: Mapped[int] = mapped_column(
        ForeignKey("stock_transfers.id", ondelete="CASCADE"), index=True
    )
    serial_id: Mapped[int] = mapped_column(
        ForeignKey("inventory_serials.id"), index=True
    )
    serial_number: Mapped[str] = mapped_column(String(160))
    transfer: Mapped[StockTransfer] = relationship(back_populates="serials")
    serial: Mapped[InventorySerial] = relationship(lazy="selectin")


class Stocktake(Base):
    __tablename__ = "stocktakes"

    id: Mapped[int] = mapped_column(primary_key=True)
    stocktake_number: Mapped[str] = mapped_column(String(40), unique=True)
    stocktake_type: Mapped[str] = mapped_column(String(20))
    warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id"), index=True)
    stocktake_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default="draft", server_default="draft", index=True
    )
    notes: Mapped[str] = mapped_column(String(500), default="")
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    completed_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True, index=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    warehouse: Mapped[Warehouse] = relationship(lazy="selectin")
    created_by: Mapped[User] = relationship(
        foreign_keys=[created_by_id], lazy="selectin"
    )
    completed_by: Mapped[User | None] = relationship(
        foreign_keys=[completed_by_id], lazy="selectin"
    )
    lines: Mapped[list["StocktakeLine"]] = relationship(
        back_populates="stocktake", cascade="all, delete-orphan", lazy="selectin"
    )


class StocktakeLine(Base):
    __tablename__ = "stocktake_lines"
    __table_args__ = (
        UniqueConstraint("stocktake_id", "item_id", name="uq_stocktake_item"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    stocktake_id: Mapped[int] = mapped_column(
        ForeignKey("stocktakes.id", ondelete="CASCADE"), index=True
    )
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id"), index=True)
    warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id"), index=True)
    system_quantity: Mapped[float] = mapped_column(Float)
    actual_quantity: Mapped[float | None] = mapped_column(Float, nullable=True)
    difference: Mapped[float | None] = mapped_column(Float, nullable=True)
    stocktake: Mapped[Stocktake] = relationship(back_populates="lines")
    item: Mapped[Item] = relationship(lazy="selectin")
    warehouse: Mapped[Warehouse] = relationship(lazy="selectin")
