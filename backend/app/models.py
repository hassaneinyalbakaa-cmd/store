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
    notes: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    item: Mapped[Item] = relationship(lazy="selectin")
    warehouse: Mapped[Warehouse] = relationship(lazy="selectin")
    storage_location: Mapped[StorageLocation | None] = relationship(lazy="selectin")
    receipt_detail: Mapped[ReceiptDetail | None] = relationship(back_populates="movement")
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
    movement: Mapped[InventoryMovement] = relationship(back_populates="serials")
    receipt_detail: Mapped[ReceiptDetail | None] = relationship(
        back_populates="serials", foreign_keys=[receipt_detail_id]
    )
