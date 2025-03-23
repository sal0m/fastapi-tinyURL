from sqlalchemy import Column, Integer, String, Boolean, TIMESTAMP, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class User(Base):
    __tablename__ = "user"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    email = Column(String, nullable=False)
    registered_at = Column(TIMESTAMP, default=datetime.utcnow)
    is_active = Column(Boolean, default=True, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)
    is_verified = Column(Boolean, default=True, nullable=False)  
    
    url = relationship("URL", back_populates="user")


class URL(Base):
    __tablename__ = "url"

    id = Column(Integer, primary_key=True, index=True)
    original_url = Column(String, nullable=False)
    short_code = Column(String, unique=True, nullable=False)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    expires_at = Column(TIMESTAMP, nullable=True)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=True)
    custom_alias = Column(String, unique=True, nullable=True)
    
    user = relationship("User", back_populates="url")
    stats = relationship("Stats", back_populates="url")


class Stats(Base):
    __tablename__ = "stats"

    id = Column(Integer, primary_key=True, index=True)
    url_id = Column(Integer, ForeignKey("url.id"), nullable=False)
    visit_count = Column(Integer, default=0)
    last_visited_at = Column(TIMESTAMP, nullable=True)
    
    url = relationship("URL", back_populates="stats")
