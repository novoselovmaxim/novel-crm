from sqlalchemy import Column, String, Integer, Text, DateTime, Date, ForeignKey, Numeric, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.sql import func
import uuid

from .database import engine
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class VedDeclaration(Base):
    __tablename__ = "ved_declarations"
    __table_args__ = (
        Index("ix_ved_decl_inn_dir", "inn", "direction"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_file = Column(Text, nullable=False, index=True)
    direction = Column(String, nullable=False, index=True)
    inn = Column(String, nullable=True, index=True)
    company_name = Column(Text, nullable=True)
    country_from = Column(String, nullable=True, index=True)
    country_to = Column(String, nullable=True, index=True)
    hs_code = Column(String, nullable=True, index=True)
    customs_value = Column(Numeric, nullable=True)
    invoice_value = Column(Numeric, nullable=True)
    stat_value = Column(Numeric, nullable=True)
    net_weight = Column(Numeric, nullable=True)
    gross_weight = Column(Numeric, nullable=True)
    incoterms = Column(String, nullable=True)
    declaration_date = Column(Date, nullable=True, index=True)
    row_data = Column(JSONB, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class VedCompanyProfile(Base):
    __tablename__ = "ved_company_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    inn = Column(String, unique=True, nullable=False, index=True)
    company_name = Column(Text, nullable=True)
    directions = Column(ARRAY(String), nullable=True)
    total_declarations = Column(Integer, default=0)
    total_customs_value = Column(Numeric, nullable=True)
    total_stat_value = Column(Numeric, nullable=True)
    total_net_weight = Column(Numeric, nullable=True)
    destination_countries = Column(ARRAY(String), nullable=True)
    source_countries = Column(ARRAY(String), nullable=True)
    hs_codes = Column(ARRAY(String), nullable=True)
    source_files = Column(ARRAY(String), nullable=True)
    contact_phone = Column(Text, nullable=True)
    contact_email = Column(Text, nullable=True)
    website = Column(Text, nullable=True)
    director = Column(Text, nullable=True)
    address = Column(Text, nullable=True)
    region = Column(Text, nullable=True)
    revenue = Column(Numeric, nullable=True)
    employees = Column(Integer, nullable=True)
    ogrn = Column(Text, nullable=True)
    activity = Column(Text, nullable=True)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


async def create_ved_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
