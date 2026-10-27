from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.core.config import settings
from backend.app.core.database import init_db
from backend.app.api.routes import router as api_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Autonomous AI Software Engineering & Controlled Remediation Platform with Human-in-the-Loop Review",
    version="1.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    init_db()

@app.get("/health")
def health():
    return {"status": "ok", "app": settings.PROJECT_NAME, "version": "1.1.0"}

app.include_router(api_router, prefix=settings.API_PREFIX)
