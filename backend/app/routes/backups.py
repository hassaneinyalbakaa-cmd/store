import os
import shutil
import subprocess
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.engine import make_url

from ..config import get_settings
from ..db import get_db
from ..dependencies import require_admin
from ..models import BackupRecord, User
from ..schemas import BackupInfo as BackupInfoSchema
from ..serializers import to_backup_info

router = APIRouter(tags=["backups"])


def backup_dir() -> Path:
    directory = Path(get_settings().backup_directory).expanduser()
    directory.mkdir(parents=True, exist_ok=True)
    return directory.resolve()


async def load_backup(db: AsyncSession, backup_id: int) -> BackupRecord | None:
    result = await db.execute(
        select(BackupRecord)
        .options(selectinload(BackupRecord.created_by))
        .where(BackupRecord.id == backup_id)
    )
    return result.scalar_one_or_none()


@router.get("/backups", response_model=list[BackupInfoSchema])
async def list_backups(
    _: User = Depends(require_admin()),
    db: AsyncSession = Depends(get_db),
) -> list[BackupInfoSchema]:
    result = await db.execute(
        select(BackupRecord)
        .options(selectinload(BackupRecord.created_by))
        .order_by(BackupRecord.id.desc())
    )
    return [to_backup_info(backup) for backup in result.scalars().all()]


@router.post(
    "/backups",
    response_model=BackupInfoSchema,
    status_code=status.HTTP_201_CREATED,
)
async def create_backup(
    _: User = Depends(require_admin()),
    db: AsyncSession = Depends(get_db),
) -> BackupInfoSchema:
    executable = shutil.which("pg_dump")
    if executable is None:
        raise HTTPException(status_code=400, detail="أداة pg_dump غير متاحة على الخادم")

    settings = get_settings()
    backup = BackupRecord(
        filename="pending",
        file_path="pending",
        size_bytes=0,
        created_by_id=_.id,
    )
    db.add(backup)
    await db.flush()
    filename = f"warehouse-backup-{backup.id:08d}.dump"
    destination = backup_dir() / filename
    db_url = make_url(settings.database_url)
    safe_url = db_url.set(password=None).render_as_string(hide_password=False)
    process_env = os.environ.copy()
    if db_url.password:
        process_env["PGPASSWORD"] = db_url.password
    completed = subprocess.run(
        [
            executable,
            "--format=custom",
            "--no-owner",
            "--file",
            str(destination),
            "--dbname",
            safe_url,
        ],
        env=process_env,
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    if completed.returncode != 0:
        destination.unlink(missing_ok=True)
        await db.rollback()
        raise HTTPException(
            status_code=400,
            detail=f"تعذر إنشاء النسخة الاحتياطية: {completed.stderr[-500:]}",
        )

    backup.filename = filename
    backup.file_path = str(destination)
    backup.size_bytes = destination.stat().st_size
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        destination.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="تعذر حفظ سجل النسخة الاحتياطية")
    saved = await load_backup(db, backup.id)
    return to_backup_info(saved)


@router.get("/backups/{backupId}/download")
async def download_backup(
    backupId: int,
    _: User = Depends(require_admin()),
    db: AsyncSession = Depends(get_db),
) -> Response:
    backup = await load_backup(db, backupId)
    if backup is None:
        raise HTTPException(status_code=404, detail="النسخة الاحتياطية غير موجودة")
    root = backup_dir()
    expected_name = f"warehouse-backup-{backup.id:08d}.dump"
    path = next(
        (candidate for candidate in root.glob("warehouse-backup-*.dump")
         if candidate.name == expected_name and candidate.is_file()),
        None,
    )
    if path is None:
        raise HTTPException(status_code=404, detail="ملف النسخة الاحتياطية غير متاح")
    return FileResponse(
        path,
        media_type="application/octet-stream",
        filename=backup.filename,
    )