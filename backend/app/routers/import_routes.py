import os
import re
import uuid
import json
import asyncio
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import select, delete, or_, func

from ..database import get_db, engine as db_engine
from ..models import User, Company, ImportSource, ImportSourceData
from ..schemas import (
    UploadPreview, ImportRunRequest, ImportResult,
    ImportFieldInfo, ImportSourceResponse, ImportSourceDataItem,
    ImportTemplateCreate, ImportTemplateResponse,
    ImportRunCreateResponse, ImportRunStatusResponse,
)
from ..auth import get_current_user, require_admin

router = APIRouter(prefix="/api/import", tags=["import"])

UPLOAD_DIR = Path("/tmp/import_uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

FIELD_LABELS: dict[str, list[str]] = {
    "inn": ["ИНН", "Инн", "инн"],
    "name": ["Компания", "Наименование", "Название", "ФИО", "Имя", "Организация"],
    "region": ["Регион", "Город", "Область", "Республика", "Край"],
    "org_form": ["ОПФ", "Правовая форма", "Организационно-правовая форма"],
    "activity_main": ["Вид деятельности", "ОКВЭД", "Деятельность", "Отрасль"],
    "activity_code": ["Код ОКВЭД", "ОКВЭД код"],
    "website": ["Сайт", "Веб-сайт", "Web-site", "URL"],
    "capital": ["Уставный капитал", "УК", "Уставной капитал"],
    "revenue": ["Выручка", "Доход", "Оборот"],
    "profit": ["Прибыль", "Чистая прибыль", "Убыток"],
    "employees": ["Сотрудники", "Численность", "Работники", "Кол-во сотрудников"],
    "import_turnover": ["Импорт", "Обороты импорта"],
    "export_turnover": ["Экспорт", "Обороты экспорта"],
    "phone": ["Телефон", "Контактный телефон", "Тел.", "Мобильный"],
    "lpr_phone": ["Телефон ЛПР", "Прямой телефон", "ЛПР"],
    "email": ["Email", "E-mail", "Почта", "Электронная почта"],
    "director": ["Руководитель", "Директор", "Глава"],
    "director_title": ["Должность", "Должность руководителя"],
    "contact_person": ["Контактное лицо", "Контакт"],
    "contact_person_full": ["Контакты компании"],
    "address": ["Адрес", "Юридический адрес"],
    "actual_address": ["Факт. адрес", "Фактический адрес"],
    "ogrn": ["ОГРН", "ОГРНИП"],
    "kpp": ["КПП"],
    "reg_date": ["Дата регистрации", "Дата"],
    "tax_office": ["Налоговая", "ИФНС", "ФНС"],
    "director_inn": ["ИНН руководителя", "ИНН директора"],
    "fin_director": ["Фин. директор", "Финансовый директор"],
    "citizenship": ["Гражданство"],
    "niche": ["Ниша"],
    "supply_subject": ["Предмет снабжения", "Снабжение"],
    "balance": ["Баланс"],
    "import_confirmed": ["Подтв. импорт", "Подтвержденный импорт"],
    "foreign_payments": ["Валютные платежи", "Валютные операции"],
    "arbitrage": ["Арбитраж", "Судебные дела"],
    "arbitrage_amount": ["Сумма исков"],
    "licenses": ["Лицензии"],
    "registries": ["Реестры"],
    "msp": ["МСП"],
    "size": ["Размер", "Категория"],
    "segment": ["Сегмент"],
    "priority": ["Приоритет"],
    "branches": ["Филиалы"],
    "comment_static": ["Комментарий", "Примечание"],
    "source_orig": ["Источник", "Откуда"],
    "focus_link": ["Focus", "Ссылка"],
}

FIELD_TYPES: dict[str, str] = {
    "inn": "string",
    "name": "string",
    "region": "string",
    "org_form": "string",
    "activity_main": "string",
    "activity_code": "string",
    "website": "string",
    "phone": "string",
    "lpr_phone": "string",
    "email": "string",
    "director": "string",
    "director_title": "string",
    "contact_person": "string",
    "contact_person_full": "string",
    "address": "string",
    "actual_address": "string",
    "ogrn": "string",
    "kpp": "string",
    "tax_office": "string",
    "director_inn": "string",
    "fin_director": "string",
    "citizenship": "string",
    "niche": "string",
    "supply_subject": "string",
    "import_turnover": "string",
    "export_turnover": "string",
    "import_confirmed": "string",
    "foreign_payments": "string",
    "arbitrage": "string",
    "arbitrage_amount": "string",
    "licenses": "string",
    "registries": "string",
    "msp": "string",
    "size": "string",
    "segment": "string",
    "priority": "string",
    "branches": "string",
    "comment_static": "string",
    "source_orig": "string",
    "focus_link": "string",
    "revenue": "number",
    "profit": "number",
    "employees": "number",
    "capital": "number",
    "balance": "number",
    "reg_date": "date",
}

INT_FIELDS = {"revenue", "profit", "employees", "capital", "balance"}
DATE_FIELDS = {"reg_date"}


def translit(text: str) -> str:
    mapping = {
        "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "yo",
        "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
        "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
        "ф": "f", "х": "kh", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "shch",
        "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
        "А": "A", "Б": "B", "В": "V", "Г": "G", "Д": "D", "Е": "E", "Ё": "Yo",
        "Ж": "Zh", "З": "Z", "И": "I", "Й": "Y", "К": "K", "Л": "L", "М": "M",
        "Н": "N", "О": "O", "П": "P", "Р": "R", "С": "S", "Т": "T", "У": "U",
        "Ф": "F", "Х": "Kh", "Ц": "Ts", "Ч": "Ch", "Ш": "Sh", "Щ": "Shch",
        "Ъ": "", "Ы": "Y", "Ь": "", "Э": "e", "Ю": "Yu", "Я": "Ya",
    }
    return "".join(mapping.get(c, c) for c in text)


def clean_val(val) -> Optional[str]:
    if val is None:
        return None
    s = str(val).strip()
    if not s or s.lower() in ("nan", "nat", "none", "", "na"):
        return None
    return s


def parse_int(val) -> Optional[int]:
    if val is None:
        return None
    try:
        return int(float(str(val).replace(" ", "").replace(",", ".")))
    except (ValueError, TypeError):
        return None


def parse_revenue(val) -> Optional[int]:
    if val is None:
        return None
    s = str(val).strip()
    if not s:
        return None
    try:
        return int(float(s.replace(" ", "").replace(",", ".")))
    except (ValueError, TypeError):
        pass
    s_lower = s.lower().replace(" ", "")
    multipliers = [
        ("млрд", 1_000_000_000),
        ("миллиард", 1_000_000_000),
        ("млн", 1_000_000),
        ("миллион", 1_000_000),
        ("тыс", 1_000),
        ("тысяч", 1_000),
    ]
    for suffix, multiplier in multipliers:
        if suffix in s_lower:
            try:
                num_str = s_lower.replace(suffix, "").strip()
                num = float(num_str.replace(",", "."))
                return int(num * multiplier)
            except (ValueError, TypeError):
                pass
    return None


def normalize_phone(val: Optional[str]) -> Optional[str]:
    if not val:
        return None
    digits = re.sub(r'\D', '', val)
    return digits[-10:] if len(digits) >= 10 else digits


def normalize_website(val: Optional[str]) -> Optional[str]:
    if not val:
        return None
    s = val.strip().lower()
    s = re.sub(r'^https?://', '', s)
    s = re.sub(r'^www\.', '', s)
    s = s.rstrip('/')
    return s or None


MATCH_THRESHOLD = 2


_NAME_STRIP = re.compile(r'\b(ооо|ао|зао|ип|оао|пао|оо|llc|inc|ltd|gmbh)\b')

def _name_matches(input_name: str, db_name: str) -> bool:
    a = _NAME_STRIP.sub('', input_name.strip().lower()).strip()
    b = _NAME_STRIP.sub('', db_name.strip().lower()).strip()
    if not a or not b:
        return False
    if a == b:
        return True
    if a in b or b in a:
        return True
    ta = translit(a)
    tb = translit(b)
    if ta == tb:
        return True
    if ta in tb or tb in ta:
        return True
    a_words = [w for w in re.split(r'[\s\-_/]+', a) if len(w) >= 3]
    b_words = [w for w in re.split(r'[\s\-_/]+', b) if len(w) >= 3]
    tb_words = [w for w in re.split(r'[\s\-_/]+', tb) if len(w) >= 3]
    for w in a_words:
        if w in b or w in tb:
            return True
    for w in b_words:
        if w in a or w in ta:
            return True
    for w in tb_words:
        if w in a or w in ta:
            return True
    if len(a_words) > 1 or len(b_words) > 1:
        for wa in a_words:
            for wb in b_words:
                if _bigram_sim(wa, wb) >= 0.7:
                    return True
    if _bigram_sim(ta, tb) >= 0.55:
        return True
    ta2 = ta.replace('ch', 'kh').replace('x', 'ks')
    tb2 = tb.replace('ch', 'kh').replace('x', 'ks')
    if ta2 != ta or tb2 != tb:
        if ta2 in tb2 or tb2 in ta2:
            return True
        if _bigram_sim(ta2, tb2) >= 0.55:
            return True
    return False


def _bigram_sim(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    a_b = {a[i:i+2] for i in range(len(a) - 1)}
    b_b = {b[i:i+2] for i in range(len(b) - 1)}
    if not a_b or not b_b:
        return 0.0
    return len(a_b & b_b) / len(a_b | b_b)


async def find_company_by_fields(
    mapped_values: dict[str, Optional[str]],
    db: AsyncSession,
) -> Optional[Company]:
    name_val = mapped_values.get("name")
    region_val = mapped_values.get("region")
    website_val = mapped_values.get("website")
    phone_val = mapped_values.get("phone") or mapped_values.get("lpr_phone")

    conditions = []
    if name_val:
        nv = name_val.strip().lower()
        conditions.append(Company.name.ilike(f"%{nv}%"))
        tnv = translit(nv)
        if tnv != nv:
            conditions.append(Company.name.ilike(f"%{tnv}%"))
        for w in set(re.split(r'[\s\-_/]+', nv)):
            if len(w) >= 3:
                conditions.append(Company.name.ilike(f"%{w}%"))
    if region_val:
        conditions.append(func.lower(Company.region) == region_val.strip().lower())
    if website_val:
        norm_web = normalize_website(website_val)
        if norm_web:
            conditions.append(func.lower(Company.website).contains(norm_web))
    if phone_val:
        norm_phone = normalize_phone(phone_val)
        if norm_phone:
            conditions.append(Company.phone.like(f"%{norm_phone}"))
            conditions.append(Company.lpr_phone.like(f"%{norm_phone}"))

    if not conditions:
        return None

    try:
        result = await db.execute(
            select(Company).where(or_(*conditions)).limit(2000)
        )
        candidates = result.scalars().all()
    except Exception:
        return None

    if not candidates:
        return None

    best_score = 0
    best_company = None
    tied = False

    for company in candidates:
        score = 0
        if name_val and company.name and _name_matches(name_val, company.name):
            score += 1
        if region_val and company.region and company.region.strip().lower() == region_val.strip().lower():
            score += 1
        if website_val and company.website:
            cw = normalize_website(company.website)
            iw = normalize_website(website_val)
            if cw and iw and (cw == iw or cw in iw or iw in cw):
                score += 1
        if phone_val:
            np = normalize_phone(phone_val)
            if np:
                cp = normalize_phone(company.phone)
                clp = normalize_phone(company.lpr_phone)
                if np == cp or np == clp:
                    score += 1

        if score > best_score:
            best_score = score
            best_company = company
            tied = False
        elif score == best_score and score > 0:
            tied = True

    if best_score >= MATCH_THRESHOLD and not tied:
        return best_company

    return None


INN_BLACKLIST_LOWER = {"№", "no", "#", "номер", "п/п", "nn", "n"}

def auto_detect_mapping(columns: list[str]) -> tuple[dict[str, str], list[str]]:
    mapping: dict[str, str] = {}
    unmatched: list[str] = []

    known_labels: dict[str, list[str]] = {}
    for key, labels in FIELD_LABELS.items():
        known_labels[key] = [l.lower().strip() for l in labels]

    for col in columns:
        col_clean = col.lower().strip()
        col_translit = translit(col_clean).lower().strip()
        matched = False

        for key, labels in known_labels.items():
            if key == "inn" and col_clean in INN_BLACKLIST_LOWER:
                continue
            for label in labels:
                if col_clean == label or col_clean in label or label in col_clean:
                    mapping[key] = col
                    matched = True
                    break
            if matched:
                break

        if not matched:
            col_slug = col_translit.replace(" ", "_").replace(",", "").replace("/", "_").replace("-", "_")
            col_slug = "".join(c for c in col_slug if c.isalnum() or c == "_")
            if col_slug and col_slug not in INN_BLACKLIST_LOWER:
                for key in FIELD_LABELS:
                    if key in col_slug or col_slug in key:
                        mapping[key] = col
                        matched = True
                        break

        if not matched:
            unmatched.append(col)

    return mapping, unmatched


@router.get("/fields", response_model=list[ImportFieldInfo])
async def list_fields():
    return [
        ImportFieldInfo(key=k, label=FIELD_LABELS.get(k, [k])[0], type=FIELD_TYPES.get(k, "string"))
        for k in FIELD_LABELS
    ]


@router.post("/upload", response_model=UploadPreview)
async def upload_file(file: UploadFile = File(...), _=Depends(require_admin)):
    if not (file.filename and (file.filename.endswith(".xlsx") or file.filename.endswith(".xls"))):
        raise HTTPException(status_code=400, detail="Only .xlsx and .xls files are supported")

    file_id = str(uuid.uuid4())
    ext = Path(file.filename).suffix
    stored_path = UPLOAD_DIR / f"{file_id}{ext}"

    content = await file.read()
    stored_path.write_bytes(content)

    try:
        xls = pd.ExcelFile(stored_path)
        sheets = xls.sheet_names

        df = pd.read_excel(stored_path, sheet_name=sheets[0], dtype=str, nrows=100)
        columns = [str(c) for c in df.columns.tolist()]
        sample_rows: list[list[Optional[str]]] = []
        for _, row in df.head(5).iterrows():
            sample_rows.append([clean_val(row[c]) for c in df.columns])

        auto_mapping, unmatched = auto_detect_mapping(columns)

        return UploadPreview(
            file_id=file_id,
            original_filename=file.filename,
            sheets=sheets,
            columns=columns,
            sample_rows=sample_rows,
            auto_mapping=auto_mapping,
            unmatched=unmatched,
        )
    except Exception as e:
        stored_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=f"Failed to parse Excel: {e}")


@router.post("/run", response_model=ImportRunCreateResponse)
async def run_import(
    req: ImportRunRequest,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    ext = ".xlsx" if (UPLOAD_DIR / f"{req.file_id}.xlsx").exists() else ".xls"
    file_path = UPLOAD_DIR / f"{req.file_id}{ext}"

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found. Upload again.")

    source = ImportSource(
        original_filename=req.original_filename,
        stored_filename=file_path.name,
        uploaded_by=current_user.id,
        column_mapping=req.mapping,
        template_name=req.template_name,
        status="queued",
    )
    db.add(source)
    await db.flush()
    source_id = source.id

    df = pd.read_excel(file_path, sheet_name=req.sheet, dtype=str)
    total_rows = len(df)
    source.total_rows = total_rows
    await db.commit()

    task_data = {
        "source_id": str(source_id),
        "file_path": str(file_path),
        "sheet": req.sheet,
        "mapping": req.mapping,
        "overwrite": req.overwrite,
    }

    asyncio.create_task(_run_import_background(task_data))

    return ImportRunCreateResponse(
        source_id=source_id,
        status="queued",
        total_rows=total_rows,
    )


@router.get("/run/{source_id}/status", response_model=ImportRunStatusResponse)
async def get_import_status(
    source_id: uuid.UUID,
    _=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ImportSource).where(ImportSource.id == source_id))
    source = result.scalar_one_or_none()
    if not source:
        raise HTTPException(status_code=404, detail="Import not found")

    return ImportRunStatusResponse(
        source_id=source.id,
        status=source.status,
        total_rows=source.total_rows or 0,
        processed_rows=source.processed_rows or 0,
        added_count=source.added_count or 0,
        updated_count=source.updated_count or 0,
        skipped_count=source.skipped_count or 0,
        error_message=source.error_message,
    )


async def _run_import_background(task_data: dict):
    source_id = uuid.UUID(task_data["source_id"])
    file_path = Path(task_data["file_path"])
    sheet = task_data["sheet"]
    mapping: dict[str, str] = task_data["mapping"]
    overwrite = task_data.get("overwrite", False)

    print(f"[IMPORT {source_id}] Starting background import for {file_path}", flush=True)

    async_session_local = async_sessionmaker(db_engine, expire_on_commit=False)

    async with async_session_local() as db:
        try:
            result = await db.execute(select(ImportSource).where(ImportSource.id == source_id))
            source = result.scalar_one()
            source.status = "processing"
            await db.commit()
            print(f"[IMPORT {source_id}] Status set to processing", flush=True)

            loop = asyncio.get_running_loop()
            df = await loop.run_in_executor(
                None, lambda: pd.read_excel(file_path, sheet_name=sheet, dtype=str)
            )

            columns = list(df.columns)
            start_time = time.monotonic()
            MAX_DURATION = 900
            total = len(df)

            for idx, row in df.iterrows():
                elapsed = time.monotonic() - start_time
                if elapsed > MAX_DURATION:
                    raise TimeoutError(f"Import timed out after {elapsed:.0f}s")

                if idx % 50 == 0:
                    print(f"[IMPORT {source_id}] Processing row {idx+1}/{total}", flush=True)

                raw_row = {str(col): clean_val(row[col]) for col in columns}

                inn_val = None
                if "inn" in mapping:
                    inn_val = clean_val(row.get(mapping["inn"]))

                mapped_values: dict[str, Optional[str]] = {}
                for db_field, excel_col in mapping.items():
                    mapped_values[db_field] = clean_val(row.get(excel_col))

                company = None

                if inn_val:
                    result = await db.execute(
                        select(Company).where(Company.inn == inn_val)
                    )
                    company = result.scalar_one_or_none()

                if not company:
                    company = await find_company_by_fields(mapped_values, db)

                if company:
                    for field, value in mapped_values.items():
                        if value is None:
                            continue
                        if field in ("inn",):
                            continue
                        if overwrite:
                            if field in INT_FIELDS:
                                parsed = parse_revenue(value)
                                if parsed is not None:
                                    setattr(company, field, parsed)
                            elif field == "reg_date":
                                try:
                                    dt = datetime.strptime(value[:10], "%Y-%m-%d")
                                    company.reg_date = dt.date()
                                except (ValueError, IndexError):
                                    pass
                            else:
                                setattr(company, field, value)
                        else:
                            if field == "name" and not company.name:
                                company.name = value
                            elif field in INT_FIELDS:
                                parsed = parse_revenue(value)
                                if parsed is not None and getattr(company, field) is None:
                                    setattr(company, field, parsed)
                            elif field == "reg_date" and company.reg_date is None:
                                try:
                                    dt = datetime.strptime(value[:10], "%Y-%m-%d")
                                    company.reg_date = dt.date()
                                except (ValueError, IndexError):
                                    pass
                            elif field not in INT_FIELDS and field not in DATE_FIELDS:
                                if getattr(company, field) is None:
                                    setattr(company, field, value)

                    source_data = ImportSourceData(
                        source_id=source.id,
                        company_id=company.id,
                        row_data=raw_row,
                        raw_row_number=idx,
                    )
                    db.add(source_data)
                    source.updated_count = (source.updated_count or 0) + 1
                else:
                    company_inn = inn_val if inn_val else f"TEMP-{uuid.uuid4()}"

                    create_kwargs: dict = {}
                    for field, value in mapped_values.items():
                        if value is None:
                            continue
                        if field in INT_FIELDS:
                            parsed = parse_revenue(value)
                            if parsed is not None:
                                create_kwargs[field] = parsed
                        elif field == "reg_date":
                            try:
                                dt = datetime.strptime(value[:10], "%Y-%m-%d")
                                create_kwargs[field] = dt.date()
                            except (ValueError, IndexError):
                                pass
                        else:
                            create_kwargs[field] = value

                    if "name" not in create_kwargs:
                        create_kwargs["name"] = f"Company {company_inn}"
                    if "inn" not in create_kwargs:
                        create_kwargs["inn"] = company_inn

                    company = Company(**create_kwargs)
                    db.add(company)
                    await db.flush()

                    source_data = ImportSourceData(
                        source_id=source.id,
                        company_id=company.id,
                        row_data=raw_row,
                        raw_row_number=idx,
                    )
                    db.add(source_data)
                    source.added_count = (source.added_count or 0) + 1

                source.processed_rows = idx + 1

                if idx % 100 == 0 and idx > 0:
                    await db.commit()

            source.status = "imported"
            file_path.unlink(missing_ok=True)
            await db.commit()
            print(f"[IMPORT {source_id}] Import completed successfully: added={source.added_count} updated={source.updated_count} skipped={source.skipped_count}", flush=True)

        except (TimeoutError, asyncio.TimeoutError, asyncio.CancelledError):
            print(f"[IMPORT {source_id}] TIMED OUT after 15 minutes", flush=True)
            source.status = "error"
            source.error_message = "Import timed out after 15 minutes"
            await db.commit()
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            print(f"[IMPORT {source_id}] ERROR: {tb[:500]}", flush=True)
            source.status = "error"
            source.error_message = tb[:500]
            await db.commit()
        finally:
            file_path.unlink(missing_ok=True)


def process_mapped_row(
    row: pd.Series,
    mapping: dict[str, str],
    df_columns: list[str],
) -> tuple[Optional[str], dict[str, Optional[str]]]:
    inn_val = None
    if "inn" in mapping:
        inn_val = clean_val(row.get(mapping["inn"]))

    mapped_values: dict[str, Optional[str]] = {}
    for db_field, excel_col in mapping.items():
        mapped_values[db_field] = clean_val(row.get(excel_col))

    return inn_val, mapped_values


@router.delete("/sources/{source_id}")
async def delete_source(
    source_id: uuid.UUID,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ImportSource).where(ImportSource.id == source_id)
    )
    src = result.scalar_one_or_none()
    if not src:
        raise HTTPException(status_code=404, detail="Source not found")
    await db.execute(
        delete(ImportSourceData).where(ImportSourceData.source_id == source_id)
    )
    await db.delete(src)
    await db.commit()
    return {"ok": True}


