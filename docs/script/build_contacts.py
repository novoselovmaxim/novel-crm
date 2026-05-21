import pandas as pd
import os
from functools import reduce

# --------- настройки ---------
FILES = {
    "merged": {
        "path": "1.xlsx",   # было merged_all.xlsx
        "sheet": "Все компании",
        "inn_cols": ["ИНН", "INN"]
    },
    "ved_jur": {
        "path": "2.xlsx",   # было VED_-2.xlsx
        "sheet": "ЮрЛица",
        "inn_cols": ["ИНН", "INN"]
    },
    "ved_ip": {
        "path": "2.xlsx",   # тот же файл, лист ИПшники
        "sheet": "ИПшники",
        "inn_cols": ["ИНН", "INN"]
    },
    "clients": {
        "path": "3.xlsx",   # было Klienty_VED_s_saitami_i_kontaktami-3.xlsx
        "sheet": "Clients",
        "inn_cols": ["ИНН", "INN"]
    },
    "moscow": {
        "path": "4.xlsx",   # было moskovskie_kompanii_500mln-4.xlsx
        "sheet": "Компании",
        "inn_cols": ["ИНН", "INN"]
    },
}

PRIMARY_KEY = "ИНН"
OUT_FILE = "contacts_full_merged.xlsx"


def find_inn_column(columns, inn_candidates):
    for c in columns:
        cu = str(c).strip().upper()
        for pattern in inn_candidates:
            if pattern.upper() in cu:
                return c
    return None


def normalize_inn_series(s: pd.Series) -> pd.Series:
    s = s.astype(str).str.replace(r"\D", "", regex=True)
    s = s.where(s.str.len().isin([10, 12]), None)
    return s


def load_source(name, cfg):
    path = cfg["path"]
    sheet = cfg["sheet"]
    inn_candidates = cfg["inn_cols"]

    if not os.path.exists(path):
        print(f"[WARN] Файл {path} не найден, пропускаю {name}")
        return None

    print(f"[INFO] Загружаю {name} из {path} ({sheet})...")
    df = pd.read_excel(path, sheet_name=sheet, dtype=str)

    inn_col = find_inn_column(df.columns, inn_candidates)
    if inn_col is None:
        print(f"[WARN] Не найден столбец ИНН в {name}, пропускаю")
        return None

    df[PRIMARY_KEY] = normalize_inn_series(df[inn_col])
    df = df[df[PRIMARY_KEY].notna()].copy()
    df.columns = [str(c).strip() for c in df.columns]

    if inn_col != PRIMARY_KEY:
        df.drop(columns=[inn_col], inplace=True, errors="ignore")

    df["__source"] = name
    return df


def union_all_sources():
    dfs = []
    for name, cfg in FILES.items():
        df = load_source(name, cfg)
        if df is not None:
            dfs.append(df)

    if not dfs:
        raise RuntimeError("Не удалось загрузить ни один источник")

    all_df = pd.concat(dfs, ignore_index=True)
    return all_df


def merge_records(all_df: pd.DataFrame) -> pd.DataFrame:
    cols = [c for c in all_df.columns if c not in ["__source"]]
    data_cols = [c for c in cols if c != PRIMARY_KEY]

    grouped = all_df.groupby(PRIMARY_KEY, dropna=False)

    rows = []
    alt_columns = set()

    for inn, grp in grouped:
        row = {PRIMARY_KEY: inn}
        for col in data_cols:
            values = grp[col].dropna().astype(str).str.strip()
            values = values[values != ""]
            unique_vals = values.unique()

            if len(unique_vals) == 0:
                row[col] = None
            elif len(unique_vals) == 1:
                row[col] = unique_vals[0]
            else:
                main_val = unique_vals[0]
                row[col] = main_val

                for val in unique_vals[1:]:
                    mask_val = (grp[col].fillna("").astype(str).str.strip() == val)
                    src_for_val = grp.loc[mask_val, "__source"].fillna("").astype(str).unique()
                    if len(src_for_val) == 0:
                        alt_col = f"{col}__alt"
                        alt_columns.add(alt_col)
                        prev = row.get(alt_col)
                        if prev:
                            if val not in prev.split(" | "):
                                row[alt_col] = prev + " | " + val
                        else:
                            row[alt_col] = val
                    else:
                        for src in src_for_val:
                            alt_col = f"{col}__alt_{src}"
                            alt_columns.add(alt_col)
                            prev = row.get(alt_col)
                            if prev:
                                if val not in prev.split(" | "):
                                    row[alt_col] = prev + " | " + val
                            else:
                                row[alt_col] = val

        rows.append(row)

    result = pd.DataFrame(rows)

    for col in alt_columns:
        if col not in result.columns:
            result[col] = None

    base_cols = [c for c in result.columns if not c.startswith("__") and "__alt" not in c]
    alt_cols = [c for c in result.columns if "__alt" in c]

    base_cols = [c for c in base_cols if c != PRIMARY_KEY]
    ordered_cols = [PRIMARY_KEY] + sorted(base_cols) + sorted(alt_cols)

    result = result[ordered_cols]
    return result


def main():
    print("[INFO] Загружаем и объединяем все источники...")
    all_df = union_all_sources()
    print(f"[INFO] Всего строк после объединения всех файлов: {len(all_df)}")

    print("[INFO] Группируем по ИНН и объединяем поля...")
    final_df = merge_records(all_df)
    print(f"[INFO] Уникальных ИНН (компаний): {len(final_df)}")

    print(f"[INFO] Сохраняю результат в {OUT_FILE} ...")
    final_df.to_excel(OUT_FILE, index=False)
    print("[INFO] Готово.")


if __name__ == "__main__":
    main()