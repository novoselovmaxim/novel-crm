from pydantic import BaseModel
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
    tg_chat_id: Optional[int] = None
    tg_username: Optional[str] = None
    
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
    actual_address: Optional[str] = None
    tax_office: Optional[str] = None
    phone: Optional[str] = None
    lpr_phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    linkedin: Optional[str] = None
    director: Optional[str] = None
    director_title: Optional[str] = None
    director_inn: Optional[str] = None
    fin_director: Optional[str] = None
    contact_person: Optional[str] = None
    contact_person_full: Optional[str] = None
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
    balance: Optional[int] = None
    import_turnover: Optional[str] = None
    export_turnover: Optional[str] = None
    import_confirmed: Optional[str] = None
    foreign_payments: Optional[str] = None
    arbitrage: Optional[str] = None
    arbitrage_amount: Optional[str] = None
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
    actual_address: Optional[str] = None
    tax_office: Optional[str] = None
    phone: Optional[str] = None
    lpr_phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    linkedin: Optional[str] = None
    director: Optional[str] = None
    director_title: Optional[str] = None
    director_inn: Optional[str] = None
    fin_director: Optional[str] = None
    contact_person: Optional[str] = None
    contact_person_full: Optional[str] = None
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
    balance: Optional[int] = None
    import_turnover: Optional[str] = None
    export_turnover: Optional[str] = None
    import_confirmed: Optional[str] = None
    foreign_payments: Optional[str] = None
    arbitrage: Optional[str] = None
    arbitrage_amount: Optional[str] = None
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
    call_status: str
    notes: Optional[str] = None
    next_call_date: Optional[date] = None

class MeetingCreate(BaseModel):
    meeting_date: date
    meeting_time: str
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
    archived: int
    unprocessed: int

class CommentCreate(BaseModel):
    text: str

class CommentResponse(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    user_id: uuid.UUID
    user_name: Optional[str] = None
    text: str
    created_at: datetime

    class Config:
        from_attributes = True

class AssignRequest(BaseModel):
    user_id: Optional[uuid.UUID] = None

class StatusUpdateRequest(BaseModel):
    call_status: str

class BulkStatusRequest(BaseModel):
    company_ids: list[uuid.UUID]
    call_status: str

class BulkStatusResponse(BaseModel):
    updated: int

class ExportRequest(BaseModel):
    company_ids: list[uuid.UUID]

class ImportFieldInfo(BaseModel):
    key: str
    label: str
    type: str

class UploadPreview(BaseModel):
    file_id: str
    original_filename: str
    sheets: list[str]
    columns: list[str]
    sample_rows: list[list[Optional[str]]]
    auto_mapping: dict[str, str]
    unmatched: list[str]

class ImportRunRequest(BaseModel):
    file_id: str
    sheet: str
    mapping: dict[str, str]
    original_filename: str = "import"
    template_name: Optional[str] = None
    overwrite: bool = False

class ImportTemplateCreate(BaseModel):
    name: str
    mapping: dict[str, str]

class ImportTemplateResponse(BaseModel):
    id: uuid.UUID
    name: str
    mapping: dict[str, str]

    class Config:
        from_attributes = True

class ImportSourceResponse(BaseModel):
    id: uuid.UUID
    original_filename: str
    uploaded_at: datetime
    column_mapping: Optional[dict]
    status: str
    template_name: Optional[str]
    total_rows: int = 0
    processed_rows: int = 0
    added_count: int = 0
    updated_count: int = 0
    skipped_count: int = 0
    error_message: Optional[str] = None

    class Config:
        from_attributes = True

class ImportSourceDataItem(BaseModel):
    source_id: uuid.UUID
    source_filename: str
    uploaded_at: datetime
    row_data: dict
    raw_row_number: Optional[int]

class ImportResult(BaseModel):
    added: int
    updated: int
    skipped: int
    total: int

class ImportRunCreateResponse(BaseModel):
    source_id: uuid.UUID
    status: str
    total_rows: int = 0

class ImportRunStatusResponse(BaseModel):
    source_id: uuid.UUID
    status: str  # queued, processing, imported, error
    total_rows: int = 0
    processed_rows: int = 0
    added_count: int = 0
    updated_count: int = 0
    skipped_count: int = 0
    error_message: Optional[str] = None
