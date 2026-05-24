"""Universal Excel importer for Novel CRM.
Usage:
  python import_new.py <file.xlsx> [--mapping mapping.json]

Auto-detects columns, creates new DB fields for unknown columns,
merges data by INN (supplement mode), creates new records if not found.
"""

import asyncio
import json
import math
import re
import sys
from datetime import date
from pathlib import Path

import pandas as pd
from dateutil import parser as dateparser
from sqlalchemy import select, text

sys.path.insert(0, str(Path(__file__).parent))
from app.database import async_session, engine
from app.models import Company

# --- Default mapping: Excel column → DB field ---
DEFAULT_COLUMN_MAP = {
    "ИНН": "inn",
    "ОГРН": "ogrn",
    "ОГРН__alt_ved_ip": "ogrn",
    "КПП": "kpp",
    "Организационно-правовая форма": "org_form",
    "Организационно-правовая форма__alt_ved_ip": "org_form",
    "Дата регистрации": "reg_date",
    "Дата регистрации__alt_ved_ip": "reg_date",
    "Дата регистрации__alt_ved_jur": "reg_date",
    "Компания": "name",
    "Наименование": "name",
    "Наименование клиента": "name",
    "Компания__alt_merged": "name",
    "ФИО": "name",
    "ФИО руководителя": "name",
    "Регион": "region",
    "Регион регистрации": "region",
    "Регион__alt_merged": "region",
    "Юр. адрес": "address",
    "Юр. адрес__alt_merged": "address",
    "Адрес (место нахождения)": "actual_address",
    "Налоговый орган": "tax_office",
    "Телефон": "phone",
    "Телефон__alt_moscow": "phone",
    "Телефон__alt_ved_jur": "phone",
    "Номер ЛПР": "lpr_phone",
    "Email": "email",
    "Электронный адрес": "email",
    "Email__alt_merged": "email",
    "Электронный адрес__alt_ved_ip": "email",
    "Сайт": "website",
    "Сайт в сети Интернет": "website",
    "Сайт компании": "website",
    "LinkedIn компания": "linkedin",
    "ФИО руководителя": "director",
    "Должность руководителя": "director_title",
    "ИНН руководителя": "director_inn",
    "ФИО финдиректора": "fin_director",
    "Представитель (ФИО, должность, телефон)": "contact_person",
    "Контакты компании": "contact_person_full",
    "Гражданство": "citizenship",
    "Основной вид деятельности": "activity_main",
    "Вид деятельности/отрасль": "activity_main",
    "Чем занимается": "activity_main",
    "Вид деятельности/отрасль__alt_ved_ip": "activity_main",
    "Код основного вида деятельности": "activity_code",
    "Код основного вида деятельности__alt_ved_ip": "activity_code",
    "Другие виды деятельности": "activity_other",
    "Ниша": "niche",
    "Ниша / Чем занимается": "niche",
    "Предмет поставки": "supply_subject",
    "Выручка": "revenue",
    "2022, Выручка, RUB": "revenue",
    "Выручка__alt_merged": "revenue",
    "Чистая прибыль/убыток": "profit",
    "2022, Чистая прибыль (убыток), RUB": "profit",
    "Количество сотрудников": "employees",
    "2022, Среднесписочная численность работников": "employees",
    "Уставный капитал, RUB": "capital",
    "Баланс": "balance",
    "2023(01.01.23-30.06.23), Обороты импорта": "import_turnover",
    "2023(01.01.23-30.06.23), Обороты экспорта": "export_turnover",
    "Импорт из Китая подтверждён": "import_confirmed",
    "Платежи за границу": "foreign_payments",
    "Арбитраж (ответчик)": "arbitrage",
    "Сумма незавершенных исков в роли ответчика, RUB": "arbitrage_amount",
    "Полученные лицензии": "licenses",
    "Реестры": "registries",
    "Реестр МСП": "msp",
    "Размер компании": "size",
    "Название сегмента": "segment",
    "Название сегмента__alt_merged": "segment",
    "Приоритет": "priority",
    "Карточка в Фокусе": "focus_link",
    "Источник": "source_orig",
    "Источники": "source_orig",
    "Филиалы": "branches",
    "Количество филиалов": "branches",
    "Комментарий / Сообщение": "comment_static",
    "Важная информация": "comment_static",
}

# Fields that should be parsed as integers
INT_FIELDS = {"revenue", "profit", "employees", "capital", "balance"}

# Fields that should be parsed as dates
DATE_FIELDS = {"reg_date"}

IP_FORMS = [
    "Индивидуальные предприниматели",
    "Индивидуальный предприниматель",
    "ИП",
]


