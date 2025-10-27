from sqlalchemy import Column, Integer, String, JSON, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from db import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String(80), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class Room(Base):
    __tablename__ = "rooms"
    id = Column(Integer, primary_key=True)
    code = Column(String(16), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    hands = relationship("Hand", back_populates="room")

class Hand(Base):
    __tablename__ = "hands"
    id = Column(Integer, primary_key=True)
    room_id = Column(Integer, ForeignKey("rooms.id"))
    started_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)
    summary = Column(JSON, nullable=True)  # {winners:[...], pot, community:[...]}
    room = relationship("Room", back_populates="hands")
