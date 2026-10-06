from datetime import datetime, timezone
from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from .db import Base

def utcnow() -> datetime:
    return datetime.now(timezone.utc)

class Decision(Base):
    __tablename__ = 'decisions'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    coin: Mapped[str] = mapped_column(String(20), index=True)
    decision: Mapped[str] = mapped_column(String(10))
    reason: Mapped[str] = mapped_column(Text)
    module_votes: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)

class Event(Base):
    __tablename__ = 'events'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_type: Mapped[str] = mapped_column(String(40), index=True)
    coin: Mapped[str] = mapped_column(String(20), default='')
    payload: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)

class Trade(Base):
    __tablename__ = 'trades'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(30), index=True)
    side: Mapped[str] = mapped_column(String(10))
    amount: Mapped[float] = mapped_column(Float)
    price: Mapped[float] = mapped_column(Float)
    realized_pnl: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(30))
    exchange_order_id: Mapped[str] = mapped_column(String(100), default='')
    reason: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
