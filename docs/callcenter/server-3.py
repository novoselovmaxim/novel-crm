import json
import os
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel
import uvicorn

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONTACTS_FILE = os.path.join(BASE_DIR, "contacts.xlsx")

app = FastAPI()

COLUMN_MAP = {
    "inn":              ["ИНН"],
    "name":             ["Наименование", "Компания", "Наименование клиента", "ФИО"],
    "phone":            ["Телефон", "Контакты компании", "Номер ЛПР"],
    "email":            ["Email", "Электронный адрес"],
    "region":           ["Регион регистрации", "Регион"],
    "address":          ["Адрес (место нахождения)", "Юр. адрес"],
    "revenue":          ["2022, Выручка, RUB", "Выручка"],
    "employees":        ["2022, Среднесписочная численность работников", "Количество сотрудников"],
    "profit":           ["2022, Чистая прибыль (убыток), RUB", "Чистая прибыль/убыток"],
    "import_turnover":  ["2023(01.01.23-30.06.23), Обороты импорта"],
    "export_turnover":  ["2023(01.01.23-30.06.23), Обороты экспорта"],
    "activity_main":    ["Основной вид деятельности", "Вид деятельности/отрасль"],
    "activity_code":    ["Код основного вида деятельности"],
    "activity_other":   ["Другие виды деятельности"],
    "niche":            ["Ниша / Чем занимается", "Ниша", "Чем занимается"],
    "website":          ["Сайт компании", "Сайт в сети Интернет", "Сайт"],
    "ogrn":             ["ОГРН"],
    "kpp":              ["КПП"],
    "reg_date":         ["Дата регистрации"],
    "org_form":         ["Организационно-правовая форма"],
    "director":         ["ФИО руководителя"],
    "director_title":   ["Должность руководителя"],
    "director_inn":     ["ИНН руководителя"],
    "fin_director":     ["ФИО финдиректора"],
    "size":             ["Размер компании"],
    "msp_registry":     ["Реестр МСП"],
    "capital":          ["Уставный капитал, RUB"],
    "balance":          ["Баланс"],
    "import_confirmed": ["Импорт из Китая подтверждён"],
    "foreign_payments": ["Платежи за границу"],
    "arbitrage":        ["Арбитраж (ответчик)"],
    "branches":         ["Филиалы"],
    "branches_count":   ["Количество филиалов"],
    "licenses":         ["Полученные лицензии"],
    "focus_link":       ["Карточка в Фокусе"],
    "registries":       ["Реестры"],
    "segment":          ["Название сегмента"],
    "source":           ["Источник", "Источники"],
    "priority":         ["Приоритет"],
    "comment":          ["Комментарий / Сообщение"],
    "status_raw":       ["Статус"],
    "contact_person":   ["Представитель (ФИО, должность, телефон)"],
    "linkedin":         ["LinkedIn компания"],
    "supply_subject":   ["Предмет поставки"],
    "important_info":   ["Важная информация"],
    "tax_authority":    ["Налоговый орган"],
    "citizenship":      ["Гражданство"],
    "call_status":      ["call_status"],
    "call_notes":       ["call_notes"],
    "call_history":     ["call_history"],
    "next_call_date":   ["next_call_date"],
    "timezone_offset":  ["timezone_offset"],
}


def load_df() -> pd.DataFrame:
    df = pd.read_excel(CONTACTS_FILE, dtype=str)
    df = df.fillna("")
    real_cols = list(df.columns)

    if "id" not in real_cols:
        df.insert(0, "id", [str(i) for i in range(1, len(df) + 1)])

    for crm in ["call_status", "call_notes", "call_history", "next_call_date"]:
        if crm not in df.columns:
            df[crm] = ""

    for target, candidates in COLUMN_MAP.items():
        if target in df.columns:
            continue
        for c in candidates:
            if c in real_cols:
                df[target] = df[c]
                break
        else:
            df[target] = ""

    return df


def save_df(df: pd.DataFrame):
    original_cols = list(pd.read_excel(CONTACTS_FILE, nrows=0, dtype=str).columns)
    crm_fields = ["id", "call_status", "call_notes", "call_history",
                  "next_call_date", "Комментарий / Сообщение", "Приоритет", "timezone_offset"]
    keep = [c for c in df.columns if c in original_cols or c in crm_fields]
    df[keep].to_excel(CONTACTS_FILE, index=False)


