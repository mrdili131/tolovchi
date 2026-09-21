from .models import Base
from sqlalchemy import Column, Integer, String, Boolean, Date, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy import Enum as SQLEnum
from enum import Enum

class TransactionStatus(Enum):
    PROVIDED = "provided"
    PENDING = "pending"
    REJECTED = "rejected"


class Transaction(Base):
    __tablename__ = 'transactions'

    amount = Column(Integer)
    fee_amount = Column(Integer, default=0)
    status = Column(SQLEnum(TransactionStatus),default=TransactionStatus.PENDING)

    is_flagged = Column(Boolean, default=False)
    admin_note = Column(String, nullable=True)
    refunded_at = Column(Date, nullable=True)

    sender_id = Column(Integer,ForeignKey("users.id"))
    receiver_id = Column(Integer,ForeignKey("users.id"))
    application_id = Column(Integer,ForeignKey("applications.id"))

    sender = relationship("User", foreign_keys=[sender_id], back_populates="transactions")
    receiver = relationship("User", foreign_keys=[receiver_id], back_populates="service_transactions")
    application = relationship("Application", foreign_keys=[application_id], back_populates="transactions")
