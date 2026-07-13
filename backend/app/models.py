from sqlalchemy import Column, String, Integer, BigInteger, Text, Boolean, DateTime, Date, ForeignKey, Enum as SAEnum, Time, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
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

class TgToken(Base):
    __tablename__ = "tg_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    token = Column(String, unique=True, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used = Column(Boolean, default=False)

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
    actual_address = Column(Text, nullable=True)
    tax_office = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    lpr_phone = Column(String, nullable=True)
    lpr_email = Column(String, nullable=True)
    email = Column(String, nullable=True)
    website = Column(String, nullable=True)
    linkedin = Column(String, nullable=True)
    director = Column(String, nullable=True)
    director_gender = Column(String, nullable=True)
    director_title = Column(String, nullable=True)
    director_inn = Column(String, nullable=True)
    fin_director = Column(String, nullable=True)
    contact_person = Column(Text, nullable=True)
    contact_person_full = Column(Text, nullable=True)
    citizenship = Column(String, nullable=True)
    activity_main = Column(Text, nullable=True)
    activity_code = Column(String, nullable=True)
    activity_other = Column(Text, nullable=True)
    niche = Column(String, nullable=True)
    supply_subject = Column(String, nullable=True)
    revenue = Column(BigInteger, nullable=True)
    profit = Column(BigInteger, nullable=True)
    employees = Column(Integer, nullable=True)
    capital = Column(BigInteger, nullable=True)
    balance = Column(BigInteger, nullable=True)
    import_turnover = Column(String, nullable=True)
    export_turnover = Column(String, nullable=True)
    import_confirmed = Column(String, nullable=True)
    foreign_payments = Column(String, nullable=True)
    arbitrage = Column(String, nullable=True)
    arbitrage_amount = Column(String, nullable=True)
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
    pipeline_stage = Column(String, default="new", index=True)
    tg_contact = Column(String, nullable=True)
    tg_status = Column(String, default="none")
    messenger = Column(String, nullable=True)
    next_call_date = Column(Date, nullable=True, index=True)
    assigned_to = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    call_count = Column(Integer, default=0)
    last_called_at = Column(DateTime(timezone=True), nullable=True)
    ai_suggestions = Column(JSONB, nullable=True)
    ai_summary = Column(Text, nullable=True)
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

class AvailabilitySlot(Base):
    __tablename__ = "availability_slots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    day_of_week = Column(Integer, nullable=False)  # 0=Monday, 6=Sunday
    time_start = Column(Time, nullable=False)
    time_end = Column(Time, nullable=False)

class Meeting(Base):
    __tablename__ = "meetings"
    __table_args__ = (UniqueConstraint("date", "hour", name="uq_meeting_slot"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    booked_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    date = Column(Date, nullable=False)
    hour = Column(Integer, nullable=False)  # 0-23
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class ImportSource(Base):
    __tablename__ = "import_sources"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    original_filename = Column(String, nullable=False)
    stored_filename = Column(String, nullable=False)
    uploaded_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
    column_mapping = Column(JSONB, nullable=True)
    template_name = Column(String, nullable=True)
    status = Column(String, default="imported")
    total_rows = Column(Integer, default=0)
    processed_rows = Column(Integer, default=0)
    added_count = Column(Integer, default=0)
    updated_count = Column(Integer, default=0)
    skipped_count = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)


class ImportSourceData(Base):
    __tablename__ = "import_source_data"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id = Column(UUID(as_uuid=True), ForeignKey("import_sources.id"), nullable=False, index=True)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=True, index=True)
    row_data = Column(JSONB, nullable=False)
    raw_row_number = Column(Integer, nullable=True)


class CompanyComment(Base):
    __tablename__ = "company_comments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    text = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class PipelineLog(Base):
    __tablename__ = "pipeline_log"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    from_stage = Column(String, nullable=True)
    to_stage = Column(String, nullable=False)
    changed_at = Column(DateTime(timezone=True), server_default=func.now())


class EmailCommunication(Base):
    __tablename__ = "email_communications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    sender_email = Column(String, nullable=False)
    recipient_email = Column(String, nullable=False)
    subject = Column(Text, nullable=False)
    body_html = Column(Text, nullable=True)
    body_text = Column(Text, nullable=True)
    status = Column(String, default="sent")
    message_id = Column(String, nullable=True, index=True)
    sent_at = Column(DateTime(timezone=True), server_default=func.now())
    opened_at = Column(DateTime(timezone=True), nullable=True)
    clicked_at = Column(DateTime(timezone=True), nullable=True)
    bounce_reason = Column(Text, nullable=True)


class EmailEvent(Base):
    __tablename__ = "email_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    communication_id = Column(UUID(as_uuid=True), ForeignKey("email_communications.id"), nullable=False, index=True)
    event_type = Column(String, nullable=False)
    link_url = Column(Text, nullable=True)
    ip_address = Column(String, nullable=True)
    user_agent = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class FollowUp(Base):
    __tablename__ = "follow_ups"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    recipient_email = Column(String, nullable=False)
    trigger_type = Column(String, default="manual")
    status = Column(String, default="pending")
    subject = Column(Text, nullable=False)
    body_html = Column(Text, nullable=True)
    body_text = Column(Text, nullable=True)
    scheduled_at = Column(DateTime(timezone=True), nullable=True, index=True)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