@app.get("/api/contacts")
def get_contacts(
    search: str = "",
    source: str = "",
    type_: str = "",
    status: str = "",
    region: str = "",
    has_phone: str = "",
    priority: str = "",
    revenue_from: float = 0,
    revenue_to: float = 0,
    limit: int = 100,
    offset: int = 0,
):
    df = load_df()

    if search:
        mask = (
            df["name"].str.contains(search, case=False, na=False)
            | df["inn"].str.contains(search, case=False, na=False)
            | df["phone"].str.contains(search, case=False, na=False)
            | df["email"].str.contains(search, case=False, na=False)
            | df["region"].str.contains(search, case=False, na=False)
            | df["activity_main"].str.contains(search, case=False, na=False)
            | df["niche"].str.contains(search, case=False, na=False)
        )
        df = df[mask]

    if source:
        df = df[df["source"] == source]

    if status:
        if status == "__empty__":
            df = df[df["call_status"] == ""]
        else:
            df = df[df["call_status"] == status]

    if region:
        df = df[df["region"].str.contains(region, case=False, na=False)]

    if has_phone == "1":
        df = df[df["phone"] != ""]

    if priority:
        df = df[df["priority"] == priority]

    rev_num = (
        df["revenue"]
        .astype(str)
        .str.replace(" ", "", regex=False)
        .str.replace(",", ".", regex=False)
    )
    rev_num = pd.to_numeric(rev_num, errors="coerce")
    df = df.assign(_revenue_num=rev_num)
    if revenue_from > 0:
        df = df[df["_revenue_num"] >= revenue_from]
    if revenue_to > 0:
        df = df[df["_revenue_num"] <= revenue_to]

    total = len(df)
    chunk = df.iloc[offset: offset + limit].copy()

    now_utc = datetime.utcnow()
    local_times = []
    for _, row in chunk.iterrows():
        val = str(row.get("timezone_offset", "")).strip()
        try:
            offset_hours = float(val.replace(",", ".")) if val else None
        except ValueError:
            offset_hours = None
        if offset_hours is not None:
            lt = now_utc + timedelta(hours=offset_hours)
            local_times.append(lt.strftime("%H:%M"))
        else:
            local_times.append("")
    chunk["local_time"] = local_times

    if "_revenue_num" in chunk.columns:
        chunk = chunk.drop(columns=["_revenue_num"])

    records = chunk.to_dict(orient="records")
    return {"total": total, "offset": offset, "limit": limit, "records": records}


@app.get("/api/contacts/{contact_id}")
def get_contact(contact_id: str):
    df = load_df()
    row = df[df["id"] == str(contact_id)]
    if row.empty:
        raise HTTPException(404, "Not found")
    return row.iloc[0].to_dict()


class CallRecord(BaseModel):
    status: str
    notes: str = ""
    next_call_date: str = ""


@app.post("/api/contacts/{contact_id}/call")
def add_call(contact_id: str, body: CallRecord):
    df = load_df()
    mask = df["id"] == str(contact_id)
    if not mask.any():
        raise HTTPException(404, "Not found")

    idx = df[mask].index[0]
    history_raw = df.at[idx, "call_history"]
    try:
        history = json.loads(history_raw) if history_raw else []
    except Exception:
        history = []

    entry = {
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "status": body.status,
        "notes": body.notes,
    }
    history.append(entry)

    df.at[idx, "call_history"] = json.dumps(history, ensure_ascii=False)
    df.at[idx, "call_status"] = body.status
    df.at[idx, "call_notes"] = body.notes
    df.at[idx, "next_call_date"] = body.next_call_date

    save_df(df)
    return {"ok": True, "history": history}


class ContactUpdate(BaseModel):
    comment: Optional[str] = None
    priority: Optional[str] = None
    call_notes: Optional[str] = None
    next_call_date: Optional[str] = None


@app.patch("/api/contacts/{contact_id}")
def update_contact(contact_id: str, body: ContactUpdate):
    df = load_df()
    mask = df["id"] == str(contact_id)
    if not mask.any():
        raise HTTPException(404, "Not found")

    idx = df[mask].index[0]
    data = body.dict(exclude_none=True)
    for k, v in data.items():
        if k in df.columns:
            df.at[idx, k] = v

    save_df(df)
    return {"ok": True}


@app.get("/api/meta")
def get_meta():
    df = load_df()
    sources = sorted([s for s in df["source"].unique().tolist() if s])
    regions = sorted([r for r in df["region"].unique().tolist() if r])
    statuses = sorted([s for s in df["call_status"].unique().tolist() if s])
    return {
        "total": len(df),
        "sources": sources,
        "regions": regions,
        "statuses": statuses,
    }


@app.get("/", response_class=HTMLResponse)
def index():
    return FileResponse(os.path.join(BASE_DIR, "index.html"))


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8765)
