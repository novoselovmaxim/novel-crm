import asyncio
import re
from sqlalchemy import text, func, select
from app.database import async_session
from app.models import Company

YEAR = r'202[3-5]'
MAPPINGS = [
    (re.compile(rf'f_{YEAR}_vyruchka_rub', re.I), 'revenue', 'bigint'),
    (re.compile(rf'f_{YEAR}_profit|pribyl|chistaya_pribyl', re.I), 'profit', 'bigint'),
    (re.compile(r'f_\d+_srednespisochnaya_chislennost|sotrudniki|workers|employees', re.I), 'employees', 'bigint'),
    (re.compile(rf'f_{YEAR}_stavka|ndfl|tax', re.I), 'tax', 'bigint'),
    (re.compile(rf'f_{YEAR}_zarplata|salary|wage', re.I), 'wage', 'bigint'),
    (re.compile(rf'f_{YEAR}_main_okved|okved_main', re.I), 'okved_main', 'text'),
    (re.compile(rf'f_{YEAR}_dop_okved|okved_dop', re.I), 'okved_dop', 'text'),
    (re.compile(rf'f_{YEAR}_phone|telefon', re.I), 'phone', 'text'),
    (re.compile(rf'f_{YEAR}_email|pochta', re.I), 'email', 'text'),
    (re.compile(rf'f_{YEAR}_website|sait|web', re.I), 'website', 'text'),
    (re.compile(rf'f_{YEAR}_address|adres', re.I), 'address', 'text'),
    (re.compile(rf'f_{YEAR}_opf', re.I), 'org_form', 'text'),
    (re.compile(rf'f_{YEAR}_region', re.I), 'region', 'text'),
    (re.compile(rf'f_{YEAR}_city|gorod', re.I), 'city', 'text'),
    (re.compile(rf'f_{YEAR}_fio|director|rukovoditel', re.I), 'director', 'text'),
]


async def migrate():
    async with async_session() as db:
        result = await db.execute(text("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'companies'
            AND column_name LIKE 'f_%'
            ORDER BY column_name
        """))
        extra_cols = {r[0]: r[1] for r in result.fetchall()}
        print(f"Found {len(extra_cols)} extra columns")

        stats_fields = ['revenue', 'profit', 'employees']
        if hasattr(Company, 'tax'):
            stats_fields.append('tax')
        if hasattr(Company, 'wage'):
            stats_fields.append('wage')

        mapped = 0
        for col, col_type in extra_cols.items():
            matched = False
            for pattern, target, target_type in MAPPINGS:
                if pattern.search(col):
                    matched = True
                    mapped += 1
                    cast_col = f'"{col}"'
                    if target_type == 'bigint' and col_type in ('text', 'character varying'):
                        cast_col = f'NULLIF(regexp_replace("{col}", \'[^0-9\\-]\', \'\', \'g\'), \'\')::bigint'
                    print(f"  {col} ({col_type}) -> {target} ({target_type})")
                    await db.execute(text(f'''
                        UPDATE companies
                        SET "{target}" = COALESCE(companies."{target}", sub.val)
                        FROM (SELECT id, {cast_col} AS val FROM companies WHERE "{col}" IS NOT NULL) AS sub
                        WHERE companies.id = sub.id AND sub.val IS NOT NULL
                    '''))
                    break
            if not matched:
                print(f"  {col} ({col_type}) -> UNMAPPED")

        await db.commit()

        total = (await db.execute(select(func.count()).select_from(Company))).scalar()
        for field in stats_fields:
            cnt = (await db.execute(select(func.count()).select_from(Company).where(getattr(Company, field).isnot(None)))).scalar()
            print(f"  {field}: {cnt}/{total} ({cnt/total*100:.1f}%)")

        print(f"\nDone. Mapped {mapped}/{len(extra_cols)} extra columns.")


if __name__ == "__main__":
    asyncio.run(migrate())
