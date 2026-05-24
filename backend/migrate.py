import asyncio
import pandas as pd
import sys
from pathlib import Path
import math
from dateutil import parser as dateparser
from datetime import date

sys.path.insert(0, str(Path(__file__).parent))

from app.database import async_session
from app.models import Company

IP_FORMS = [
    "Индивидуальные предприниматели",
    "Индивидуальный предприниматель",
    "ИП",
]

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
            s = str(val).strip()
            s = s.replace(" ", "").replace(",", ".")
            if s and not s.startswith("nan"):
                return int(float(s))
        except (ValueError, TypeError):
            pass
    return None

def parse_date(val):
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

def merge_values(*keys, row=None, prioritize=None):
    """Collect values from columns, optionally with priority ordering.
    If prioritize is a list, those columns come first (preferred), but all non-empty values are included."""
    values = []
    seen = set()

    all_keys = list(keys)
    if prioritize:
        all_keys = prioritize + [k for k in keys if k not in prioritize]

    for key in all_keys:
        val = row.get(key)
        if val is not None and str(val).strip() and str(val).strip().lower() not in ("nan", "nat", ""):
            cleaned = str(val).strip()
            if cleaned not in seen:
                values.append(cleaned)
                seen.add(cleaned)

    return "; ".join(values) if values else None

def clean_str(val):
    s = str(val).strip()
    if s.lower() in ("nan", "nat", "", "none"):
        return None
    if s.endswith(".0") and s.count(".") == 1:
        s = s[:-2]
    return s

def get_first(*keys, row=None):
    for key in keys:
        val = row.get(key)
        if val is not None:
            cleaned = clean_str(val)
            if cleaned:
                return cleaned
    return None

async def normalize_row(row: dict) -> dict:
    org_form = get_first("Организационно-правовая форма", "Организационно-правовая форма__alt_ved_ip", row=row)
    is_ip = org_form in IP_FORMS if org_form else False

    name = get_first("Наименование", "Наименование клиента", "Компания", "Компания__alt_merged", row=row)
    if not name and is_ip:
        name = get_first("ФИО", "ФИО руководителя", row=row)

    inn = clean_str(row.get("ИНН"))

    revenue_val = get_first("2022, Выручка, RUB", "Выручка__alt_merged", "Выручка", row=row)
    profit_val = get_first("2022, Чистая прибыль (убыток), RUB", "Чистая прибыль/убыток", row=row)
    employees_val = get_first("2022, Среднесписочная численность работников", "Количество сотрудников", row=row)

    return {
        "name": name,
        "inn": inn,
        "ogrn": get_first("ОГРН", "ОГРН__alt_ved_ip", row=row),
        "kpp": get_first("КПП", row=row),
        "org_form": org_form,
        "reg_date": parse_date(get_first("Дата регистрации", "Дата регистрации__alt_ved_ip", "Дата регистрации__alt_ved_jur", row=row)),
        "region": get_first("Регион", "Регион регистрации", "Регион__alt_merged", row=row),
        "address": merge_values("Юр. адрес", "Юр. адрес__alt_merged", row=row),
        "actual_address": get_first("Адрес (место нахождения)", row=row),
        "tax_office": get_first("Налоговый орган", row=row),
        "phone": merge_values("Телефон", "Телефон__alt_moscow", "Телефон__alt_ved_jur", row=row),
        "lpr_phone": get_first("Номер ЛПР", row=row),
        "email": merge_values(
            "Email", "Электронный адрес",
            "Email__alt_merged", "Электронный адрес__alt_ved_ip",
            row=row,
            prioritize=["Email", "Электронный адрес", "Email__alt_merged"],
        ),
        "website": merge_values(
            "Сайт", "Сайт в сети Интернет", "Сайт компании",
            row=row,
            prioritize=["Сайт в сети Интернет", "Сайт компании", "Сайт"],
        ),
        "linkedin": get_first("LinkedIn компания", row=row),
        "director": get_first("ФИО руководителя", "ФИО", row=row),
        "director_title": get_first("Должность руководителя", row=row),
        "director_inn": get_first("ИНН руководителя", row=row),
        "fin_director": get_first("ФИО финдиректора", row=row),
        "contact_person": get_first("Представитель (ФИО, должность, телефон)", row=row),
        "contact_person_full": get_first("Контакты компании", row=row),
        "citizenship": get_first("Гражданство", row=row),
        "activity_main": merge_values(
            "Основной вид деятельности", "Вид деятельности/отрасль",
            "Чем занимается", "Вид деятельности/отрасль__alt_ved_ip",
            row=row,
        ),
        "activity_code": get_first("Код основного вида деятельности", "Код основного вида деятельности__alt_ved_ip", row=row),
        "activity_other": get_first("Другие виды деятельности", row=row),
        "niche": get_first("Ниша", "Ниша / Чем занимается", row=row),
        "supply_subject": get_first("Предмет поставки", row=row),
        "revenue": parse_int(revenue_val),
        "profit": parse_int(profit_val),
        "employees": parse_int(employees_val),
        "capital": parse_int(get_first("Уставный капитал, RUB", row=row)),
        "balance": parse_int(get_first("Баланс", row=row)),
        "import_turnover": get_first("2023(01.01.23-30.06.23), Обороты импорта", row=row),
        "export_turnover": get_first("2023(01.01.23-30.06.23), Обороты экспорта", row=row),
        "import_confirmed": get_first("Импорт из Китая подтверждён", row=row),
        "foreign_payments": get_first("Платежи за границу", row=row),
        "arbitrage": get_first("Арбитраж (ответчик)", row=row),
        "arbitrage_amount": get_first("Сумма незавершенных исков в роли ответчика, RUB", row=row),
        "licenses": get_first("Полученные лицензии", row=row),
        "registries": get_first("Реестры", row=row),
        "msp": get_first("Реестр МСП", row=row),
        "size": get_first("Размер компании", row=row),
        "segment": get_first("Название сегмента", "Название сегмента__alt_merged", row=row),
        "priority": get_first("Приоритет", row=row),
        "source_orig": merge_values("Источник", "Источники", row=row),
        "branches": merge_values("Филиалы", "Количество филиалов", row=row),
        "comment_static": merge_values("Комментарий / Сообщение", "Важная информация", row=row),
        "focus_link": get_first("Карточка в Фокусе", row=row),
    }

async def migrate_excel(file_path: str):
    df = pd.read_excel(file_path, dtype={"ИНН": str})
    print(f"Read {len(df)} rows from Excel")

    added = 0
    updated = 0
    skipped = 0

    from sqlalchemy import select

    async with async_session() as session:
        for idx, row in df.iterrows():
            data = await normalize_row(row.to_dict())
            if not data.get("inn") or not data.get("name"):
                skipped += 1
                continue

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
