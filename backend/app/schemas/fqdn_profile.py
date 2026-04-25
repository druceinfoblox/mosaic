from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class FqdnProfileSchema(BaseModel):
    fqdn: str
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    total_queries: int
    unique_clients: int
    answer_ips: list[str]
    is_internal: bool
    category: Optional[str] = None

    model_config = {"from_attributes": True}
