from pydantic import BaseModel
from .models import Base
from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy import Enum as SQLEnum
from enum import Enum
from sqlalchemy.orm import relationship

class UserType(Enum):
    USER = "user"
    SERVICE = "service"
    ADMIN = "admin"


class User(Base):
    __tablename__ = 'users'

    username = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    service_name = Column(String,default="This is not a service account")
    balance = Column(Integer,default=0)

    last_name = Column(String,default="")
    first_name = Column(String,default="")
    middle_name = Column(String,default="")
    phone_number = Column(String, nullable=True)
    webhook_url = Column(String, nullable=True)

    role = Column(SQLEnum(UserType),default=UserType.USER)
    is_active = Column(Boolean, default=True)

    cards = relationship("Card", back_populates="user")
    service_applications = relationship("Application", foreign_keys="Application.service_id", back_populates="service")
    applications = relationship("Application", foreign_keys="Application.payer_id", back_populates="payer")
    transactions = relationship("Transaction", foreign_keys="Transaction.sender_id", back_populates="sender")
    service_transactions = relationship("Transaction", foreign_keys="Transaction.receiver_id", back_populates="receiver")
    api_keys = relationship("ApiKey", back_populates="service")