def translit(name: str) -> str:
    ru_en = {
        "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e",
        "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
        "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
        "ф": "f", "х": "kh", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "shch",
        "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
    }
    s = name.lower().strip()
    s = s.replace(" ", "_").replace("/", "_").replace(",", "").replace("(", "").replace(")", "")
    result = ""
    for ch in s:
        result += ru_en.get(ch, ch if ch.isalnum() or ch == "_" else "_")
    result = re.sub(r"_+", "_", result).strip("_")
    if result and result[0].isdigit():
        result = "f_" + result
    return result


def clean_str(val):
    if val is None:
        return None
    s = str(val).strip()
    if s.lower() in ("nan", "nat", "", "none"):
        return None
    if s.endswith(".0") and s.count(".") == 1:
        s = s[:-2]
    return s


def parse_int(val):
    if val is None:
        return None
    try:
        f = float(val)
        if math.isnan(f):
            return None
        return int(f)
    except (ValueError, TypeError):
        try:
            s = str(val).strip().replace(" ", "").replace(",", ".")
            if s and not s.startswith("nan"):
                return int(float(s))
        except (ValueError, TypeError):
            pass
    return None


def parse_date_val(val):
    if val is None:
        return None
    try:
        if isinstance(val, date):
            return val
        if isinstance(val, pd.Timestamp):
            return val.date()
        s = str(val).strip()
        if s and s.lower() not in ("nan", "nat", ""):
            dt = dateparser.parse(s, dayfirst=True)
            if dt:
                return dt.date()
    except Exception:
        pass
    return None


def get_first(*keys, row=None):
    for key in keys:
        val = row.get(key)
        cleaned = clean_str(val)
        if cleaned:
            return cleaned
    return None


async def get_db_columns() -> set:
    async with engine.begin() as conn:
        result = await conn.execute(text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = 'companies'"
        ))
        return {row[0] for row in result}


async def add_column(column_name: str, col_type: str = "TEXT"):
    async with engine.begin() as conn:
        await conn.execute(text(
            f'ALTER TABLE companies ADD COLUMN IF NOT EXISTS "{column_name}" {col_type}'
        ))
    print(f"  + Created column: {column_name}")


