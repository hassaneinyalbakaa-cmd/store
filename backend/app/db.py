from collections.abc import AsyncGenerator
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from .config import get_settings


def _async_database_url(url: str) -> str:
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    parsed = urlsplit(url)
    query = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if key not in {"sslmode", "channel_binding"}
    ]
    return urlunsplit(parsed._replace(query=urlencode(query)))


def _async_connect_args(url: str) -> dict[str, str]:
    query = dict(parse_qsl(urlsplit(url).query, keep_blank_values=True))
    if query.get("sslmode") in {"require", "verify-ca", "verify-full"}:
        return {"ssl": "require"}
    return {}


engine = create_async_engine(
    _async_database_url(get_settings().database_url),
    connect_args=_async_connect_args(get_settings().database_url),
    pool_pre_ping=True,
    pool_recycle=1800,
)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session