@router.get("/sources", response_model=list[ImportSourceResponse])
async def list_sources(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ImportSource)
        .where(ImportSource.status != "template")
        .order_by(ImportSource.uploaded_at.desc())
    )
    return [ImportSourceResponse.model_validate(s) for s in result.scalars().all()]


@router.get("/sources/{source_id}/data", response_model=list[ImportSourceDataItem])
async def get_source_data(
    source_id: uuid.UUID,
    company_id: uuid.UUID = Query(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ImportSourceData, ImportSource)
        .join(ImportSource, ImportSourceData.source_id == ImportSource.id)
        .where(
            ImportSourceData.source_id == source_id,
            ImportSourceData.company_id == company_id,
        )
    )
    rows = result.all()

    items = []
    for sd, src in rows:
        items.append(ImportSourceDataItem(
            source_id=sd.source_id,
            source_filename=src.original_filename,
            uploaded_at=src.uploaded_at,
            row_data=sd.row_data,
            raw_row_number=sd.raw_row_number,
        ))
    return items


@router.get("/data", response_model=list[ImportSourceDataItem])
async def get_company_source_data(
    company_id: uuid.UUID = Query(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ImportSourceData, ImportSource)
        .join(ImportSource, ImportSourceData.source_id == ImportSource.id)
        .where(
            ImportSourceData.company_id == company_id,
            ImportSource.status == "imported",
        )
        .order_by(ImportSource.uploaded_at.desc(), ImportSourceData.raw_row_number)
    )
    rows = result.all()

    items = []
    for sd, src in rows:
        items.append(ImportSourceDataItem(
            source_id=sd.source_id,
            source_filename=src.original_filename,
            uploaded_at=src.uploaded_at,
            row_data=sd.row_data,
            raw_row_number=sd.raw_row_number,
        ))
    return items


