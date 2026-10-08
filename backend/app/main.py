from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

from .database import get_db
from .models import create_tables
from .models_ved import create_ved_tables
from .routers import auth, companies, dashboard, telegram, import_routes, availability, pipeline, tracking, communications, follow_ups, ai_search, research, ved_routes
import os
from .notifications import notifier
from .telegram_webhook import router as telegram_webhook_router, start_polling, stop_polling
from .scheduler import create_scheduler

app = FastAPI(title="Novel CRM", version="0.1.0")
scheduler = None

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(companies.router)
app.include_router(dashboard.router)
app.include_router(telegram.router)
app.include_router(telegram_webhook_router)
app.include_router(import_routes.router)
app.include_router(availability.router)
app.include_router(pipeline.router)
app.include_router(tracking.router)
app.include_router(communications.router)
app.include_router(follow_ups.router)
app.include_router(ai_search.router)
app.include_router(research.router)
app.include_router(ved_routes.router)

@app.get("/api/health")
async def health():
    return {"status": "ok"}

@app.on_event("startup")
async def startup():
    global scheduler
    await create_tables()
    await create_ved_tables()
    
    # Initialize notifier (skip Telegram connection check in webhook mode)
    tg_mode = os.getenv("TG_BOT_MODE", "webhook")
    if tg_mode == "polling":
        await notifier.initialize()
    else:
        # In webhook mode, just mark as initialized without connecting to TG API
        notifier._initialized = True
        logger = __import__('logging').getLogger(__name__)
        logger.info("Telegram notifier initialized in webhook mode (no TG API connection)")
    
    # Start polling only in polling mode
    if tg_mode == "polling":
        try:
            await start_polling()
        except Exception as e:
            print(f"Telegram polling init failed (non-fatal): {e}")
    else:
        # Ensure webhook is deleted if switching from polling
        try:
            from telegram import Bot
            bot = Bot(token=os.getenv("TG_BOT_TOKEN", ""))
            await bot.delete_webhook(drop_pending_updates=True)
        except Exception:
            pass
    
    scheduler = create_scheduler()
    scheduler.start()
    print("Scheduler started")

@app.on_event("shutdown")
async def shutdown():
    global scheduler
    await stop_polling()
    if scheduler:
        scheduler.shutdown(wait=False)

static_dir = Path("/app/static")
if static_dir.exists():
    app.mount("/assets", StaticFiles(directory=str(static_dir / "assets")), name="assets")

@app.get("/{full_path:path}")
async def serve_frontend(full_path: str):
    if full_path.startswith("api/"):
        return {"detail": "Not Found"}
    file_path = static_dir / full_path
    if file_path.exists() and file_path.is_file():
        return FileResponse(file_path)
    index_path = static_dir / "index.html"
    if index_path.exists():
        return FileResponse(index_path, headers={"Cache-Control": "no-cache"})
    return {"detail": "Not Found"}
