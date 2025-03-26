import random
import string
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from src.auth.database import Link, Stats, User, get_async_session
from src.auth.manager import current_active_user
from src.redis_utils import set_cache, get_cache, delete_cache
from fastapi.responses import RedirectResponse
# from slowapi import Limiter
from slowapi.util import get_remote_address
import qrcode
from io import BytesIO
from fastapi.responses import StreamingResponse

router = APIRouter()
# limiter = Limiter(key_func=get_remote_address, storage_uri="redis://redis:6379/1")  

MAX_ANONYMOUS_LINK_LIFETIME = timedelta(days=30)  # Максимальный срок жизни анонимной ссылки
DEFAULT_ANONYMOUS_EXPIRATION = timedelta(days=7)   # Срок по умолчанию, если не указан


# Генерация уникального короткого кода
async def generate_unique_short_code(length: int = 10) -> str:
    characters = string.ascii_letters + string.digits
    async for session in get_async_session():
        while True:
            code = ''.join(random.choice(characters) for _ in range(length))
            result = await session.execute(select(Link).filter(Link.short_code == code))
            if not result.scalars().first():
                return code

# Создание короткой ссылки
@router.post("/links/shorten")
# @limiter.limit("10/minute") #Не больше 10 запросов в минуту, защита от брутфорса и DDoS-атак
async def shorten_link(
    request: Request,  
    original_url: str, 
    custom_alias: str = None, 
    expires_at: datetime = None, 
    user: User = Depends(current_active_user), 
):
    async for session in get_async_session(): 
        if custom_alias:
            result = await session.execute(select(Link).filter(Link.custom_alias == custom_alias))
            if result.scalars().first():
                raise HTTPException(status_code=400, detail="Custom alias is already taken.")
    
    short_code = custom_alias if custom_alias else await generate_unique_short_code()
    link = Link(original_url=original_url, short_code=short_code, user_email=user.email if user else None, expires_at=expires_at)
    
    async for session in get_async_session(): 
        session.add(link)
        await session.commit()
        return {"short_code": short_code, "original_url": original_url}
    

# Создание короткой ссылки для незарегистрированных пользователей
@router.post("/links/anonymous/shorten")
# @limiter.limit("5/minute")
async def shorten_link_anonymous(
    request: Request,
    original_url: str,
    custom_alias: str = None,
    expires_at: datetime = None,
):
    async for session in get_async_session():
        if custom_alias:
            result = await session.execute(select(Link).filter(Link.custom_alias == custom_alias))
            if result.scalars().first():
                raise HTTPException(status_code=400, detail="Custom alias is already taken.")
    
    now = datetime.now()
    max_expiration = now + MAX_ANONYMOUS_LINK_LIFETIME
    
    if expires_at:
        if expires_at > max_expiration:
            raise HTTPException(
                status_code=400,
                detail=f"Maximum expiration time for anonymous links is {MAX_ANONYMOUS_LINK_LIFETIME.days} days. Register to get more."
            )
    else:
        expires_at = now + DEFAULT_ANONYMOUS_EXPIRATION
    
    short_code = custom_alias if custom_alias else await generate_unique_short_code()
    
    link = Link(
        original_url=original_url,
        short_code=short_code,
        user_email=None,
        expires_at=expires_at,
    )
    
    async for session in get_async_session():
        session.add(link)
        await session.commit()
        return {
            "short_code": short_code,
            "original_url": original_url,
            "expires_at": expires_at,
            "message": f"Anonymous link created. It will expire on {expires_at}."
        }

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
@router.get("/links/search/")
async def search_links(
    query: str,
    user: User = Depends(current_active_user),  
    exact_match: bool = False,
    page: int = 1,
    per_page: int = 10
):
    async for session in get_async_session():
        stmt = select(Link).where(Link.user_email == user.email)  
        
        if exact_match:
            # Точное совпадение
            stmt = stmt.where(Link.original_url == query)
        else:
            # Поиск по части URL (без учета регистра)
            stmt = stmt.where(Link.original_url.ilike(f"%{query}%"))
        
        # Пагинация
        stmt = stmt.offset((page - 1) * per_page).limit(per_page)
        
        result = await session.execute(stmt)
        links = result.scalars().all()
        
        if not links:
            raise HTTPException(status_code=404, detail="No links found matching your query")
        
        return [{
            "short_code": link.short_code,
            "original_url": link.original_url,
            "created_at": link.created_at,
        } for link in links]

    
# Изменение срока действия ссылки
@router.patch("/links/{short_code}/expiration")
async def update_expiration(
    short_code: str,
    new_expires_at: datetime,
    user: User = Depends(current_active_user)
):
    async for session in get_async_session():
        result = await session.execute(select(Link).filter(Link.short_code == short_code))
        link = result.scalars().first()
        
        if not link:
            raise HTTPException(status_code=404, detail="Link not found")
        
        if link.user_email != user.email:
            raise HTTPException(status_code=403, detail="Not your link")
        
        link.expires_at = new_expires_at
        await session.commit()
        return {"message": "Expiration updated"}
    

#Получение qr-кода для короткой ссылки
@router.get("/links/{short_code}/qrcode")
async def get_qrcode(short_code: str):
    async for session in get_async_session():
        result = await session.execute(select(Link).filter(Link.short_code == short_code))
        link = result.scalars().first()
        
        if not link:
            raise HTTPException(status_code=404, detail="Link not found")
        
        img = qrcode.make(link.original_url)
        buf = BytesIO()
        img.save(buf)
        buf.seek(0)
        
        return StreamingResponse(buf, media_type="image/png")
    

#Получение всех ссылок для пользователя
@router.get("/links/me/links")
async def get_user_links(
    user: User = Depends(current_active_user),
    page: int = 1,
    per_page: int = 10
):
    async for session in get_async_session():
        result = await session.execute(
            select(Link)
            .filter(Link.user_email == user.email)
            .offset((page - 1) * per_page)
            .limit(per_page)
        )
        links = result.scalars().all()
        return [{
            "short_code": link.short_code,
            "original_url": link.original_url,
            "created_at": link.created_at,
            "expires_at": link.expires_at
        } for link in links]
