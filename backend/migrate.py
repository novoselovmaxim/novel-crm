import asyncio
import pandas as pd
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.database import async_session
from app.models import Company

async def normalize_row(row: dict) -> dict:
    def get_first(*keys):
        for key in keys:
            val = row.get(key)
            if val and str(val).strip():
                return str(val).strip()
        return None
    
    revenue_val = get_first("Выручка", "Выручка 2022", "Выручка RUB")
    employees_val = get_first("Численность сотрудников")
    
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
        "revenue": int(float(revenue_val)) if revenue_val else None,
        "employees": int(float(employees_val)) if employees_val else None,
    }

async def migrate_excel(file_path: str):
    df = pd.read_excel(file_path)
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
