from .models import Base
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
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
    status = Column(SQLEnum(TransactionStatus),default=TransactionStatus.PENDING)

    sender_id = Column(Integer,ForeignKey("users.id"))
    receiver_id = Column(Integer,ForeignKey("users.id"))

    sender = relationship("User", foreign_keys=[sender_id], back_populates="transactions")
    receiver = relationship("User", foreign_keys=[receiver_id], back_populates="transactions")
