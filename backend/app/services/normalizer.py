"""
Normalizes parsed DNS events into canonical form and persists to DB.
"""
import re
from datetime import datetime
from typing import Sequence
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.models.dns_event import DnsEvent
from app.schemas.dns_event import DnsEventCreate

INTERNAL_IP_RE = re.compile(
    r"^(10\.|172\.(1[6-9]|2[0-9]|3[01])\.|192\.168\.|127\.|169\.254\.|::1)"
)


def is_private_ip(ip: str) -> bool:
    return bool(INTERNAL_IP_RE.match(ip))


async def bulk_insert_events(db: AsyncSession, events: list[DnsEventCreate]) -> int:
    db_events = [
        DnsEvent(
            timestamp=e.timestamp,
            client_ip=e.client_ip,
            fqdn=e.fqdn.lower().strip("."),
            query_type=e.query_type,
            rcode=e.rcode,
            answer_ips=e.answer_ips,
            message_type=e.message_type,
            raw_line=e.raw_line,
            ingested_at=datetime.utcnow(),
        )
        for e in events
        if e.client_ip and e.fqdn
    ]
    db.add_all(db_events)
    await db.commit()
    return len(db_events)


async def clear_events(db: AsyncSession) -> None:
    await db.execute(delete(DnsEvent))
    await db.commit()
