# CRM MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Working CRM application with PostgreSQL database, FastAPI backend, React frontend, deployed on VPS at novel.maxnov.ru

**Architecture:** FastAPI serves both API and static React files on single port (3020). Docker Compose orchestrates PostgreSQL + Backend. Frontend built and served as static files by FastAPI.

**Tech Stack:** PostgreSQL 16, Python/FastAPI, SQLAlchemy 2.0 async, React 18 + Vite + TypeScript + Tailwind CSS, Docker Compose

**Server Constraints:**
- Server: 80.87.111.142, Ubuntu
- Host nginx on port 8443 (iptables 443→8443)
- Docker host networking BROKEN for ports <1024 (AppArmor)
- SSL via Let's Encrypt already configured
- Other projects on ports: 3003, 3004, 3010, 5678, 8081, 8082
- CRM will use port 3020 (isolated Docker network)

---

## Phase 1: Backend Foundation

### Task 1: Project Structure & Docker Setup

**Files:**
- Create: `backend/app/__init__.py`
- Create: `backend/app/main.py`
- Create: `backend/app/database.py`
- Create: `backend/requirements.txt`
- Create: `backend/Dockerfile`
- Create: `docker-compose.yml`
- Create: `.env.example`
- Create: `.gitignore`

- [ ] **Step 1: Create backend directory structure**

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py
│   └── database.py
├── requirements.txt
└── Dockerfile
```

- [ ] **Step 2: Create requirements.txt**

```txt
fastapi==0.115.6
uvicorn[standard]==0.34.0
sqlalchemy[asyncio]==2.0.36
asyncpg==0.30.0
pydantic==2.10.4
pydantic-settings==2.7.0
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.20
openpyxl==3.1.5
pandas==2.2.3
alembic==1.14.0
```

- [ ] **Step 3: Create backend Dockerfile**

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ./app ./app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 4: Create docker-compose.yml**

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:16-alpine
    container_name: novel_crm_postgres
    environment:
      POSTGRES_USER: ${DB_USER:-novel}
      POSTGRES_PASSWORD: ${DB_PASSWORD:-novel_secret}
      POSTGRES_DB: ${DB_NAME:-novel_crm}
    ports:
      - "5433:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    networks:
      - novel_net

  backend:
    build: ./backend
    container_name: novel_crm_backend
    environment:
      DB_URL: postgresql+asyncpg://${DB_USER:-novel}:${DB_PASSWORD:-novel_secret}@postgres:5432/${DB_NAME:-novel_crm}
      JWT_SECRET: ${JWT_SECRET:-change_me_in_production}
      JWT_ALGORITHM: HS256
      JWT_ACCESS_EXPIRE_MINUTES: 15
      JWT_REFRESH_EXPIRE_DAYS: 30
    ports:
      - "3020:8000"
    depends_on:
      - postgres
    networks:
      - novel_net

volumes:
  pgdata:

networks:
  novel_net:
    driver: bridge
```

- [ ] **Step 5: Create .env.example**

```env
DB_USER=novel
DB_PASSWORD=change_me_to_secure_password
DB_NAME=novel_crm
JWT_SECRET=change_me_to_long_random_string
```

- [ ] **Step 6: Create .gitignore**

```
.env
__pycache__/
*.pyc
node_modules/
dist/
build/
*.egg-info/
.venv/
```

- [ ] **Step 7: Create database.py**

```python
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    db_url: str = "postgresql+asyncpg://novel:novel_secret@localhost:5432/novel_crm"
    jwt_secret: str = "change_me_in_production"
    jwt_algorithm: str = "HS256"
    jwt_access_expire_minutes: int = 15
    jwt_refresh_expire_days: int = 30

    class Config:
        env_file = ".env"

settings = Settings()

engine = create_async_engine(settings.db_url, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_db():
    async with async_session() as session:
        yield session
```

- [ ] **Step 8: Create main.py (basic)**

```python
from fastapi import FastAPI

app = FastAPI(title="Novel CRM", version="0.1.0")

@app.get("/api/health")
async def health():
    return {"status": "ok"}
```

- [ ] **Step 9: Commit**

```bash
git add .
git commit -m "feat: initial project structure with Docker Compose"
```

---

### Task 2: Database Models

**Files:**
- Create: `backend/app/models.py`
- Create: `backend/app/schemas.py`

- [ ] **Step 1: Create SQLAlchemy models**

```python
from sqlalchemy import Column, String, Integer, BigInteger, Text, Boolean, DateTime, Date, ForeignKey, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
import enum

from .database import engine
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class UserRole(str, enum.Enum):
    admin = "admin"
    lead = "lead"
    manager = "manager"

class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    name = Column(String)
    role = Column(SAEnum(UserRole), nullable=False, default=UserRole.manager)
    tg_chat_id = Column(BigInteger, nullable=True)
    tg_username = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Company(Base):
    __tablename__ = "companies"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    inn = Column(String, unique=True, nullable=False, index=True)
    ogrn = Column(String, nullable=True)
    kpp = Column(String, nullable=True)
    org_form = Column(String, nullable=True)
    reg_date = Column(Date, nullable=True)
    name = Column(String, nullable=False, index=True)
    region = Column(String, nullable=True, index=True)
    address = Column(Text, nullable=True)
    tax_office = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    email = Column(String, nullable=True)
    website = Column(String, nullable=True)
    linkedin = Column(String, nullable=True)
    director = Column(String, nullable=True)
    director_title = Column(String, nullable=True)
    director_inn = Column(String, nullable=True)
    fin_director = Column(String, nullable=True)
    contact_person = Column(String, nullable=True)
    citizenship = Column(String, nullable=True)
    activity_main = Column(String, nullable=True)
    activity_code = Column(String, nullable=True)
    activity_other = Column(String, nullable=True)
    niche = Column(String, nullable=True)
    supply_subject = Column(String, nullable=True)
    revenue = Column(BigInteger, nullable=True)
    profit = Column(BigInteger, nullable=True)
    employees = Column(Integer, nullable=True)
    capital = Column(BigInteger, nullable=True)
    import_turnover = Column(String, nullable=True)
    export_turnover = Column(String, nullable=True)
    import_confirmed = Column(String, nullable=True)
    foreign_payments = Column(String, nullable=True)
    arbitrage = Column(String, nullable=True)
    licenses = Column(String, nullable=True)
    registries = Column(String, nullable=True)
    msp = Column(String, nullable=True)
    size = Column(String, nullable=True)
    segment = Column(String, nullable=True)
    priority = Column(String, nullable=True)
    focus_link = Column(String, nullable=True)
    source_orig = Column(String, nullable=True)
    branches = Column(String, nullable=True)
    comment_static = Column(Text, nullable=True)
    call_status = Column(String, default="new", index=True)
    next_call_date = Column(Date, nullable=True, index=True)
    assigned_to = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    call_count = Column(Integer, default=0)
    last_called_at = Column(DateTime(timezone=True), nullable=True)
    is_deleted = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class CallLog(Base):
    __tablename__ = "call_log"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    call_status = Column(String, nullable=False)
    notes = Column(Text, nullable=True)
    called_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

class AuditLog(Base):
    __tablename__ = "audit_log"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    field_name = Column(String, nullable=False)
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    changed_at = Column(DateTime(timezone=True), server_default=func.now())

async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
```

