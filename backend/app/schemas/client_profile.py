from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class ClientProfileSchema(BaseModel):
    client_ip: str
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    total_queries: int
    unique_fqdns: int
    top_fqdns: list[str]
    subnet: Optional[str] = None
    owner: Optional[str] = None
    site: Optional[str] = None
    business_unit: Optional[str] = None
    hostname: Optional[str] = None

    model_config = {"from_attributes": True}
