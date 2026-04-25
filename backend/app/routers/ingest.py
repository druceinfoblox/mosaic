from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import get_db
from app.models.dns_event import DnsEvent
from app.services.parser import parse_dns_logs
from app.services.normalizer import bulk_insert_events, clear_events
from app.services.enricher import seed_demo_subnet_context
from app.fixtures.generator import generate_csv

router = APIRouter(prefix="/api/v1/ingest", tags=["ingest"])


@router.post("")
async def ingest_file(file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    content = await file.read()
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        text = content.decode("latin-1")

    events = parse_dns_logs(text)
    if not events:
        raise HTTPException(status_code=422, detail="No valid DNS events parsed from file")

    inserted = await bulk_insert_events(db, events)
    return {"status": "ok", "parsed": len(events), "inserted": inserted, "filename": file.filename}


@router.post("/generate-demo")
async def generate_demo(db: AsyncSession = Depends(get_db)):
    await clear_events(db)
    await seed_demo_subnet_context(db)

    csv_content = generate_csv(days=90, clients_per_subnet=50)
    events = parse_dns_logs(csv_content)
    inserted = await bulk_insert_events(db, events)
    return {
        "status": "ok",
        "message": "Demo data generated",
        "events_parsed": len(events),
        "events_inserted": inserted,
    }


@router.get("/status")
async def ingest_status(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(func.count(DnsEvent.id)))
    total = result.scalar() or 0

    result2 = await db.execute(select(func.count(func.distinct(DnsEvent.client_ip))))
    unique_clients = result2.scalar() or 0

    result3 = await db.execute(select(func.count(func.distinct(DnsEvent.fqdn))))
    unique_fqdns = result3.scalar() or 0

    result4 = await db.execute(select(func.min(DnsEvent.timestamp), func.max(DnsEvent.timestamp)))
    row = result4.first()
    min_ts, max_ts = (row[0], row[1]) if row else (None, None)

    return {
        "total_events": total,
        "unique_clients": unique_clients,
        "unique_fqdns": unique_fqdns,
        "earliest": min_ts.isoformat() if min_ts else None,
        "latest": max_ts.isoformat() if max_ts else None,
    }
