import os
from datetime import datetime, timedelta
from sqlalchemy import select, delete
from src.auth.database import Link, Stats, get_async_session

UNUSED_LINK_EXPIRE_DAYS = int(os.getenv('UNUSED_LINK_EXPIRE_DAYS', 160))

async def delete_unused_links():
    """Удаление ссылок, которые не использовались более N дней"""
    async for session in get_async_session():
        now = datetime.now()
        cutoff_date = now - timedelta(days=UNUSED_LINK_EXPIRE_DAYS)
        
        # Находим ссылки для удаления
        query = delete(Link).where(
            (
                (Link.id.not_in(select(Stats.link_id))) & (Link.created_at < cutoff_date) |
                (Link.id.in_(
                    select(Stats.link_id).where(Stats.last_visited_at < cutoff_date)
                ))
            ) &
            (
                (Link.expires_at.is_(None)) |  # Нет ограничения по времени жизни
                (Link.expires_at < now)  # Срок действия истёк
            )
        )
        
        result = await session.execute(query)
        deleted_count = result.rowcount
        await session.commit()
        
        return deleted_count