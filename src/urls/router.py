import random
import string
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from src.auth.database import Link, Stats, User, get_async_session
from src.auth.manager import current_active_user
from src.redis import set_cache, get_cache, delete_cache
from fastapi.responses import RedirectResponse

router = APIRouter()

# Функция для генерации случайного короткого кода
def generate_short_code(length: int = 10):
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

# Создание короткой ссылки
@router.post("/links/shorten")
async def shorten_link(
    original_url: str, 
    custom_alias: str = None, 
    expires_at: datetime = None, 
    user: User = Depends(current_active_user) 
):
    async for session in get_async_session(): 
        if custom_alias:
            result = await session.execute(select(Link).filter(Link.custom_alias == custom_alias))
            if result.scalars().first():
                raise HTTPException(status_code=400, detail="Custom alias is already taken.")
    
    short_code = custom_alias if custom_alias else generate_short_code()
    link = Link(original_url=original_url, short_code=short_code, user_email=user.email if user else None, expires_at=expires_at)
    
    async for session in get_async_session(): 
        session.add(link)
        await session.commit()
        return {"short_code": short_code, "original_url": original_url}

# Перенаправление по короткой ссылке
@router.get("/links/{short_code}")
async def redirect_to_original(short_code: str):
    cached_url = await get_cache(f"link:{short_code}")
    if cached_url:
        return RedirectResponse(url=cached_url, status_code=307)
    
    async for session in get_async_session():
        result = await session.execute(select(Link).filter(Link.short_code == short_code))
        link = result.scalars().first()
        if not link:
            raise HTTPException(status_code=404, detail="Link not found.")
        
        result_stats = await session.execute(select(Stats).filter(Stats.link_id == link.id))
        stats = result_stats.scalars().first()
        if not stats:
            stats = Stats(link_id=link.id, visit_count=1, last_visited_at=datetime.now())
            session.add(stats)
        else:
            stats.visit_count += 1
            stats.last_visited_at = datetime.now()

        await session.commit()

        if stats.visit_count > 10:
            await set_cache(f"link:{short_code}", link.original_url, expire=3600)
        
        return RedirectResponse(url=link.original_url, status_code=307)

# Получение статистики по короткой ссылке
@router.get("/links/{short_code}/stats")
async def get_link_stats(short_code: str):
    async for session in get_async_session():
        result = await session.execute(
            select(Link, Stats).outerjoin(Stats, Link.id == Stats.link_id).filter(Link.short_code == short_code)
        )
        row = result.first()

        if not row:
            raise HTTPException(status_code=404, detail="Link not found.")

        link, stats = row

        return {
            "original_url": link.original_url,
            "created_at": link.created_at,
            "visit_count": stats.visit_count if stats else 0,
            "last_visited_at": stats.last_visited_at if stats else None
        }

# Удаление короткой ссылки
@router.delete("/links/{short_code}")
async def delete_link(short_code: str, user: User = Depends(current_active_user)):  
    async for session in get_async_session():
        result = await session.execute(select(Link).filter(Link.short_code == short_code))
        link = result.scalars().first()
        if not link:
            raise HTTPException(status_code=404, detail="Link not found.")
        
        if link.user_email != user.email:
            raise HTTPException(status_code=403, detail="You do not have permission to delete this link.")
        
        await session.delete(link)
        await session.commit()
        await delete_cache(f"link:{short_code}")
        return {"message": "Link deleted successfully."}

# Обновление оригинального URL для короткой ссылки
@router.put("/links/{short_code}")
async def update_link(short_code: str, original_url: str, user: User = Depends(current_active_user)): 
    async for session in get_async_session():
        result = await session.execute(select(Link).filter(Link.short_code == short_code))
        link = result.scalars().first()
        if not link:
            raise HTTPException(status_code=404, detail="Link not found.")
        
        if link.user_email != user.email:
            raise HTTPException(status_code=403, detail="You do not have permission to update this link.")
        
        link.original_url = original_url
        await session.commit()
        await delete_cache(f"link:{short_code}")
        return {"message": "Link updated successfully."}

# Поиск ссылки по оригинальному URL
@router.get("/links/search")
async def search_link(original_url: str):
    async for session in get_async_session():
        result = await session.execute(select(Link).filter(Link.original_url == original_url))
        link = result.scalars().first()
        if not link:
            raise HTTPException(status_code=404, detail="Link not found.")
        
        return {"short_code": link.short_code, "original_url": link.original_url}
