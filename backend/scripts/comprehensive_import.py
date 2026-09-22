"""
Comprehensive import script for all source files.
Imports ALL fields from ALL source files, tracks sources, stores raw data.
"""
import asyncio
import os
import uuid
import re
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import async_session, settings
from app.models import Company, User, ImportSource, ImportSourceData

# Field type mappings
INT_FIELDS = {"revenue", "profit", "employees", "capital", "balance"}
DATE_FIELDS = {"reg_date"}

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

INT_FIELDS = {"revenue", "profit", "employees", "capital", "balance"}
DATE_FIELDS = {"reg_date"}

INN_BLACKLIST_LOWER = {"№", "no", "#", "номер", "п/п", "nn", "n"}

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
    if isinstance(val, int):
        return val
    s = str(val).strip().replace(" ", "")
    try:
        return int(float(s))
    except:
        return None

def parse_revenue(val) -> Optional[int]:
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return int(val)
    s = str(val).strip()
    s = s.replace(" ", "").replace(",", ".").replace("млн", "000000").replace("тыс", "000")
    s = s.replace("млн.₽", "").replace("тыс.₽", "").replace("₽", "").replace("млн", "").replace("тыс", "")
    try:
        return int(float(s))
    except:
        return None

def parse_date(val) -> Optional[datetime]:
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, str):
        s = val.strip()
        for fmt in ('%Y-%m-%d %H:%M:%S.%f%z', '%Y-%m-%d %H:%M:%S%z', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%d.%m.%Y', '%Y/%m/%d'):
            try:
                return datetime.strptime(s, fmt).date()
            except:
                pass
    return None

def parse_datetime(val) -> Optional[datetime]:
    if val is None:
        return None
    if isinstance(val, datetime):
        return val
    if isinstance(val, str):
        s = val.strip()
        for fmt in ('%Y-%m-%d %H:%M:%S.%f%z', '%Y-%m-%d %H:%M:%S%z', '%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d'):
            try:
                return datetime.strptime(s, fmt)
            except:
                pass
    return None

def parse_bool(val) -> bool:
    if val is None or val == '':
        return False
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        return val.strip().lower() in ('true', '1', 'yes', 'да')
    return bool(val)

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


async def import_file(filepath: Path, filename: str, admin_user_id: uuid.UUID) -> dict:
    """Import a single Excel file."""
    print(f"\n=== Importing {filename} ===")
    
    async with async_session() as db:
        try:
            # Check if source already exists
            existing = await db.execute(
                select(ImportSource).where(ImportSource.original_filename == filename)
            )
            if existing.scalar_one_or_none():
                print(f"  Skipping {filename} - already imported")
                return {"created": 0, "updated": 0, "errors": 0, "skipped": 1}

            # Create ImportSource record
            source = ImportSource(
                original_filename=filename,
                stored_filename=filename,
                uploaded_by=admin_user_id,
                uploaded_at=datetime.now(),
                status="imported",
            )
            db.add(source)
            await db.flush()
            source_id = source.id
            print(f"  Created ImportSource: {source_id}")

            # Read Excel file
            try:
                wb = pd.ExcelFile(filepath)
                sheets = wb.sheet_names
                print(f"  Sheets: {sheets}")
            except Exception as e:
                print(f"  Failed to read Excel: {e}")
                return {"created": 0, "updated": 0, "errors": 1, "skipped": 0}

            total_created = 0
            total_updated = 0
            total_errors = 0

            for sheet_name in sheets:
                print(f"  Processing sheet: {sheet_name}")
                
                try:
                    df = pd.read_excel(filepath, sheet_name=sheet_name, dtype=str, na_filter=False)
                    df = df.fillna("")
                except Exception as e:
                    print(f"  Failed to read sheet {sheet_name}: {e}")
                    continue

                if df.empty:
                    print(f"  Sheet {sheet_name} is empty, skipping")
                    continue

                # Auto-detect column mapping
                columns = [str(c) for c in df.columns.tolist()]
                mapping, unmatched = auto_detect_mapping(columns)
                print(f"  Mapping: {mapping}")
                if unmatched:
                    print(f"  Unmatched columns: {unmatched}")

                # Process each row
                for idx, row in df.iterrows():
                    try:
                        inn_val = None
                        if "inn" in mapping:
                            inn_val = clean_val(row.get(mapping["inn"]))

                        # Build mapped values
                        mapped_values: dict[str, Optional[str]] = {}
                        for db_field, excel_col in mapping.items():
                            val = clean_val(row.get(excel_col))
                            if val is not None:
                                mapped_values[db_field] = val

                        # Skip rows without INN
                        if not inn_val:
                            continue

                        # Check if company exists
                        result = await db.execute(
                            select(Company).where(Company.inn == inn_val)
                        )
                        company = result.scalar_one_or_none()

                        # Prepare data for company
                        data = {}
                        for db_field, val in mapped_values.items():
                            if val is None:
                                continue
                            if db_field in INT_FIELDS:
                                parsed = parse_revenue(val)
                                if parsed is not None:
                                    data[db_field] = parsed
                            elif db_field == "reg_date":
                                parsed = parse_date(val)
                                if parsed is not None:
                                    data[db_field] = parsed
                            else:
                                data[db_field] = val

                        # Always set import_source_id
                        data["import_source_id"] = str(source_id)
                        data["source_orig"] = filename

                        if company:
                            # Update existing company
                            for field, value in data.items():
                                if value is not None:
                                    setattr(company, field, value)
                        else:
                            # Create new company
                            if "name" not in data or not data["name"]:
                                name_candidates = [
                                    mapped_values.get("name"),
                                    mapped_values.get("company"),
                                    mapped_values.get("company_name"),
                                ]
                                for nc in name_candidates:
                                    if nc:
                                        data["name"] = nc
                                        break
                                else:
                                    data["name"] = f"Company {inn_val}"

                            data["inn"] = inn_val
                            data["call_status"] = "new"
                            data["pipeline_stage"] = "new"
                            data["call_count"] = 0

                            company = Company(**data)
                            db.add(company)

                        # Store raw row data in ImportSourceData
                        raw_row = {str(col): clean_val(row[col]) for col in df.columns if clean_val(row[col])}
                        source_data = ImportSourceData(
                            source_id=source_id,
                            company_id=company.id if company else None,
                            row_data=raw_row,
                            raw_row_number=int(idx) + 1,
                        )
                        db.add(source_data)

                    except Exception as e:
                        print(f"    Row {idx} error: {e}")
                        await db.rollback()

                # Commit all rows for this sheet
                try:
                    await db.commit()
                    print(f"  Sheet {sheet_name}: committed")
                except Exception as e:
                    print(f"  Sheet {sheet_name} commit error: {e}")
                    await db.rollback()

            return {"created": 0, "updated": 0, "errors": 0, "skipped": 0}

        except Exception as e:
            print(f"  Fatal error importing {filename}: {e}")
            return {"created": 0, "updated": 0, "errors": 1, "skipped": 0}


async def import_all_files():
    """Import all Excel files from docs/ folder."""
    
    # Find admin user
    async with async_session() as db:
        admin_result = await db.execute(
            select(User).where(User.role == "admin").limit(1)
        )
        admin = admin_result.scalar_one_or_none()
        if not admin:
            print("No admin user found!")
            return
        admin_user_id = admin.id
        print(f"Using admin: {admin.email} (id: {admin_user_id})")

    docs_dir = Path("/app/docs")
    files = list(docs_dir.glob("*.xlsx")) + list(docs_dir.glob("*.xls"))
    
    # Also include subdirectories
    for subdir in ["база-вэд", "script", "callcenter"]:
        subdir_path = docs_dir / subdir
        if subdir_path.exists():
            files.extend(subdir_path.glob("*.xlsx"))
            files.extend(subdir_path.glob("*.xls"))

    print(f"Found {len(files)} files to process")
    
    total_created = 0
    total_updated = 0
    total_errors = 0
    total_skipped = 0

    for filepath in sorted(files):
        filename = filepath.name
        if filename.startswith(".") or filename.startswith("~$"):
            continue
            
        result = await import_file(filepath, filename, admin_user_id)
        total_created += result["created"]
        total_updated += result["updated"]
        total_errors += result["errors"]
        total_skipped += result.get("skipped", 0)
        
        print(f"  Result: created={result['created']}, updated={result['updated']}, errors={result['errors']}")

    print(f"\n=== IMPORT COMPLETE ===")
    print(f"Total created: {total_created}")
    print(f"Total updated: {total_updated}")
    print(f"Total errors: {total_errors}")
    print(f"Total skipped: {total_skipped}")

if __name__ == "__main__":
    asyncio.run(import_all_files())