from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from app.api.v1 import auth, dashboard, datasets, health, projects, requests, strategy
from app.core.config import settings


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="Central backend for DataForge",
)

# Login session stored in a signed cookie.
# For production: set https_only=True and serve the API over HTTPS.
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.session_secret_key,
    same_site="lax",
    https_only=False,
    max_age=60 * 60 * 24 * 7,  # 7 days
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(projects.router, prefix="/api/v1")
app.include_router(requests.router, prefix="/api/v1")
app.include_router(strategy.router, prefix="/api/v1")
app.include_router(datasets.router, prefix="/api/v1")
app.include_router(datasets.exports_router, prefix="/api/v1")
app.include_router(dashboard.router, prefix="/api/v1")
