import csv
import io
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.database import get_db
from app.models.subnet_context import SubnetContext
from app.routers.illumio import _app_settings

router = APIRouter(prefix="/api/v1/settings", tags=["settings"])


class SettingsUpdate(BaseModel):
    ILLUMIO_PCE_URL: Optional[str] = None
    ILLUMIO_ORG_ID: Optional[str] = None
    ILLUMIO_API_KEY_USERNAME: Optional[str] = None
    ILLUMIO_API_KEY_SECRET: Optional[str] = None
    ILLUMIO_DRY_RUN: Optional[str] = None


@router.get("")
async def get_settings():
    from app.routers.illumio import get_settings as _get
    settings = _get()
    # Mask secret
    masked = dict(settings)
    if masked.get("ILLUMIO_API_KEY_SECRET"):
        masked["ILLUMIO_API_KEY_SECRET"] = "***"
    return masked


@router.put("")
async def update_settings(update: SettingsUpdate):
    data = update.model_dump(exclude_none=True)
    _app_settings.update(data)
    return {"status": "ok", "updated": list(data.keys())}


_subnet_router = APIRouter(prefix="/api/v1/subnet-context", tags=["settings"])


@_subnet_router.post("")
async def upload_subnet_context(file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    content = await file.read()
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        text = content.decode("latin-1")

    reader = csv.DictReader(io.StringIO(text))
    rows = []
    for row in reader:
        normalized = {k.strip().lower(): v.strip() for k, v in row.items()}
        cidr = normalized.get("cidr") or normalized.get("subnet") or normalized.get("network")
        if not cidr:
            continue
        rows.append(
            SubnetContext(
                cidr=cidr,
                label=normalized.get("label"),
                business_unit=normalized.get("business_unit") or normalized.get("bu"),
                site=normalized.get("site"),
                owner=normalized.get("owner"),
                notes=normalized.get("notes"),
            )
        )

    if not rows:
        raise HTTPException(status_code=422, detail="No valid subnet rows found")

    # Upsert: delete existing and reinsert
    await db.execute(delete(SubnetContext))
    db.add_all(rows)
    await db.commit()
    return {"status": "ok", "inserted": len(rows)}


@_subnet_router.get("")
async def get_subnet_context(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(SubnetContext))
    entries = result.scalars().all()
    return [
        {
            "id": e.id,
            "cidr": e.cidr,
            "label": e.label,
            "business_unit": e.business_unit,
            "site": e.site,
            "owner": e.owner,
        }
        for e in entries
    ]
