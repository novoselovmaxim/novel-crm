import json
import os
import pandas as pd
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel
from typing import Optional
import uvicorn

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONTACTS_FILE = os.path.join(BASE_DIR, "contacts.xlsx")

app = FastAPI()

def load_df():
    df = pd.read_excel(CONTACTS_FILE, dtype=str)
    df = df.fillna('')
    return df

def save_df(df):
    df.to_excel(CONTACTS_FILE, index=False)

@app.get("/api/contacts")
def get_contacts(
    search: str = '',
    source: str = '',
    type_: str = '',
    status: str = '',
    region: str = '',
    has_phone: str = '',
    priority: str = '',
    limit: int = 100,
    offset: int = 0
):
    df = load_df()

    if search:
        mask = (
            df['name'].str.contains(search, case=False, na=False) |
            df['inn'].str.contains(search, case=False, na=False) |
            df['phone'].str.contains(search, case=False, na=False) |
            df['email'].str.contains(search, case=False, na=False) |
            df['region'].str.contains(search, case=False, na=False) |
            df['activity_main'].str.contains(search, case=False, na=False) |
            df['niche'].str.contains(search, case=False, na=False)
        )
        df = df[mask]

    if source:
        df = df[df['source'] == source]
    if type_:
        df = df[df['type'] == type_]
    if status:
        if status == '__empty__':
            df = df[df['call_status'] == '']
        else:
            df = df[df['call_status'] == status]
    if region:
        df = df[df['region'].str.contains(region, case=False, na=False)]
    if has_phone == '1':
        df = df[df['phone'] != '']
    if priority:
        df = df[df['priority'] == priority]

    total = len(df)
    chunk = df.iloc[offset:offset+limit]
    records = chunk.to_dict(orient='records')
    return {"total": total, "offset": offset, "limit": limit, "records": records}

@app.get("/api/contacts/{contact_id}")
def get_contact(contact_id: int):
    df = load_df()
    row = df[df['id'] == str(contact_id)]
    if row.empty:
        raise HTTPException(404, "Not found")
    return row.iloc[0].to_dict()

class CallRecord(BaseModel):
    status: str
    notes: str = ''
    next_call_date: str = ''

@app.post("/api/contacts/{contact_id}/call")
def add_call(contact_id: int, body: CallRecord):
    df = load_df()
    mask = df['id'] == str(contact_id)
    if not mask.any():
        raise HTTPException(404, "Not found")

    idx = df[mask].index[0]
    history_raw = df.at[idx, 'call_history']
    try:
        history = json.loads(history_raw) if history_raw else []
    except:
        history = []

    entry = {
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "status": body.status,
        "notes": body.notes,
    }
    history.append(entry)
    df.at[idx, 'call_history'] = json.dumps(history, ensure_ascii=False)
    df.at[idx, 'call_status'] = body.status
    df.at[idx, 'call_notes'] = body.notes
    df.at[idx, 'next_call_date'] = body.next_call_date
    save_df(df)
    return {"ok": True, "history": history}

class ContactUpdate(BaseModel):
    comment: Optional[str] = None
    priority: Optional[str] = None
    call_notes: Optional[str] = None
    next_call_date: Optional[str] = None

@app.patch("/api/contacts/{contact_id}")
def update_contact(contact_id: int, body: ContactUpdate):
    df = load_df()
    mask = df['id'] == str(contact_id)
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
    return {
        "total": len(df),
        "sources": sorted(df['source'].unique().tolist()),
        "regions": sorted([r for r in df['region'].unique().tolist() if r]),
        "statuses": sorted([s for s in df['call_status'].unique().tolist() if s]),
    }

@app.get("/", response_class=HTMLResponse)
def index():
    return FileResponse(os.path.join(BASE_DIR, "index.html"))

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8765)
