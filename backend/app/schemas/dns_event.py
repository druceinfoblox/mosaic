from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class DnsEventCreate(BaseModel):
    timestamp: datetime
    client_ip: str
    fqdn: str
    query_type: str = "A"
    rcode: str = "NOERROR"
    answer_ips: list[str] = []
    message_type: str = "QUERY"
    raw_line: Optional[str] = None


class DnsEventSchema(DnsEventCreate):
    id: int
    ingested_at: datetime

    model_config = {"from_attributes": True}
