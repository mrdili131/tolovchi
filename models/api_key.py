from .models import Base
from sqlalchemy import Column, Integer, String, Boolean, Date, ForeignKey
from sqlalchemy.orm import relationship

class ApiKey(Base):
    __tablename__ = 'api_keys'

    service_id = Column(Integer, ForeignKey("users.id"))
    name = Column(String, default="API key")
    key_prefix = Column(String, nullable=False)
    key_hash = Column(String, nullable=False, unique=True)
    is_active = Column(Boolean, default=True)
    last_used_at = Column(Date, nullable=True)
    revoked_at = Column(Date, nullable=True)

    service = relationship("User", back_populates="api_keys")
