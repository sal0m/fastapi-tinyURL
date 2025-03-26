from fastapi import Depends, FastAPI

from src.auth.database import User
from src.auth.schemas import UserCreate, UserRead, UserUpdate
from src.auth.manager import auth_backend, current_active_user, fastapi_users
import uvicorn
from src.urls.router import router as links_router
from src.urls.router import limiter
from slowapi.middleware import SlowAPIMiddleware


app = FastAPI()


app.include_router(
    fastapi_users.get_auth_router(auth_backend), prefix="/auth/jwt", tags=["auth"]
)
app.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix="/auth",
    tags=["auth"],
)
app.include_router(
    fastapi_users.get_reset_password_router(),
    prefix="/auth",
    tags=["auth"],
)
app.include_router(
    fastapi_users.get_verify_router(UserRead),
    prefix="/auth",
    tags=["auth"],
)
app.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate),
    prefix="/users",
    tags=["users"],
)

# Роутер для управления короткими ссылками
app.add_middleware(SlowAPIMiddleware)
app.state.limiter = limiter
app.include_router(links_router, prefix="/api", tags=["links"])


@app.get("/authenticated-route")
async def authenticated_route(user: User = Depends(current_active_user)):
    return {"message": f"Hello {user.email}!"}

@app.get("/unprotected-route")
def unprotected_route():
    return f"Hello, anonym"


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", log_level="info")