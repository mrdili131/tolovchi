from .models import Base
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship

class UserSession(Base):
    __tablename__ = 'user_sessions'

    created_at = Column(DateTime, server_default=func.now())

    user_id = Column(Integer, ForeignKey("users.id"))
    jti = Column(String, nullable=False, unique=True)
    user_agent = Column(String, nullable=True)
    ip_address = Column(String, nullable=True)
    expires_at = Column(DateTime, nullable=False)
    last_seen_at = Column(DateTime, nullable=True)
    revoked_at = Column(DateTime, nullable=True)

    user = relationship("User")
