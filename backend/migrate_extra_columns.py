"""
One-time script to consolidate extra columns from old imports into standard company fields.
Run on production database AFTER deploying the new import system.

Usage:
    python migrate_extra_columns.py
"""

import re
from sqlalchemy import create_engine, text, inspect

# Use your production database URL
DATABASE_URL = "postgresql://novel:novel_secret@localhost:5432/novel_crm"

# Priority order for each standard field (most recent year first)
FIELD_MAPPINGS: dict[str, list[re.Pattern]] = {
    "revenue": [
        re.compile(r"^f_2025_vyruchka_rub$", re.I),
        re.compile(r"^f_2024_vyruchka_rub$", re.I),
        re.compile(r"^f_2023_vyruchka_rub$", re.I),
        re.compile(r"^vyruchka_rub$", re.I),
        re.compile(r"^vyruchka$", re.I),
    ],
    "profit": [
        re.compile(r"^f_2025_chistaya_pribyl_ubytok_rub$", re.I),
        re.compile(r"^f_2024_chistaya_pribyl_ubytok_rub$", re.I),
        re.compile(r"^f_2023_chistaya_pribyl_ubytok_rub$", re.I),
        re.compile(r"^chistaya_pribyl_ubytok_rub$", re.I),
        re.compile(r"^chistaya_pribyl$", re.I),
    ],
    "employees": [
        re.compile(r"^f_2025_srednespisochnaya_chislennost_rabotnikov$", re.I),
        re.compile(r"^f_2024_srednespisochnaya_chislennost_rabotnikov$", re.I),
        re.compile(r"^f_2023_srednespisochnaya_chislennost_rabotnikov$", re.I),
        re.compile(r"^srednespisochnaya_chislennost_rabotnikov$", re.I),
        re.compile(r"^srednespisochnaya_chislennost$", re.I),
    ],
    "import_turnover": [
        re.compile(r"^oborot_importa$", re.I),
        re.compile(r"^importnyy_oborot$", re.I),
    ],
    "export_turnover": [
        re.compile(r"^oborot_eksporta$", re.I),
        re.compile(r"^eksportnyy_oborot$", re.I),
    ],
    "balance": [
        re.compile(r"^f_2025_valyuta_balansa$", re.I),
        re.compile(r"^f_2024_valyuta_balansa$", re.I),
        re.compile(r"^f_2023_valyuta_balansa$", re.I),
        re.compile(r"^valyuta_balansa$", re.I),
    ],
}


def main():
    engine = create_engine(DATABASE_URL)
    inspector = inspect(engine)

    # Get all columns of the companies table
    columns = [col["name"] for col in inspector.get_columns("companies")]
    extra_columns = set(columns) - {
        "id", "inn", "ogrn", "kpp", "org_form", "reg_date", "name", "region",
        "address", "actual_address", "tax_office", "phone", "lpr_phone",
        "email", "website", "linkedin", "director", "director_title",
        "director_inn", "fin_director", "contact_person", "contact_person_full",
        "citizenship", "activity_main", "activity_code", "activity_other",
        "niche", "supply_subject", "revenue", "profit", "employees", "capital",
        "balance", "import_turnover", "export_turnover", "import_confirmed",
        "foreign_payments", "arbitrage", "arbitrage_amount", "licenses",
        "registries", "msp", "size", "segment", "priority", "focus_link",
        "source_orig", "branches", "comment_static", "call_status",
        "next_call_date", "assigned_to", "call_count", "last_called_at",
        "is_deleted", "created_at", "updated_at",
    }

    print(f"Found {len(extra_columns)} extra columns:")
    for col in sorted(extra_columns):
        print(f"  - {col}")

    # Map extra columns to standard fields
    for standard_field, patterns in FIELD_MAPPINGS.items():
        matched_columns = []
        for pattern in patterns:
            for col in extra_columns:
                if pattern.match(col):
                    matched_columns.append(col)

        if not matched_columns:
            print(f"\nNo extra columns for '{standard_field}'")
            continue

        # Build a COALESCE chain: most recent year first (already ordered in FIELD_MAPPINGS)
        coalesce_parts = []
        for col in matched_columns:
            col_quoted = f'"{col}"'
            coalesce_parts.append(f"NULLIF({col_quoted}::text, '')::bigint")

        if not coalesce_parts:
            continue

        coalesce_parts.append(f'"{standard_field}"')
        coalesce_expr = "COALESCE(" + ", ".join(coalesce_parts) + ")"

        sql = text(f"""
            UPDATE companies
            SET "{standard_field}" = {coalesce_expr}
            WHERE "{standard_field}" IS NULL
              AND ({" OR ".join(f'"{c}" IS NOT NULL' for c in matched_columns)})
        """)

        print(f"\nUpdating '{standard_field}' from: {matched_columns}")
        with engine.begin() as conn:
            result = conn.execute(sql)
            print(f"  Updated {result.rowcount} rows")

    # Import/export as string — handle separately (cast to TEXT, not BIGINT)
    string_mappings = {
        "import_turnover": [r"^oborot_importa$"],
        "export_turnover": [r"^oborot_eksporta$"],
    }

    for standard_field, patterns in string_mappings.items():
        matched_columns = []
        for p in patterns:
            regex = re.compile(p, re.I)
            for col in extra_columns:
                if regex.match(col):
                    matched_columns.append(col)

        if not matched_columns:
            continue

        coalesce_parts = []
        for col in matched_columns:
            col_quoted = f'"{col}"'
            coalesce_parts.append(f"NULLIF({col_quoted}::text, '')")

        coalesce_parts.append(f'"{standard_field}"')
        coalesce_expr = "COALESCE(" + ", ".join(coalesce_parts) + ")"

        sql = text(f"""
            UPDATE companies
            SET "{standard_field}" = {coalesce_expr}
            WHERE "{standard_field}" IS NULL
              AND ({" OR ".join(f'"{c}" IS NOT NULL' for c in matched_columns)})
        """)

        print(f"\nUpdating '{standard_field}' from: {matched_columns}")
        with engine.begin() as conn:
            result = conn.execute(sql)
            print(f"  Updated {result.rowcount} rows")

    print("\nDone! Extra columns consolidated into standard fields.")


if __name__ == "__main__":
    main()