async def main():
    import argparse
    parser = argparse.ArgumentParser(description="Import Excel data into CRM")
    parser.add_argument("file", help="Path to Excel file")
    parser.add_argument("--mapping", help="JSON mapping file (Excel col → DB field)")
    parser.add_argument("--yes", action="store_true", help="Auto-confirm new columns")
    parser.add_argument("--dry-run", action="store_true", help="Analyze only, no import")
    args = parser.parse_args()

    # Load mapping
    column_map = dict(DEFAULT_COLUMN_MAP)
    if args.mapping:
        with open(args.mapping, encoding="utf-8") as f:
            user_map = json.load(f)
        column_map.update(user_map)
        print(f"Loaded {len(user_map)} mappings from {args.mapping}")

    # Read Excel
    df = pd.read_excel(args.file, dtype={"ИНН": str})
    excel_columns = set(df.columns)
    print(f"\nRead {len(df)} rows from {args.file}")
    print(f"Columns ({len(excel_columns)}):")

    # Categorize columns
    mapped_cols = {}
    unmapped_cols = []
    for col in sorted(excel_columns):
        if col in column_map:
            mapped_cols[col] = column_map[col]
        else:
            unmapped_cols.append(col)

    # Group mapped by DB field
    db_to_excel = {}
    for ex_col, db_col in mapped_cols.items():
        db_to_excel.setdefault(db_col, []).append(ex_col)

    print(f"\n  Known mappings ({len(mapped_cols)} excel → {len(db_to_excel)} db):")
    for db_field, ex_cols in sorted(db_to_excel.items()):
        print(f"    {db_field} ← {', '.join(ex_cols)}")

    if unmapped_cols:
        print(f"\n  Unknown ({len(unmapped_cols)}):")
        existing_db = await get_db_columns()
        new_db_cols = []
        skip_cols = set()
        for col in unmapped_cols:
            if "№" in col or col.strip().lower() in ("#", "no", "номер", "номер п/п"):
                print(f"    {col} → (skipped — row index)")
                skip_cols.add(col)
                continue
            suggested = translit(col)
            if not suggested:
                suggested = f"extra_col_{len(new_db_cols) + 1}"
            if suggested in existing_db:
                print(f"    {col} → {suggested} (fits existing DB column)")
                column_map[col] = suggested
                mapped_cols[col] = suggested
            else:
                print(f"    {col} → {suggested} (NEW)")
                new_db_cols.append((col, suggested))

        if new_db_cols:
            if not args.yes:
                print(f"\nWill create {len(new_db_cols)} new DB columns and import their data.")
                resp = input("Continue? [Y/n]: ").strip().lower()
                if resp not in ("", "y", "yes"):
                    print("Aborted.")
                    return

            for ex_col, db_col in new_db_cols:
                await add_column(db_col)
                column_map[ex_col] = db_col
                mapped_cols[ex_col] = db_col

    # Rebuild DB → Excel mapping
    db_to_excel = {}
    for ex_col, db_col in mapped_cols.items():
        db_to_excel.setdefault(db_col, []).append(ex_col)

    # Separate model columns from extra (dynamic) columns
    model_columns = {c.name for c in Company.__table__.columns}
    extra_columns = set()
    for ex_col, db_col in mapped_cols.items():
        if db_col not in model_columns:
            extra_columns.add(db_col)

    if extra_columns:
        print(f"\nExtra (dynamically added) DB columns: {', '.join(sorted(extra_columns))}")

    if args.dry_run:
        print(f"\n{'='*60}")
        print(f"Dry run — no data imported.")
        print(f"Would process {len(df)} rows with {len(db_to_excel)} DB fields.")
        if extra_columns:
            print(f"Extra dynamic columns: {', '.join(sorted(extra_columns))}")
        print(f"{'='*60}")
        return

    # Import
    print(f"\n{'='*60}")
    print(f"Starting import...")
    print(f"{'='*60}")

    added = 0
    updated = 0
    skipped = 0
    matched_by_name = 0

    async with async_session() as session:
        for idx, row in df.iterrows():
            rd = row.to_dict()
            inn = clean_str(rd.get("ИНН"))

            # Build values dict
            values = {}
            for db_field, ex_cols in db_to_excel.items():
                if db_field == "name":
                    # Handle IP fallback for name
                    org_form = get_first(
                        "Организационно-правовая форма",
                        "Организационно-правовая форма__alt_ved_ip",
                        row=rd,
                    )
                    is_ip = org_form in IP_FORMS if org_form else False

                    name = None
                    for ex_col in ex_cols:
                        v = clean_str(rd.get(ex_col))
                        if v:
                            name = v
                            break

                    if not name and is_ip:
                        for col in ["ФИО", "ФИО руководителя"]:
                            if col in rd:
                                name = clean_str(rd.get(col))
                                if name:
                                    break

                    if name:
                        values["name"] = name
                elif db_field in INT_FIELDS:
                    v = None
                    for ex_col in ex_cols:
                        raw = rd.get(ex_col)
                        if raw is not None:
                            parsed = parse_int(raw)
                            if parsed is not None:
                                v = parsed
                                break
                    if v is not None:
                        values[db_field] = v
                elif db_field in DATE_FIELDS:
                    v = None
                    for ex_col in ex_cols:
                        parsed = parse_date_val(rd.get(ex_col))
                        if parsed is not None:
                            v = parsed
                            break
                    if v is not None:
                        values[db_field] = v
                else:
                    vals = []
                    seen = set()
                    for ex_col in ex_cols:
                        v = clean_str(rd.get(ex_col))
                        if v and v not in seen:
                            vals.append(v)
                            seen.add(v)
                    if vals:
                        values[db_field] = "; ".join(vals)

            db_name = values.get("name")
            if not db_name or not inn:
                skipped += 1
                continue

            # Separate model vs extra values
            model_vals = {k: v for k, v in values.items() if k in model_columns}
            extra_vals = {k: v for k, v in values.items() if k in extra_columns}

            # Try INN match
            result = await session.execute(select(Company).where(Company.inn == inn))
            existing = result.scalar_one_or_none()

            if not existing:
                # Try name match
                result = await session.execute(
                    select(Company).where(Company.name.ilike(db_name))
                )
                existing = result.scalar_one_or_none()
                if existing:
                    matched_by_name += 1

            if existing:
                # Update model fields (supplement mode)
                for key, value in model_vals.items():
                    if value and getattr(existing, key) is None:
                        setattr(existing, key, value)

                # Update extra fields via raw SQL
                if extra_vals:
                    set_parts = []
                    params = {"oid": existing.id}
                    for ek, ev in extra_vals.items():
                        set_parts.append(f'"{ek}" = :{ek}')
                        params[ek] = ev
                    await session.execute(text(
                        f'UPDATE companies SET {", ".join(set_parts)} WHERE id = :oid'
                    ), params)
                updated += 1
            else:
                company = Company(**{k: v for k, v in model_vals.items() if v is not None})
                session.add(company)
                if extra_vals:
                    await session.flush()
                    set_parts = []
                    params = {"oid": company.id}
                    for ek, ev in extra_vals.items():
                        set_parts.append(f'"{ek}" = :{ek}')
                        params[ek] = ev
                    await session.execute(text(
                        f'UPDATE companies SET {", ".join(set_parts)} WHERE id = :oid'
                    ), params)
                added += 1

            if (idx + 1) % 500 == 0:
                await session.commit()
                print(f"  Processed {idx + 1} rows...")

        await session.commit()

    print(f"\n{'='*60}")
    print(f"Import complete:")
    print(f"  Added:     {added} new")
    print(f"  Updated:   {updated} existing")
    print(f"    by INN:  {updated - matched_by_name}")
    print(f"    by name: {matched_by_name}")
    print(f"  Skipped:   {skipped}")
    print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(main())
