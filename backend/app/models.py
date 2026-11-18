# backend/app/models.py

from sqlalchemy import Column, Integer, String, Boolean, DateTime, UniqueConstraint
from sqlalchemy.sql import func
from app.database import Base


class StreamOfferState(Base):
    """
    Хранит локальное состояние оффера в потоке.
    Позволяет отслеживать удаленные (deleted) и закрепленные (pinned) офферы.
    """
    __tablename__ = "stream_offer_states"
    
    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, nullable=False, index=True)
    stream_id = Column(Integer, nullable=False, index=True)
    offer_id = Column(Integer, nullable=False)
    offer_name = Column(String, nullable=False)
    
    # Состояние оффера
    share = Column(Integer, nullable=False, default=0)
    state = Column(String, nullable=False, default="active")
    
    # Локальные флаги
    deleted = Column(Boolean, nullable=False, default=False)
    pinned = Column(Boolean, nullable=False, default=False)
    
    # Позиция в списке
    position = Column(Integer, nullable=False, default=0)
    
    # Временные метки
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Уникальный ключ: один оффер в одном потоке
    __table_args__ = (
        UniqueConstraint('stream_id', 'offer_id', name='uq_stream_offer'),
    )
    
    def __repr__(self):
        return f"<StreamOfferState stream={self.stream_id} offer={self.offer_id} deleted={self.deleted}>"
