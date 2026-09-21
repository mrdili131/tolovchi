from .models import Base
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship

class PaymentAttempt(Base):
    __tablename__ = 'payment_attempts'

    created_at = Column(DateTime, server_default=func.now())

    application_id = Column(Integer, ForeignKey("applications.id"))
    success = Column(Boolean, nullable=False)
    reason = Column(String, nullable=True)
    attempt_number = Column(Integer, nullable=False)

    application = relationship("Application", back_populates="payment_attempts")
