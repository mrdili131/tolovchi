from pydantic import BaseModel
from .models import Base
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Date, func
from sqlalchemy import Enum as SQLEnum
from enum import Enum
from sqlalchemy.orm import relationship

class PaymentFrequency(Enum):
    # DAILY = "daily"
    # WEEKLY = "weekly"
    MONTHLY = "monthly"
    # YEARLY = "yearly"

class Application(Base):
    __tablename__ = 'applications'

    name = Column(String, default="Unnamed")
    description = Column(String, default="No description")
    amount = Column(Integer,default=1000)
    balance = Column(Integer,default=0)
    debt = Column(Integer,default=0)
    cancellable = Column(Boolean, default=True)
    frequency = Column(SQLEnum(PaymentFrequency),default=PaymentFrequency.MONTHLY)
    pay_day = Column(Integer,default=1)
    start_date = Column(Date,server_default=func.current_date())
    end_date = Column(Date,nullable=True)
    is_active = Column(Boolean, default=False)
    service_id = Column(Integer,ForeignKey("users.id"))
    payer_id = Column(Integer,ForeignKey("users.id"))

    service = relationship("User", foreign_keys=[service_id], back_populates="service_applications")
    payer = relationship("User", foreign_keys=[payer_id], back_populates="applications")