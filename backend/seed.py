import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .app.db import SessionLocal
from .app.models import Permission, Role, User
from .app.security import hash_password


PERMISSIONS = [
    ("dashboard:read", "عرض لوحة التحكم", "الوصول إلى الملخص الأولي"),
    ("users:read", "عرض المستخدمين", "عرض قائمة مستخدمي النظام"),
    ("users:write", "إدارة المستخدمين", "إنشاء وتعديل المستخدمين"),
    ("roles:read", "عرض الأدوار والصلاحيات", "عرض أدوار النظام وصلاحياتها"),
    ("warehouses:read", "عرض المخازن", "عرض قائمة المخازن"),
    ("warehouses:write", "إدارة المخازن", "إنشاء وتعديل المخازن"),
    ("departments:read", "عرض الأقسام", "عرض قائمة الأقسام"),
    ("departments:write", "إدارة الأقسام", "إنشاء وتعديل الأقسام"),
    ("items:read", "عرض الأصناف", "عرض والبحث في دليل الأصناف"),
    ("items:write", "إدارة الأصناف", "إنشاء وتعديل وتعطيل الأصناف"),
    ("receipts:read", "عرض سندات الاستلام", "عرض سجل سندات الاستلام"),
    ("receipts:write", "إنشاء سندات الاستلام", "إنشاء سندات الاستلام وإضافة المخزون"),
    ("inventory:read", "عرض المخزون", "عرض الأرصدة وحركات المخزون والصلاحية"),
    ("inventory:write", "إدارة المخزون", "إضافة الأرصدة الافتتاحية"),
]

ROLES = [
    (
        "admin",
        "مدير النظام",
        "إدارة كاملة للمستخدمين والأدوار والصلاحيات",
        [
            "dashboard:read",
            "users:read",
            "users:write",
            "roles:read",
            "warehouses:read",
            "warehouses:write",
            "departments:read",
            "departments:write",
            "items:read",
            "items:write",
            "receipts:read",
            "receipts:write",
            "inventory:read",
            "inventory:write",
        ],
    ),
    (
        "warehouse_keeper",
        "أمين المخزن",
        "الوصول التشغيلي للمخزن مع قراءة المستخدمين",
        [
            "dashboard:read",
            "users:read",
            "roles:read",
            "warehouses:read",
            "departments:read",
            "items:read",
            "items:write",
            "receipts:read",
            "receipts:write",
            "inventory:read",
            "inventory:write",
        ],
    ),
    (
        "department_employee",
        "موظف القسم",
        "الوصول الأساسي إلى النظام",
        ["dashboard:read"],
    ),
]


async def seed() -> None:
    async with SessionLocal() as db:
        permission_map: dict[str, Permission] = {}
        for code, display_name, description in PERMISSIONS:
            permission = (
                await db.execute(select(Permission).where(Permission.code == code))
            ).scalar_one_or_none()
            if not permission:
                permission = Permission(
                    code=code, display_name=display_name, description=description
                )
                db.add(permission)
            permission_map[code] = permission
        await db.flush()

        role_map: dict[str, Role] = {}
        for name, display_name, description, permission_codes in ROLES:
            role = (await db.execute(select(Role).where(Role.name == name))).scalar_one_or_none()
            if not role:
                role = Role(name=name, display_name=display_name, description=description)
                db.add(role)
            role.display_name = display_name
            role.description = description
            role.permissions = [permission_map[code] for code in permission_codes]
            role_map[name] = role
        await db.flush()

        admin = (
            await db.execute(select(User).where(User.username == "admin"))
        ).scalar_one_or_none()
        if not admin:
            db.add(
                User(
                    username="admin",
                    display_name="مدير النظام",
                    password_hash=hash_password("Admin@12345"),
                    role_id=role_map["admin"].id,
                    is_active=True,
                )
            )
        await db.commit()


if __name__ == "__main__":
    asyncio.run(seed())