- [ ] **Step 2: Create Pydantic schemas**

```python
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime, date
import uuid
from enum import Enum

class UserRole(str, Enum):
    admin = "admin"
    lead = "lead"
    manager = "manager"

class UserCreate(BaseModel):
    email: str
    password: str
    name: str
    role: UserRole = UserRole.manager

class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    name: Optional[str]
    role: UserRole
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

class LoginRequest(BaseModel):
    email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class CompanyBase(BaseModel):
    name: str
    inn: str
    ogrn: Optional[str] = None
    kpp: Optional[str] = None
    org_form: Optional[str] = None
    reg_date: Optional[date] = None
    region: Optional[str] = None
    address: Optional[str] = None
    tax_office: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    linkedin: Optional[str] = None
    director: Optional[str] = None
    director_title: Optional[str] = None
    director_inn: Optional[str] = None
    fin_director: Optional[str] = None
    contact_person: Optional[str] = None
    citizenship: Optional[str] = None
    activity_main: Optional[str] = None
    activity_code: Optional[str] = None
    activity_other: Optional[str] = None
    niche: Optional[str] = None
    supply_subject: Optional[str] = None
    revenue: Optional[int] = None
    profit: Optional[int] = None
    employees: Optional[int] = None
    capital: Optional[int] = None
    import_turnover: Optional[str] = None
    export_turnover: Optional[str] = None
    import_confirmed: Optional[str] = None
    foreign_payments: Optional[str] = None
    arbitrage: Optional[str] = None
    licenses: Optional[str] = None
    registries: Optional[str] = None
    msp: Optional[str] = None
    size: Optional[str] = None
    segment: Optional[str] = None
    priority: Optional[str] = None
    focus_link: Optional[str] = None
    source_orig: Optional[str] = None
    branches: Optional[str] = None
    comment_static: Optional[str] = None
    call_status: Optional[str] = "new"
    next_call_date: Optional[date] = None
    assigned_to: Optional[uuid.UUID] = None

class CompanyCreate(CompanyBase):
    pass

class CompanyUpdate(BaseModel):
    name: Optional[str] = None
    inn: Optional[str] = None
    ogrn: Optional[str] = None
    kpp: Optional[str] = None
    org_form: Optional[str] = None
    reg_date: Optional[date] = None
    region: Optional[str] = None
    address: Optional[str] = None
    tax_office: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    linkedin: Optional[str] = None
    director: Optional[str] = None
    director_title: Optional[str] = None
    director_inn: Optional[str] = None
    fin_director: Optional[str] = None
    contact_person: Optional[str] = None
    citizenship: Optional[str] = None
    activity_main: Optional[str] = None
    activity_code: Optional[str] = None
    activity_other: Optional[str] = None
    niche: Optional[str] = None
    supply_subject: Optional[str] = None
    revenue: Optional[int] = None
    profit: Optional[int] = None
    employees: Optional[int] = None
    capital: Optional[int] = None
    import_turnover: Optional[str] = None
    export_turnover: Optional[str] = None
    import_confirmed: Optional[str] = None
    foreign_payments: Optional[str] = None
    arbitrage: Optional[str] = None
    licenses: Optional[str] = None
    registries: Optional[str] = None
    msp: Optional[str] = None
    size: Optional[str] = None
    segment: Optional[str] = None
    priority: Optional[str] = None
    focus_link: Optional[str] = None
    source_orig: Optional[str] = None
    branches: Optional[str] = None
    comment_static: Optional[str] = None
    call_status: Optional[str] = None
    next_call_date: Optional[date] = None
    assigned_to: Optional[uuid.UUID] = None

class CompanyResponse(CompanyBase):
    id: uuid.UUID
    call_count: int
    last_called_at: Optional[datetime]
    is_deleted: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class CompanyListResponse(BaseModel):
    items: list[CompanyResponse]
    total: int
    page: int
    page_size: int

class CallLogCreate(BaseModel):
    company_id: uuid.UUID
    call_status: str
    notes: Optional[str] = None

class CallLogResponse(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    user_id: uuid.UUID
    call_status: str
    notes: Optional[str]
    called_at: datetime
    
    class Config:
        from_attributes = True

class DashboardMetrics(BaseModel):
    total_companies: int
    new_companies: int
    in_progress: int
    interested: int
    meetings_scheduled: int
    refused: int
    calls_today: int
    tasks_today: int
    overdue: int

class AssignRequest(BaseModel):
    user_id: uuid.UUID
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/models.py backend/app/schemas.py
git commit -m "feat: add database models and Pydantic schemas"
```

---

### Task 3: Authentication (JWT)

**Files:**
- Create: `backend/app/auth.py`
- Create: `backend/app/routers/__init__.py`
- Create: `backend/app/routers/auth.py`

- [ ] **Step 1: Create auth.py**

```python
from datetime import datetime, timedelta
from typing import Optional
from passlib.context import CryptContext
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from .database import get_db, settings
from .models import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.jwt_access_expire_minutes))
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)

def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.jwt_refresh_expire_days)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    try:
        payload = jwt.decode(credentials.credentials, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user

async def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role not in ["admin"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return user

async def require_admin_or_lead(user: User = Depends(get_current_user)) -> User:
    if user.role not in ["admin", "lead"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin or Lead access required")
    return user
```

- [ ] **Step 2: Create auth router**

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..database import get_db
from ..models import User
from ..schemas import LoginRequest, TokenResponse, UserCreate, UserResponse
from ..auth import hash_password, verify_password, create_access_token, create_refresh_token, get_current_user, require_admin, require_admin_or_lead

router = APIRouter(prefix="/api/auth", tags=["auth"])

@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == request.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account deactivated")
    
    return TokenResponse(
        access_token=create_access_token({"sub": str(user.id)}),
        refresh_token=create_refresh_token({"sub": str(user.id)})
    )

