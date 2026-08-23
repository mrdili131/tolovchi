from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import Column, Integer, String, Date
from datetime import date

class Base(DeclarativeBase):
    id = Column(Integer, primary_key=True, unique=True)
    created_at = Column(Date, default=date.today())