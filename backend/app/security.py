import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from pwdlib import PasswordHash
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from .config import get_settings
from .models import User, UserSession


password_hash = PasswordHash.recommended()


def hash_password(value: str) -> str:
    return password_hash.hash(value)


def verify_password(value: str, hashed: str) -> bool:
    return password_hash.verify(value, hashed)


def _hash_session_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


async def create_session(db: AsyncSession, user: User) -> str:
    raw_token = secrets.token_urlsafe(48)
    now = datetime.now(UTC)
    session = UserSession(
        id=_hash_session_token(raw_token),
        user_id=user.id,
        expires_at=now + timedelta(hours=get_settings().session_ttl_hours),
    )
    db.add(session)
    await db.commit()
    return raw_token


async def get_session_user(db: AsyncSession, raw_token: str | None) -> User | None:
    if not raw_token:
        return None
    result = await db.execute(
        select(UserSession).where(
            UserSession.id == _hash_session_token(raw_token),
            UserSession.expires_at > datetime.now(UTC),
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        return None
    await db.refresh(session, attribute_names=["user"])
    return session.user


async def delete_session(db: AsyncSession, raw_token: str | None) -> None:
    if raw_token:
        await db.execute(
            delete(UserSession).where(UserSession.id == _hash_session_token(raw_token))
        )
        await db.commit()