@router.post("/register", response_model=UserResponse)
async def register(
    request: UserCreate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(User).where(User.email == request.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    
    user = User(
        email=request.email,
        password_hash=hash_password(request.password),
        name=request.name,
        role=request.role
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user
```

- [ ] **Step 3: Update main.py to include router**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import create_tables
from .routers import auth

app = FastAPI(title="Novel CRM", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)

@app.get("/api/health")
async def health():
    return {"status": "ok"}

@app.on_event("startup")
async def startup():
    await create_tables()
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/auth.py backend/app/routers/ backend/app/main.py
git commit -m "feat: add JWT authentication"
```

---

### Task 4: Companies API

**Files:**
- Create: `backend/app/routers/companies.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Create companies router**

```python
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from typing import Optional
import uuid

from ..database import get_db
from ..models import User, Company, CallLog, AuditLog
from ..schemas import CompanyCreate, CompanyUpdate, CompanyResponse, CompanyListResponse, CallLogCreate, CallLogResponse, AssignRequest
from ..auth import get_current_user, require_admin, require_admin_or_lead

router = APIRouter(prefix="/api/companies", tags=["companies"])

@router.get("", response_model=CompanyListResponse)
async def list_companies(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    search: Optional[str] = None,
    region: Optional[str] = None,
    status: Optional[str] = None,
    assigned_to: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    query = select(Company).where(Company.is_deleted == False)
    count_query = select(func.count()).select_from(Company).where(Company.is_deleted == False)
    
    if current_user.role == "manager":
        query = query.where(Company.assigned_to == current_user.id)
        count_query = count_query.where(Company.assigned_to == current_user.id)
    
    if search:
        search_filter = or_(
            Company.name.ilike(f"%{search}%"),
            Company.inn.ilike(f"%{search}%"),
            Company.phone.ilike(f"%{search}%"),
            Company.email.ilike(f"%{search}%")
        )
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)
    
    if region:
        query = query.where(Company.region == region)
        count_query = count_query.where(Company.region == region)
    
    if status:
        query = query.where(Company.call_status == status)
        count_query = count_query.where(Company.call_status == status)
    
    if assigned_to:
        query = query.where(Company.assigned_to == assigned_to)
        count_query = count_query.where(Company.assigned_to == assigned_to)
    
    query = query.order_by(Company.next_call_date.asc().nulls_last()).offset((page - 1) * page_size).limit(page_size)
    
    result = await db.execute(query)
    companies = result.scalars().all()
    
    count_result = await db.execute(count_query)
    total = count_result.scalar()
    
    return CompanyListResponse(
        items=[CompanyResponse.model_validate(c) for c in companies],
        total=total,
        page=page,
        page_size=page_size
    )

@router.get("/{company_id}", response_model=CompanyResponse)
async def get_company(
    company_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Company).where(Company.id == company_id, Company.is_deleted == False))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    if current_user.role == "manager" and company.assigned_to != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    return company

@router.post("", response_model=CompanyResponse)
async def create_company(
    request: CompanyCreate,
    current_user: User = Depends(require_admin_or_lead),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Company).where(Company.inn == request.inn))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Company with this INN already exists")
    
    company = Company(**request.model_dump())
    db.add(company)
    await db.commit()
    await db.refresh(company)
    return company

@router.patch("/{company_id}", response_model=CompanyResponse)
async def update_company(
    company_id: uuid.UUID,
    request: CompanyUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Company).where(Company.id == company_id, Company.is_deleted == False))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    if current_user.role == "manager" and company.assigned_to != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        old_value = getattr(company, field)
        setattr(company, field, value)
        audit = AuditLog(
            user_id=current_user.id,
            company_id=company.id,
            field_name=field,
            old_value=str(old_value) if old_value else None,
            new_value=str(value) if value else None
        )
        db.add(audit)
    
    await db.commit()
    await db.refresh(company)
    return company

@router.post("/{company_id}/call", response_model=CallLogResponse)
async def log_call(
    company_id: uuid.UUID,
    request: CallLogCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Company).where(Company.id == company_id, Company.is_deleted == False))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    company.call_count += 1
    company.call_status = request.call_status
    company.last_called_at = func.now()
    
    call_log = CallLog(
        company_id=company_id,
        user_id=current_user.id,
        call_status=request.call_status,
        notes=request.notes
    )
    db.add(call_log)
    await db.commit()
    await db.refresh(call_log)
    return call_log

@router.patch("/{company_id}/assign", response_model=CompanyResponse)
async def assign_company(
    company_id: uuid.UUID,
    request: AssignRequest,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Company).where(Company.id == company_id, Company.is_deleted == False))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    company.assigned_to = request.user_id
    await db.commit()
    await db.refresh(company)
    return company

@router.delete("/{company_id}")
async def delete_company(
    company_id: uuid.UUID,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Company).where(Company.id == company_id, Company.is_deleted == False))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    company.is_deleted = True
    await db.commit()
    return {"message": "Company deleted"}
```

- [ ] **Step 2: Update main.py to include companies router**

```python
from .routers import auth, companies

app.include_router(auth.router)
app.include_router(companies.router)
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/routers/companies.py backend/app/main.py
git commit -m "feat: add companies CRUD API"
```

---

### Task 5: Dashboard & Excel Import

**Files:**
- Create: `backend/app/routers/dashboard.py`
- Create: `backend/migrate.py`
- Create: `backend/create_admin.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Create dashboard router**

```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import date, datetime

from ..database import get_db
from ..models import User, Company, CallLog
from ..schemas import DashboardMetrics
from ..auth import get_current_user, require_admin_or_lead

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

@router.get("/me", response_model=DashboardMetrics)
async def my_dashboard(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    base_query = select(Company).where(Company.is_deleted == False)
    if current_user.role == "manager":
        base_query = base_query.where(Company.assigned_to == current_user.id)
    
    result = await db.execute(base_query)
    companies = result.scalars().all()
    
    today = date.today()
    tasks_today = sum(1 for c in companies if c.next_call_date == today)
    overdue = sum(1 for c in companies if c.next_call_date and c.next_call_date < today)
    
    calls_today_result = await db.execute(
        select(func.count(CallLog.id)).where(
            CallLog.user_id == current_user.id,
            func.date(CallLog.called_at) == today
        )
    )
    calls_today = calls_today_result.scalar() or 0
    
    return DashboardMetrics(
        total_companies=len(companies),
        new_companies=sum(1 for c in companies if c.call_status == "new"),
        in_progress=sum(1 for c in companies if c.call_status == "in_progress"),
        interested=sum(1 for c in companies if c.call_status == "interested"),
        meetings_scheduled=sum(1 for c in companies if c.call_status == "meeting"),
        refused=sum(1 for c in companies if c.call_status == "refused"),
        calls_today=calls_today,
        tasks_today=tasks_today,
        overdue=overdue
    )
```

