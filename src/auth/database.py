from collections.abc import AsyncGenerator
from datetime import datetime

from fastapi import Depends
from fastapi_users.db import SQLAlchemyBaseUserTableUUID, SQLAlchemyUserDatabase
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, BigInteger, Text
from src.config import DB_HOST, DB_PASS, DB_USER, DB_PORT, DB_NAME

DATABASE_URL = f'postgresql+asyncpg://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}'

class Base(DeclarativeBase):
    pass

class User(SQLAlchemyBaseUserTableUUID, Base):
    registered_at = Column(DateTime, nullable=False, default=datetime.now())

    # Связь с ссылками
    links = relationship("Link", back_populates="user", foreign_keys="[Link.user_email]")

class Link(Base):
    __tablename__ = "link"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    original_url = Column(Text, nullable=False)  # Длинный URL
    short_code = Column(String(10), unique=True, nullable=False, index=True)  # Код короткой ссылки
    created_at = Column(DateTime, nullable=False, default=datetime.now())  # Дата создания
    expires_at = Column(DateTime, nullable=True)  # Дата истечения (если есть)
    custom_alias = Column(String(50), unique=True, nullable=True)  # Пользовательский alias
    user_email = Column(String, ForeignKey("user.email", ondelete="SET NULL"), nullable=True)  # Владелец ссылки

    # Связь с пользователем
    user = relationship("User", back_populates="links", foreign_keys=[user_email])

    # Связь со статистикой
    stats = relationship("Stats", back_populates="link", cascade="all, delete-orphan")

class Stats(Base):
    __tablename__ = "stats"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    link_id = Column(BigInteger, ForeignKey("link.id", ondelete="CASCADE"), nullable=False)
    visit_count = Column(Integer, nullable=False, default=0)  # Счетчик посещений
    last_visited_at = Column(DateTime, nullable=True)  # Дата последнего посещения

    # Связь с ссылками
    link = relationship("Link", back_populates="stats")

engine = create_async_engine(DATABASE_URL)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)

async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session

async def get_user_db(session: AsyncSession = Depends(get_async_session)):
    yield SQLAlchemyUserDatabase(session, User)
