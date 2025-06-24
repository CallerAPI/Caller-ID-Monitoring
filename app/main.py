from starlette.middleware.sessions import SessionMiddleware
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi import FastAPI, Request
from pathlib import Path
import os

from app.routers import api, auth
from app.api.v1.endpoints import phone_numbers
from app.db.base import Base, engine
from app.services.monitor import init_monitoring

app = FastAPI()

@app.on_event("startup")
async def startup():
    # Create database tables
    Base.metadata.create_all(bind=engine)
    # Initialize the monitoring scheduler
    init_monitoring()

# Add session middleware
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SECRET_KEY", "your-secret-key"),
    max_age=7 * 24 * 60 * 60  # 1 week
)

# Mount static files
static_dir = Path(__file__).parent / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Templates
templates_dir = Path(__file__).parent / "templates"
templates_dir.mkdir(exist_ok=True)
templates = Jinja2Templates(directory=str(templates_dir))

# API routers
app.include_router(api.router)
app.include_router(auth.router)
app.include_router(phone_numbers.router, prefix="/api/v1/phone-numbers", tags=["phone-numbers"])

@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "title": "Caller ID Monitor"
        }
    )

@app.get("/branded")
async def branded(request: Request):
    return templates.TemplateResponse(
        "branded.html",
        {
            "request": request,
            "title": "Branded Caller ID"
        }
    )

@app.get("/pricing")
async def pricing(request: Request):
    return templates.TemplateResponse(
        "pricing.html",
        {
            "request": request,
            "title": "Pricing"
        }
    )

@app.get("/settings")
async def settings(request: Request):
    return templates.TemplateResponse(
        "settings.html",
        {
            "request": request,
            "title": "Settings"
        }
    )