- [ ] **Step 2: Create migrate.py for Excel import**

```python
import asyncio
import pandas as pd
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.database import async_session, engine
from app.models import Base, Company

async def normalize_row(row: dict) -> dict:
    """Normalize Excel row to Company fields"""
    def get_first(*keys):
        for key in keys:
            val = row.get(key)
            if val and str(val).strip():
                return str(val).strip()
        return None
    
    return {
        "name": get_first("Компания", "Наименование", "Наименование клиента", "ФИО"),
        "inn": get_first("ИНН"),
        "ogrn": get_first("ОГРН"),
        "kpp": get_first("КПП"),
        "region": get_first("Регион регистрации", "Регион"),
        "address": get_first("Адрес", "Юр. адрес"),
        "phone": get_first("Телефон"),
        "email": get_first("Email"),
        "website": get_first("Сайт", "Website"),
        "director": get_first("Руководитель", "Директор"),
        "activity_main": get_first("Основной вид деятельности"),
        "activity_code": get_first("Код ОКВЭД"),
        "revenue": int(float(get_first("Выручка", "Выручка 2022", "Выручка RUB"))) if get_first("Выручка", "Выручка 2022", "Выручка RUB") else None,
        "employees": int(float(get_first("Численность сотрудников"))) if get_first("Численность сотрудников") else None,
    }

async def migrate_excel(file_path: str):
    df = pd.read_excel(file_path)
    print(f"Read {len(df)} rows from Excel")
    
    added = 0
    updated = 0
    skipped = 0
    
    async with async_session() as session:
        for idx, row in df.iterrows():
            data = await normalize_row(row.to_dict())
            if not data.get("inn") or not data.get("name"):
                skipped += 1
                continue
            
            from sqlalchemy import select
            result = await session.execute(select(Company).where(Company.inn == data["inn"]))
            existing = result.scalar_one_or_none()
            
            if existing:
                for key, value in data.items():
                    if value and not getattr(existing, key):
                        setattr(existing, key, value)
                updated += 1
            else:
                company = Company(**{k: v for k, v in data.items() if v})
                session.add(company)
                added += 1
            
            if (idx + 1) % 500 == 0:
                await session.commit()
                print(f"Processed {idx + 1} rows...")
        
        await session.commit()
    
    print(f"\nMigration complete:")
    print(f"  Added: {added}")
    print(f"  Updated: {updated}")
    print(f"  Skipped: {skipped}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python migrate.py <excel_file.xlsx>")
        sys.exit(1)
    asyncio.run(migrate_excel(sys.argv[1]))
```

- [ ] **Step 3: Create create_admin.py**

```python
import asyncio
import sys
from pathlib import Path
from getpass import getpass

sys.path.insert(0, str(Path(__file__).parent))

from app.database import async_session
from app.models import User
from app.auth import hash_password

async def create_admin():
    email = input("Admin email: ")
    password = getpass("Admin password: ")
    name = input("Admin name: ")
    
    async with async_session() as session:
        from sqlalchemy import select
        result = await session.execute(select(User).where(User.email == email))
        if result.scalar_one_or_none():
            print("User already exists")
            return
        
        user = User(
            email=email,
            password_hash=hash_password(password),
            name=name,
            role="admin"
        )
        session.add(user)
        await session.commit()
        print(f"Admin user created: {email}")

if __name__ == "__main__":
    asyncio.run(create_admin())
```

- [ ] **Step 4: Update main.py**

```python
from .routers import auth, companies, dashboard

app.include_router(auth.router)
app.include_router(companies.router)
app.include_router(dashboard.router)
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers/dashboard.py backend/migrate.py backend/create_admin.py backend/app/main.py
git commit -m "feat: add dashboard API and Excel import script"
```

---

## Phase 2: Frontend

### Task 6: React + Vite Setup

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/tsconfig.json`
- Create: `frontend/tsconfig.node.json`
- Create: `frontend/index.html`
- Create: `frontend/tailwind.config.js`
- Create: `frontend/postcss.config.js`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/index.css`

- [ ] **Step 1: Create package.json**

```json
{
  "name": "novel-crm-frontend",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "@tanstack/react-table": "^8.20.5",
    "@tanstack/react-virtual": "^3.10.9",
    "axios": "^1.7.9",
    "date-fns": "^4.1.0",
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-router-dom": "^7.0.2",
    "zustand": "^5.0.2"
  },
  "devDependencies": {
    "@types/react": "^18.3.12",
    "@types/react-dom": "^18.3.1",
    "@vitejs/plugin-react": "^4.3.4",
    "autoprefixer": "^10.4.20",
    "postcss": "^8.4.49",
    "tailwindcss": "^3.4.16",
    "typescript": "^5.7.2",
    "vite": "^6.0.3"
  }
}
```

- [ ] **Step 2: Create vite.config.ts**

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': 'http://localhost:3020'
    }
  }
})
```

- [ ] **Step 3: Create tsconfig.json**

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "isolatedModules": true,
    "moduleDetection": "force",
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "forceConsistentCasingInFileNames": true
  },
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

- [ ] **Step 4: Create tsconfig.node.json**

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["ES2023"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "isolatedModules": true,
    "moduleDetection": "force",
    "noEmit": true,
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true
  },
  "include": ["vite.config.ts"]
}
```

- [ ] **Step 5: Create index.html**

```html
<!DOCTYPE html>
<html lang="ru">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Novel CRM</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 6: Create tailwind.config.js**

```javascript
/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        bg: '#0F1117',
        surface: '#1A1D27',
        surfaceHover: '#222536',
        accent: '#4F6EF7',
        text: '#E2E8F0',
        muted: '#8892A4',
        success: '#22C55E',
        warning: '#F59E0B',
        error: '#EF4444',
        info: '#3B82F6',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      }
    },
  },
  plugins: [],
}
```

- [ ] **Step 7: Create postcss.config.js**

```javascript
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
```

- [ ] **Step 8: Create src/index.css**

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

body {
  @apply bg-bg text-text font-sans;
}

::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}

::-webkit-scrollbar-track {
  @apply bg-surface;
}

::-webkit-scrollbar-thumb {
  @apply bg-muted/30 rounded;
}

::-webkit-scrollbar-thumb:hover {
  @apply bg-muted/50;
}
```

