from .models import Base
from sqlalchemy import Column, Integer, String, Date, ForeignKey
from sqlalchemy.orm import relationship
from enum import Enum

class PayoutStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    REJECTED = "rejected"

class PayoutRequest(Base):
    __tablename__ = 'payout_requests'

    service_id = Column(Integer, ForeignKey("users.id"))
    amount = Column(Integer, nullable=False)
    card_number = Column(String, nullable=False)
    status = Column(String, default=PayoutStatus.PENDING.value)
    admin_note = Column(String, nullable=True)
    processed_at = Column(Date, nullable=True)
    processed_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    service = relationship("User", foreign_keys=[service_id])
    processed_by_admin = relationship("User", foreign_keys=[processed_by])
