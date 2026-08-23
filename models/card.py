from pydantic import BaseModel
from .models import Base
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship

class Card(Base):
    __tablename__ = 'cards'

    token = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    user_id = Column(Integer,ForeignKey("users.id"))

    user = relationship("User", back_populates="cards")