from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Item


async def lock_item_inventory(db: AsyncSession, item_id: int) -> None:
    """Serialize balance-changing operations for an item.

    Inventory balances are derived from movement rows, so there is no balance
    row that can be locked directly. Locking the stable item row gives all
    issue and transfer transactions for that item a shared serialization
    point, including when the balance is currently zero and has no movement
    rows.
    """
    await db.execute(
        select(Item.id).where(Item.id == item_id).with_for_update()
    )