- [ ] **Step 9: Create src/main.tsx**

```typescript
import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
```

- [ ] **Step 10: Create src/App.tsx (basic)**

```typescript
import { BrowserRouter } from 'react-router-dom'
import { AuthProvider } from './store/auth'
import AppRoutes from './routes'

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </BrowserRouter>
  )
}
```

- [ ] **Step 11: Commit**

```bash
git add frontend/
git commit -m "feat: initialize React + Vite + TypeScript + Tailwind frontend"
```

---

### Task 7: Auth Store & API Client

**Files:**
- Create: `frontend/src/api/client.ts`
- Create: `frontend/src/store/auth.ts`
- Create: `frontend/src/routes.tsx`
- Create: `frontend/src/pages/Login.tsx`

- [ ] **Step 1: Create API client**

```typescript
import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export default api
```

- [ ] **Step 2: Create auth store**

```typescript
import { create } from 'zustand'
import api from '../api/client'

interface User {
  id: string
  email: string
  name: string | null
  role: 'admin' | 'lead' | 'manager'
  is_active: boolean
  created_at: string
}

interface AuthState {
  user: User | null
  token: string | null
  isLoading: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => void
  fetchUser: () => Promise<void>
}

export const useAuth = create<AuthState>((set) => ({
  user: null,
  token: localStorage.getItem('access_token'),
  isLoading: false,
  
  login: async (email: string, password: string) => {
    set({ isLoading: true })
    try {
      const { data } = await api.post('/auth/login', { email, password })
      localStorage.setItem('access_token', data.access_token)
      set({ token: data.access_token })
      await fetchUser()
    } finally {
      set({ isLoading: false })
    }
  },
  
  logout: () => {
    localStorage.removeItem('access_token')
    set({ user: null, token: null })
  },
  
  fetchUser: async () => {
    try {
      const { data } = await api.get('/auth/me')
      set({ user: data })
    } catch {
      localStorage.removeItem('access_token')
      set({ user: null, token: null })
    }
  },
}))

export const AuthProvider = ({ children }: { children: React.ReactNode }) => {
  const fetchUser = useAuth((s) => s.fetchUser)
  const token = useAuth((s) => s.token)
  
  React.useEffect(() => {
    if (token) fetchUser()
  }, [token, fetchUser])
  
  return children
}
```

- [ ] **Step 3: Create routes**

```typescript
import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from './store/auth'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const token = useAuth((s) => s.token)
  return token ? <>{children}</> : <Navigate to="/login" />
}

export default function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/" element={
        <ProtectedRoute>
          <Dashboard />
        </ProtectedRoute>
      } />
    </Routes>
  )
}
```

- [ ] **Step 4: Create Login page**

```typescript
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../store/auth'

export default function Login() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const login = useAuth((s) => s.login)
  const isLoading = useAuth((s) => s.isLoading)
  const navigate = useNavigate()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    try {
      await login(email, password)
      navigate('/')
    } catch {
      setError('Неверный email или пароль')
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-bg">
      <div className="w-full max-w-md p-8 bg-surface rounded-xl shadow-xl">
        <h1 className="text-2xl font-bold text-center mb-8">Novel CRM</h1>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-muted mb-1">Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full px-4 py-2 bg-bg border border-muted/20 rounded-lg focus:outline-none focus:ring-2 focus:ring-accent"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-muted mb-1">Пароль</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-4 py-2 bg-bg border border-muted/20 rounded-lg focus:outline-none focus:ring-2 focus:ring-accent"
              required
            />
          </div>
          {error && <p className="text-error text-sm">{error}</p>}
          <button
            type="submit"
            disabled={isLoading}
            className="w-full py-2 bg-accent hover:bg-accent/90 text-white font-medium rounded-lg transition-colors disabled:opacity-50"
          >
            {isLoading ? 'Вход...' : 'Войти'}
          </button>
        </form>
      </div>
    </div>
  )
}
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/api/ frontend/src/store/auth.ts frontend/src/routes.tsx frontend/src/pages/Login.tsx
git commit -m "feat: add authentication UI and API client"
```

---

### Task 8: Dashboard & Company Table

**Files:**
- Create: `frontend/src/pages/Dashboard.tsx`
- Create: `frontend/src/components/CompanyTable.tsx`
- Create: `frontend/src/components/CompanyCard.tsx`
- Create: `frontend/src/components/StatusBadge.tsx`

- [ ] **Step 1: Create StatusBadge component**

```typescript
const statusColors: Record<string, string> = {
  new: 'bg-gray-500/20 text-gray-400',
  'not_reached': 'bg-orange-500/20 text-orange-400',
  'no_answer': 'bg-red-500/20 text-red-400',
  'callback': 'bg-blue-500/20 text-blue-400',
  'in_progress': 'bg-yellow-500/20 text-yellow-400',
  interested: 'bg-green-500/20 text-green-400',
  meeting: 'bg-purple-500/20 text-purple-400',
  refused: 'bg-gray-600/20 text-gray-500',
}

const statusLabels: Record<string, string> = {
  new: 'Новый',
  not_reached: 'Не дозвонился',
  no_answer: 'Не отвечает',
  callback: 'Перезвонить',
  in_progress: 'В работе',
  interested: 'Заинтересован',
  meeting: 'Встреча назначена',
  refused: 'Отказ',
}

export default function StatusBadge({ status }: { status: string }) {
  return (
    <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${statusColors[status] || statusColors.new}`}>
      {statusLabels[status] || status}
    </span>
  )
}
```

- [ ] **Step 2: Create CompanyTable component**

```typescript
import { useState, useEffect } from 'react'
import { useVirtualizer } from '@tanstack/react-virtual'
import { useRef } from 'react'
import api from '../api/client'
import StatusBadge from './StatusBadge'
import CompanyCard from './CompanyCard'

interface Company {
  id: string
  name: string
  inn: string
  region: string | null
  phone: string | null
  website: string | null
  call_status: string
  call_count: number
  next_call_date: string | null
  assigned_to: string | null
  revenue: number | null
}

