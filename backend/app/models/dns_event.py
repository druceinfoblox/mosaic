from datetime import datetime
from sqlalchemy import Integer, String, DateTime, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class DnsEvent(Base):
    __tablename__ = "dns_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True)
    client_ip: Mapped[str] = mapped_column(String(45), index=True)
    fqdn: Mapped[str] = mapped_column(String(253), index=True)
    query_type: Mapped[str] = mapped_column(String(16), default="A")
    rcode: Mapped[str] = mapped_column(String(16), default="NOERROR")
    answer_ips: Mapped[list] = mapped_column(JSON, default=list)
    message_type: Mapped[str] = mapped_column(String(16), default="QUERY")
    raw_line: Mapped[str | None] = mapped_column(Text, nullable=True)
    ingested_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
