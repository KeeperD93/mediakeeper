from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, func
from models.base import Base


class SchedulerTask(Base):
    __tablename__ = "scheduler_tasks"

    id           = Column(Integer,                    primary_key=True, index=True)
    key          = Column(String(100),  nullable=False, unique=True, index=True)
    label        = Column(String(200),  nullable=False)
    enabled      = Column(Boolean,      default=True)
    interval_sec = Column(Integer,      nullable=False)
    last_run     = Column(DateTime(timezone=True), nullable=True)
    last_status  = Column(String(20),   nullable=True)   # ok | error | running
    last_error   = Column(Text,         nullable=True)
    run_count    = Column(Integer,      default=0)
    created_at   = Column(DateTime(timezone=True), server_default=func.now())
    updated_at   = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