export default function CompanyTable() {
  const [companies, setCompanies] = useState<Company[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [selectedCompany, setSelectedCompany] = useState<Company | null>(null)
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)

  useEffect(() => {
    const fetchCompanies = async () => {
      try {
        const { data } = await api.get('/companies', {
          params: { page, page_size: 50, search }
        })
        setCompanies(data.items)
        setTotal(data.total)
      } finally {
        setLoading(false)
      }
    }
    fetchCompanies()
  }, [page, search])

  const parentRef = useRef<HTMLDivElement>(null)
  const virtualizer = useVirtualizer({
    count: companies.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 40,
    overscan: 5,
  })

  const formatRevenue = (val: number | null) => {
    if (!val) return '—'
    if (val >= 1e9) return `${(val / 1e9).toFixed(1)} млрд`
    if (val >= 1e6) return `${(val / 1e6).toFixed(0)} млн`
    if (val >= 1e3) return `${(val / 1e3).toFixed(0)} тыс`
    return val.toString()
  }

  if (loading) return <div className="flex items-center justify-center h-64">Загрузка...</div>

  return (
    <div className="flex h-full">
      <div className="flex-1 flex flex-col">
        <div className="p-4 border-b border-muted/10">
          <input
            type="text"
            placeholder="Поиск по названию, ИНН, телефону..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full px-4 py-2 bg-bg border border-muted/20 rounded-lg focus:outline-none focus:ring-2 focus:ring-accent"
          />
        </div>
        
        <div className="grid grid-cols-12 gap-2 px-4 py-2 text-xs font-medium text-muted border-b border-muted/10">
          <div className="col-span-3">Компания</div>
          <div className="col-span-1">ИНН</div>
          <div className="col-span-1">Регион</div>
          <div className="col-span-2">Деятельность</div>
          <div className="col-span-1">Выручка</div>
          <div className="col-span-1">Телефон</div>
          <div className="col-span-1">Попыток</div>
          <div className="col-span-1">Статус</div>
          <div className="col-span-1">Перезвонить</div>
        </div>

        <div ref={parentRef} className="flex-1 overflow-auto">
          <div style={{ height: `${virtualizer.getTotalSize()}px`, position: 'relative' }}>
            {virtualizer.getVirtualItems().map((virtualRow) => {
              const company = companies[virtualRow.index]
              return (
                <div
                  key={company.id}
                  ref={virtualizer.measureElement}
                  data-index={virtualRow.index}
                  onClick={() => setSelectedCompany(company)}
                  className="absolute inset-x-0 grid grid-cols-12 gap-2 px-4 items-center h-10 hover:bg-surfaceHover cursor-pointer border-b border-muted/5"
                  style={{ transform: `translateY(${virtualRow.start}px)` }}
                >
                  <div className="col-span-3 font-medium truncate">{company.name}</div>
                  <div className="col-span-1 font-mono text-xs truncate">{company.inn}</div>
                  <div className="col-span-1 text-muted truncate">{company.region || '—'}</div>
                  <div className="col-span-2 text-muted truncate">{company.activity_main || '—'}</div>
                  <div className="col-span-1">{formatRevenue(company.revenue)}</div>
                  <div className="col-span-1">
                    {company.phone ? (
                      <a href={`tel:${company.phone}`} className="text-accent hover:underline">{company.phone}</a>
                    ) : '—'}
                  </div>
                  <div className="col-span-1 text-center">{company.call_count}</div>
                  <div className="col-span-1"><StatusBadge status={company.call_status} /></div>
                  <div className="col-span-1 text-xs">
                    {company.next_call_date ? (
                      <span className={new Date(company.next_call_date) < new Date() ? 'text-error' : ''}>
                        {company.next_call_date}
                      </span>
                    ) : '—'}
                  </div>
                </div>
              )
            })}
          </div>
        </div>

        <div className="p-3 border-t border-muted/10 flex items-center justify-between text-sm text-muted">
          <span>Всего: {total}</span>
          <div className="flex gap-2">
            <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1} className="px-3 py-1 bg-surface rounded disabled:opacity-50">
              Назад
            </button>
            <span className="px-3 py-1">Стр. {page}</span>
            <button onClick={() => setPage(p => p + 1)} disabled={page * 50 >= total} className="px-3 py-1 bg-surface rounded disabled:opacity-50">
              Вперёд
            </button>
          </div>
        </div>
      </div>

      {selectedCompany && (
        <CompanyCard company={selectedCompany} onClose={() => setSelectedCompany(null)} />
      )}
    </div>
  )
}
```

- [ ] **Step 3: Create CompanyCard component**

```typescript
import { useState } from 'react'
import api from '../api/client'

interface Company {
  id: string
  name: string
  inn: string
  phone: string | null
  email: string | null
  website: string | null
  region: string | null
  call_status: string
  call_count: number
  comment_static: string | null
  next_call_date: string | null
}

const statuses = [
  { value: 'new', label: 'Новый', color: 'bg-gray-500' },
  { value: 'not_reached', label: 'Не дозвонился', color: 'bg-orange-500' },
  { value: 'no_answer', label: 'Не отвечает', color: 'bg-red-500' },
  { value: 'callback', label: 'Перезвонить', color: 'bg-blue-500' },
  { value: 'in_progress', label: 'В работе', color: 'bg-yellow-500' },
  { value: 'interested', label: 'Заинтересован', color: 'bg-green-500' },
  { value: 'meeting', label: 'Встреча назначена', color: 'bg-purple-500' },
  { value: 'refused', label: 'Отказ', color: 'bg-gray-600' },
]

