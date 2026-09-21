from .models import Base
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship

class Notification(Base):
    __tablename__ = 'notifications'

    created_at = Column(DateTime, server_default=func.now())

    title = Column(String, nullable=False)
    message = Column(String, nullable=False)

    # NULL target_user_id means broadcast to every account.
    target_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    target_user = relationship("User", foreign_keys=[target_user_id])
    admin = relationship("User", foreign_keys=[created_by])


class NotificationRead(Base):
    __tablename__ = 'notification_reads'

    notification_id = Column(Integer, ForeignKey("notifications.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    read_at = Column(DateTime, server_default=func.now())

    notification = relationship("Notification")
