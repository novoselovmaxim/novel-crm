from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime, date
from decimal import Decimal
import uuid


class VedDeclarationResponse(BaseModel):
    id: uuid.UUID
    source_file: str
    direction: str
    inn: Optional[str] = None
    company_name: Optional[str] = None
    country_from: Optional[str] = None
    country_to: Optional[str] = None
    hs_code: Optional[str] = None
    customs_value: Optional[Decimal] = None
    invoice_value: Optional[Decimal] = None
    stat_value: Optional[Decimal] = None
    net_weight: Optional[Decimal] = None
    gross_weight: Optional[Decimal] = None
    incoterms: Optional[str] = None
    declaration_date: Optional[date] = None
    row_data: dict
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class VedProfileResponse(BaseModel):
    id: uuid.UUID
    inn: str
    company_name: Optional[str] = None
    directions: Optional[List[str]] = None
    total_declarations: int = 0
    total_customs_value: Optional[Decimal] = None
    total_stat_value: Optional[Decimal] = None
    total_net_weight: Optional[Decimal] = None
    destination_countries: Optional[List[str]] = None
    source_countries: Optional[List[str]] = None
    hs_codes: Optional[List[str]] = None
    source_files: Optional[List[str]] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    website: Optional[str] = None
    director: Optional[str] = None
    address: Optional[str] = None
    region: Optional[str] = None
    revenue: Optional[Decimal] = None
    employees: Optional[int] = None
    ogrn: Optional[str] = None
    activity: Optional[str] = None
    company_id: Optional[uuid.UUID] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class VedProfileDetailResponse(VedProfileResponse):
    declarations: List[VedDeclarationResponse] = []


class VedProfilesResponse(BaseModel):
    items: List[VedProfileResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class VedStatsResponse(BaseModel):
    total_profiles: int
    total_declarations: int
    with_company: int
    without_company: int
    import_count: int
    export_count: int
    total_customs_value: Optional[Decimal] = None
    top_countries: List[dict] = []
    top_hs_codes: List[dict] = []


class VedImportRequest(BaseModel):
    file_paths: List[str]
    direction: Optional[str] = None  # auto-detect if not set


class VedImportResponse(BaseModel):
    status: str
    profiles_created: int
    profiles_updated: int
    declarations_inserted: int
    errors: List[str] = []