export default function CompanyCard({ company, onClose }: { company: Company; onClose: () => void }) {
  const [notes, setNotes] = useState('')
  const [selectedStatus, setSelectedStatus] = useState(company.call_status)
  const [nextCallDate, setNextCallDate] = useState(company.next_call_date || '')

  const handleSaveCall = async () => {
    await api.post(`/companies/${company.id}/call`, {
      call_status: selectedStatus,
      notes,
    })
    setNotes('')
    window.location.reload()
  }

  return (
    <div className="w-[480px] bg-surface border-l border-muted/10 overflow-y-auto">
      <div className="sticky top-0 bg-surface border-b border-muted/10 p-4">
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-lg font-bold">{company.name}</h2>
          <button onClick={onClose} className="text-muted hover:text-text">✕</button>
        </div>
        <p className="text-sm text-muted font-mono">ИНН: {company.inn}</p>
        {company.region && <p className="text-sm text-muted">Регион: {company.region}</p>}
        
        <div className="mt-3 flex gap-2">
          {company.phone && (
            <a href={`tel:${company.phone}`} className="px-3 py-1 bg-accent text-white text-sm rounded-lg hover:bg-accent/90">
              📞 {company.phone}
            </a>
          )}
          {company.email && (
            <a href={`mailto:${company.email}`} className="px-3 py-1 bg-surfaceHover text-sm rounded-lg hover:bg-muted/20">
              ✉️ Email
            </a>
          )}
          {company.website && (
            <a href={company.website} target="_blank" rel="noopener" className="px-3 py-1 bg-surfaceHover text-sm rounded-lg hover:bg-muted/20">
              🌐 Сайт
            </a>
          )}
        </div>
      </div>

      <div className="p-4 border-b border-muted/10">
        <h3 className="text-sm font-medium mb-2">Статус</h3>
        <div className="flex flex-wrap gap-2">
          {statuses.map((s) => (
            <button
              key={s.value}
              onClick={() => setSelectedStatus(s.value)}
              className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-colors ${
                selectedStatus === s.value
                  ? `${s.color} text-white`
                  : 'bg-bg text-muted hover:text-text'
              }`}
            >
              {s.label}
            </button>
          ))}
        </div>
      </div>

      <div className="p-4 border-b border-muted/10">
        <h3 className="text-sm font-medium mb-2">Комментарий к звонку</h3>
        <textarea
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          className="w-full h-24 px-3 py-2 bg-bg border border-muted/20 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-accent"
          placeholder="Результат звонка..."
        />
      </div>

      <div className="p-4 border-b border-muted/10">
        <h3 className="text-sm font-medium mb-2">Следующий звонок</h3>
        <input
          type="date"
          value={nextCallDate}
          onChange={(e) => setNextCallDate(e.target.value)}
          className="w-full px-3 py-2 bg-bg border border-muted/20 rounded-lg focus:outline-none focus:ring-2 focus:ring-accent"
        />
        <div className="flex gap-2 mt-2">
          <button onClick={() => {
            const d = new Date()
            d.setDate(d.getDate() + 1)
            setNextCallDate(d.toISOString().split('T')[0])
          }} className="px-2 py-1 text-xs bg-surfaceHover rounded hover:bg-muted/20">+1 день</button>
          <button onClick={() => {
            const d = new Date()
            d.setDate(d.getDate() + 3)
            setNextCallDate(d.toISOString().split('T')[0])
          }} className="px-2 py-1 text-xs bg-surfaceHover rounded hover:bg-muted/20">+3 дня</button>
          <button onClick={() => {
            const d = new Date()
            d.setDate(d.getDate() + 7)
            setNextCallDate(d.toISOString().split('T')[0])
          }} className="px-2 py-1 text-xs bg-surfaceHover rounded hover:bg-muted/20">+неделя</button>
        </div>
      </div>

      <div className="p-4">
        <button
          onClick={handleSaveCall}
          className="w-full py-2 bg-accent hover:bg-accent/90 text-white font-medium rounded-lg transition-colors"
        >
          Сохранить звонок
        </button>
      </div>
    </div>
  )
}
```

- [ ] **Step 4: Create Dashboard page**

```typescript
import { useEffect, useState } from 'react'
import { useAuth } from '../store/auth'
import api from '../api/client'
import CompanyTable from '../components/CompanyTable'

interface Metrics {
  total_companies: number
  new_companies: number
  in_progress: number
  interested: number
  meetings_scheduled: number
  refused: number
  calls_today: number
  tasks_today: number
  overdue: number
}

export default function Dashboard() {
  const user = useAuth((s) => s.user)
  const logout = useAuth((s) => s.logout)
  const [metrics, setMetrics] = useState<Metrics | null>(null)

  useEffect(() => {
    api.get('/dashboard/me').then(({ data }) => setMetrics(data))
  }, [])

  return (
    <div className="h-screen flex flex-col bg-bg">
      <header className="flex items-center justify-between px-6 py-3 bg-surface border-b border-muted/10">
        <h1 className="text-xl font-bold">Novel CRM</h1>
        <div className="flex items-center gap-4">
          <span className="text-sm text-muted">{user?.name || user?.email}</span>
          <button onClick={logout} className="text-sm text-muted hover:text-text">Выйти</button>
        </div>
      </header>

      {metrics && (
        <div className="grid grid-cols-4 gap-4 p-4">
          <MetricCard label="Задач на сегодня" value={metrics.tasks_today} color="accent" />
          <MetricCard label="Просрочено" value={metrics.overdue} color="error" />
          <MetricCard label="Звонков сегодня" value={metrics.calls_today} color="success" />
          <MetricCard label="Всего компаний" value={metrics.total_companies} color="muted" />
        </div>
      )}

      <div className="flex-1 overflow-hidden">
        <CompanyTable />
      </div>
    </div>
  )
}

function MetricCard({ label, value, color }: { label: string; value: number; color: string }) {
  const colorClasses: Record<string, string> = {
    accent: 'border-accent/30',
    error: 'border-error/30',
    success: 'border-success/30',
    muted: 'border-muted/20',
  }
  const valueColors: Record<string, string> = {
    accent: 'text-accent',
    error: 'text-error',
    success: 'text-success',
    muted: 'text-text',
  }
  
  return (
    <div className={`p-4 bg-surface rounded-xl border ${colorClasses[color]}`}>
      <p className="text-sm text-muted">{label}</p>
      <p className={`text-2xl font-bold ${valueColors[color]}`}>{value}</p>
    </div>
  )
}
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ frontend/src/pages/Dashboard.tsx
git commit -m "feat: add dashboard, company table with virtualization, and company card"
```

---

## Phase 3: Build & Deploy

### Task 9: Frontend Dockerfile & Build Integration

**Files:**
- Create: `frontend/Dockerfile`
- Modify: `backend/Dockerfile`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Create frontend Dockerfile**

```dockerfile
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

- [ ] **Step 2: Create frontend/nginx.conf**

```nginx
server {
    listen 80;
    server_name _;
    root /usr/share/nginx/html;
    index index.html;
    
    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

- [ ] **Step 3: Update backend Dockerfile to serve static files**

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ./app ./app
COPY --from=frontend-builder /app/dist ./app/static

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 4: Update main.py to serve static files**

```python
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

# Add after routers
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/assets", StaticFiles(directory=str(static_dir / "assets")), name="assets")

@app.get("/{full_path:path}")
async def serve_frontend(full_path: str):
    """Serve React SPA for all non-API routes"""
    file_path = static_dir / full_path
    if file_path.exists() and file_path.is_file():
        return FileResponse(file_path)
    index_path = static_dir / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return {"error": "Not found"}
```

- [ ] **Step 5: Update docker-compose.yml for multi-stage build**

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:16-alpine
    container_name: novel_crm_postgres
    environment:
      POSTGRES_USER: ${DB_USER:-novel}
      POSTGRES_PASSWORD: ${DB_PASSWORD:-novel_secret}
      POSTGRES_DB: ${DB_NAME:-novel_crm}
    ports:
      - "5433:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    networks:
      - novel_net

  backend:
    build: 
      context: ./backend
      dockerfile: Dockerfile
    container_name: novel_crm_backend
    environment:
      DB_URL: postgresql+asyncpg://${DB_USER:-novel}:${DB_PASSWORD:-novel_secret}@postgres:5432/${DB_NAME:-novel_crm}
      JWT_SECRET: ${JWT_SECRET:-change_me_in_production}
      JWT_ALGORITHM: HS256
      JWT_ACCESS_EXPIRE_MINUTES: 15
      JWT_REFRESH_EXPIRE_DAYS: 30
    ports:
      - "3020:8000"
    depends_on:
      - postgres
    networks:
      - novel_net

volumes:
  pgdata:

networks:
  novel_net:
    driver: bridge
```

- [ ] **Step 6: Commit**

```bash
git add frontend/Dockerfile frontend/nginx.conf backend/Dockerfile backend/app/main.py docker-compose.yml
git commit -m "feat: add Docker build for frontend served by FastAPI"
```

---

### Task 10: Deploy Scripts & Server Config

**Files:**
- Create: `deploy/server-setup.sh`
- Create: `deploy/nginx-novel.conf`
- Create: `deploy/deploy.sh`
- Create: `deploy/.env.production`

- [ ] **Step 1: Create deploy/nginx-novel.conf**

```nginx
server {
    listen 80;
    server_name novel.maxnov.ru;
    return 301 https://$host$request_uri;
}

server {
    listen 8443 ssl;
    server_name novel.maxnov.ru;

    ssl_certificate /etc/letsencrypt/live/novel.maxnov.ru/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/novel.maxnov.ru/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:3020;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

- [ ] **Step 2: Create deploy/deploy.sh**

```bash
#!/bin/bash
set -e

echo "=== Novel CRM Deployment ==="

# Check if running on server
if [ ! -d "/opt/novel-crm" ]; then
    echo "Error: /opt/novel-crm not found. Run server-setup.sh first."
    exit 1
fi

cd /opt/novel-crm

# Copy env file
if [ ! -f ".env" ]; then
    echo "Error: .env not found. Copy from .env.example and fill in values."
    exit 1
fi

# Build and start
echo "Building and starting containers..."
docker compose down
docker compose up -d --build

# Wait for postgres
echo "Waiting for PostgreSQL..."
sleep 5

echo "=== Deployment complete ==="
echo "Application running at: https://novel.maxnov.ru"
echo "Backend API: http://localhost:3020/api/docs"
```

- [ ] **Step 3: Create deploy/server-setup.sh**

```bash
#!/bin/bash
set -e

echo "=== Novel CRM Server Setup ==="

# Create project directory
mkdir -p /opt/novel-crm
cd /opt/novel-crm

# Copy project files (run from project root)
# scp -r . root@80.87.111.142:/opt/novel-crm

# Copy nginx config
cp deploy/nginx-novel.conf /etc/nginx/sites-available/novel.maxnov.ru
ln -sf /etc/nginx/sites-available/novel.maxnov.ru /etc/nginx/sites-enabled/

# Test and reload nginx
nginx -t && nginx -s reload

# Get SSL certificate if not exists
if [ ! -d "/etc/letsencrypt/live/novel.maxnov.ru" ]; then
    echo "Obtaining SSL certificate..."
    certbot --nginx -d novel.maxnov.ru
fi

echo "=== Server setup complete ==="
```

- [ ] **Step 4: Create deploy/.env.production**

```env
DB_USER=novel
DB_PASSWORD=<generate_secure_password>
DB_NAME=novel_crm
JWT_SECRET=<generate_long_random_string>
```

- [ ] **Step 5: Commit**

```bash
git add deploy/
git commit -m "feat: add deployment scripts and nginx config"
```

---

### Task 11: README & Documentation

**Files:**
- Create: `README.md`

- [ ] **Step 1: Create README**

```markdown
# Novel CRM

Mini-CRM для обзвона B2B-контактов.

## Быстрый старт (локально)

```bash
# 1. Клонировать репозиторий
git clone <repo-url>
cd novel-crm

# 2. Создать .env
cp .env.example .env
# Отредактировать .env

# 3. Запустить
docker compose up -d

# 4. Создать админа
docker compose exec backend python create_admin.py

# 5. Импортировать Excel
docker compose exec backend python migrate.py /path/to/file.xlsx

# Приложение доступно на http://localhost:3020
```

## Деплой на VPS

```bash
# 1. Скопировать на сервер
scp -r . root@80.87.111.142:/opt/novel-crm

# 2. На сервере
cd /opt/novel-crm
cp deploy/.env.production .env
# Заполнить .env

# 3. Настроить nginx
sudo cp deploy/nginx-novel.conf /etc/nginx/sites-available/novel.maxnov.ru
sudo ln -sf /etc/nginx/sites-available/novel.maxnov.ru /etc/nginx/sites-enabled/
sudo nginx -t && sudo nginx -s reload

# 4. Получить SSL
sudo certbot --nginx -d novel.maxnov.ru

# 5. Запустить
bash deploy/deploy.sh
```

## Стек

- **Backend:** FastAPI, SQLAlchemy 2.0 async, PostgreSQL 16
- **Frontend:** React 18, TypeScript, Tailwind CSS, TanStack Table
- **Deploy:** Docker Compose, Nginx (host), Let's Encrypt

## Структура проекта

```
├── backend/          # FastAPI backend
│   ├── app/          # Application code
│   ├── migrate.py    # Excel import script
│   └── create_admin.py
├── frontend/         # React frontend
├── deploy/           # Deployment scripts
├── docker-compose.yml
└── README.md
```
```

- [ ] **Step 2: Final commit**

```bash
git add README.md
git commit -m "docs: add README with setup and deployment instructions"
```

---

## Summary

This plan creates a working MVP CRM with:
1. PostgreSQL database with all models from spec
2. FastAPI backend with JWT auth, CRUD for companies, call logging
3. React frontend with virtualized table, company card slide-in panel
4. Docker Compose for local development
5. Deployment scripts for VPS with nginx integration
6. Excel import script for 20,000 contacts

**Total estimated steps:** ~40 steps across 11 tasks
**Estimated time:** 2-3 days for MVP
**Deploy target:** novel.maxnov.ru on port 3020
