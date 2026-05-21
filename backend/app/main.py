from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import create_tables
from .routers import auth, companies, dashboard

app = FastAPI(title="Novel CRM", version="0.1.0")

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

@app.get("/api/health")
async def health():
    return {"status": "ok"}

@app.on_event("startup")
async def startup():
    await create_tables()
