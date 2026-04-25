from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class DependencySchema(BaseModel):
    id: int
    client_ip: str
    fqdn: str
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    query_count: int
    days_observed: int
    confidence_score: float
    is_internal: bool
    answer_ips_stable: bool

    model_config = {"from_attributes": True}
