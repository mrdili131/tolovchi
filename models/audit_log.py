from .models import Base
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship

class AdminAuditLog(Base):
    __tablename__ = 'admin_audit_logs'

    created_at = Column(DateTime, server_default=func.now())

    admin_id = Column(Integer, ForeignKey("users.id"))
    action = Column(String, nullable=False)
    target_type = Column(String, nullable=False)
    target_id = Column(Integer, nullable=False)
    detail = Column(String, nullable=True)

    admin = relationship("User", foreign_keys=[admin_id])
