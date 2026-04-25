from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class SubnetContext(Base):
    __tablename__ = "subnet_context"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    cidr: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    label: Mapped[str | None] = mapped_column(String(100), nullable=True)
    business_unit: Mapped[str | None] = mapped_column(String(100), nullable=True)
    site: Mapped[str | None] = mapped_column(String(100), nullable=True)
    owner: Mapped[str | None] = mapped_column(String(100), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