@router.post("/templates", response_model=ImportTemplateResponse)
async def create_template(
    req: ImportTemplateCreate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    src = ImportSource(
        original_filename=f"template_{req.name}",
        stored_filename="template",
        uploaded_by=current_user.id,
        column_mapping=req.mapping,
        template_name=req.name,
        status="template",
    )
    db.add(src)
    await db.commit()
    await db.refresh(src)
    return ImportTemplateResponse(id=src.id, name=src.template_name or "", mapping=src.column_mapping or {})


@router.get("/templates", response_model=list[ImportTemplateResponse])
async def list_templates(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ImportSource)
        .where(
            ImportSource.status == "template",
            ImportSource.template_name.isnot(None),
        )
        .order_by(ImportSource.template_name)
    )
    return [
        ImportTemplateResponse(id=s.id, name=s.template_name or "", mapping=s.column_mapping or {})
        for s in result.scalars().all()
    ]


@router.delete("/templates/{template_id}")
async def delete_template(
    template_id: uuid.UUID,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ImportSource).where(
            ImportSource.id == template_id,
            ImportSource.status == "template",
        )
    )
    src = result.scalar_one_or_none()
    if not src:
        raise HTTPException(status_code=404, detail="Template not found")
    await db.delete(src)
    await db.commit()
    return {"ok": True}
