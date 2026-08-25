from pydantic import BaseModel
from .models import Base
from sqlalchemy import Column, Integer, String
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
    service_name = Column(String,default="Unnamed")
    balance = Column(Integer,default=0)

    last_name = Column(String,default="")
    first_name = Column(String,default="")
    middle_name = Column(String,default="")

    type = Column(SQLEnum(UserType),default=UserType.USER)

    cards = relationship("Card", back_populates="user")
    service_applications = relationship("Application", foreign_keys="Application.service_id", back_populates="service")
    applications = relationship("Application", foreign_keys="Application.payer_id", back_populates="payer")