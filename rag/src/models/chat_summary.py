from sqlalchemy import Column, Integer, Text, DateTime, func
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class ChatSummary(Base):
    __tablename__ = 'chat_summaries'

    id = Column(Integer, primary_key=True, autoincrement=True)
    summary = Column(Text, nullable=False, default="")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now()) 