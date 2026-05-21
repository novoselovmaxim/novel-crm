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
