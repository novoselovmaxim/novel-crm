import uuid
from datetime import date, time, timedelta, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, and_

from ..database import get_db
from ..models import User, Company, AvailabilitySlot, Meeting
from ..auth import get_current_user, require_admin_or_lead
from ..notifications import notifier

router = APIRouter(prefix="/api/availability", tags=["availability"])


class SlotCreate(BaseModel):
    day_of_week: int  # 0=Monday
    time_start: str  # "09:00"
    time_end: str    # "18:00"


class BookMeeting(BaseModel):
    company_id: str
    date: str  # "2026-05-25"
    hour: int  # 0-23


@router.get("/slots")
async def get_all_slots(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(AvailabilitySlot))
    slots = result.scalars().all()
    users = {}
    result = await db.execute(select(User).where(User.role.in_(["admin", "lead"]), User.is_active == True))
    for u in result.scalars().all():
        users[str(u.id)] = {"id": str(u.id), "name": u.name or u.email}

    by_user: dict[str, list] = {}
    for s in slots:
        uid = str(s.user_id)
        by_user.setdefault(uid, []).append({
            "day_of_week": s.day_of_week,
            "time_start": s.time_start.strftime("%H:%M"),
            "time_end": s.time_end.strftime("%H:%M"),
        })

    return {
        "users": list(users.values()),
        "slots": by_user,
    }


@router.get("/slots/my")
async def get_my_slots(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AvailabilitySlot).where(AvailabilitySlot.user_id == current_user.id)
    )
    slots = result.scalars().all()
    return [
        {
            "day_of_week": s.day_of_week,
            "time_start": s.time_start.strftime("%H:%M"),
            "time_end": s.time_end.strftime("%H:%M"),
        }
        for s in slots
    ]


@router.put("/slots/my")
async def set_my_slots(
    slots: list[SlotCreate],
    current_user: User = Depends(require_admin_or_lead),
    db: AsyncSession = Depends(get_db),
):
    await db.execute(delete(AvailabilitySlot).where(AvailabilitySlot.user_id == current_user.id))
    for s in slots:
        ts = time.fromisoformat(s.time_start)
        te = time.fromisoformat(s.time_end)
        db.add(AvailabilitySlot(user_id=current_user.id, day_of_week=s.day_of_week, time_start=ts, time_end=te))
    await db.commit()
    return {"status": "ok"}


@router.get("/calendar")
async def get_calendar(
    week_start: str = Query(..., description="Monday of the week, YYYY-MM-DD"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    start = date.fromisoformat(week_start)
    # Monday = 0
    # Adjust so week_start is always Monday
    days_since_monday = start.weekday()
    start = start - timedelta(days=days_since_monday)
    end = start + timedelta(days=6)

    # Get all users with availability (admin + lead)
    result = await db.execute(
        select(User).where(User.role.in_(["admin", "lead"]), User.is_active == True)
    )
    avail_users = result.scalars().all()

    # Get all availability slots
    result = await db.execute(select(AvailabilitySlot))
    all_slots = result.scalars().all()

    # Get meetings in this week
    result = await db.execute(
        select(Meeting).where(
            Meeting.date >= start, Meeting.date <= end
        )
    )
    meetings = result.scalars().all()
    booked = {(m.date, m.hour) for m in meetings}

    # Build per-user per-day-of-week lookup
    user_slots: dict[str, dict[int, tuple[int, int]]] = {}
    for u in avail_users:
        uid = str(u.id)
        user_slots[uid] = {}
    for s in all_slots:
        uid = str(s.user_id)
        if uid not in user_slots:
            continue
        user_slots[uid][s.day_of_week] = (s.time_start.hour, s.time_end.hour)

    # Build response
    days = []
    for i in range(7):
        d = start + timedelta(days=i)
        dow = d.weekday()
        slots = []
        available_users = []
        for u in avail_users:
            uid = str(u.id)
            slot_range = user_slots.get(uid, {}).get(dow)
            if slot_range:
                available_users.append({"id": uid, "name": u.name or u.email, "range": slot_range})

        if not available_users:
            days.append({"date": d.isoformat(), "slots": []})
            continue

        # Find the overall hour range
        min_hour = min(u["range"][0] for u in available_users)
        max_hour = max(u["range"][1] for u in available_users)

        for h in range(min_hour, max_hour):
            if (d, h) in booked:
                continue
            who = [u["id"] for u in available_users if u["range"][0] <= h < u["range"][1]]
            if who:
                slots.append({"hour": h, "users": who})

        days.append({"date": d.isoformat(), "slots": slots})

    return {
        "week_start": start.isoformat(),
        "users": [{"id": str(u.id), "name": u.name or u.email} for u in avail_users],
        "days": days,
    }


@router.post("/book")
async def book_meeting(
    body: BookMeeting,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    meeting_date = date.fromisoformat(body.date)

    # Check slot is still free
    result = await db.execute(
        select(Meeting).where(Meeting.date == meeting_date, Meeting.hour == body.hour)
    )
    if result.scalar_one_or_none():
        raise HTTPException(409, "This slot is already booked")

    # Verify company exists
    result = await db.execute(
        select(Company).where(Company.id == body.company_id, Company.is_deleted == False)
    )
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(404, "Company not found")

    meeting = Meeting(
        company_id=body.company_id,
        booked_by=current_user.id,
        date=meeting_date,
        hour=body.hour,
    )
    db.add(meeting)

    company.call_status = "meeting"
    company.next_call_date = meeting_date

    await db.commit()
    await db.refresh(meeting)

    admin_ids = []
    admins = await db.execute(select(User.id).where(User.role.in_(["admin", "lead"])))
    admin_ids = [u for u in admins.scalars().all() if u != current_user.id]

    await notifier.notify_meeting(
        f"📅 Назначена встреча с {company.name}\n"
        f"🗓 {meeting_date} в {body.hour}:00",
        manager_id=current_user.id,
        admin_ids=admin_ids,
    )

    return {"status": "ok", "meeting_id": str(meeting.id)}


@router.get("/meetings")
async def get_meetings(
    date_from: str = Query(...),
    date_to: str = Query(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Meeting).where(Meeting.date >= date.fromisoformat(date_from), Meeting.date <= date.fromisoformat(date_to))
    )
    meetings = result.scalars().all()
    result_data = []
    for m in meetings:
        c_result = await db.execute(select(Company).where(Company.id == m.company_id))
        company = c_result.scalar_one_or_none()
        u_result = await db.execute(select(User).where(User.id == m.booked_by))
        user = u_result.scalar_one_or_none()
        result_data.append({
            "id": str(m.id),
            "date": m.date.isoformat(),
            "hour": m.hour,
            "company_id": str(m.company_id),
            "company_name": company.name if company else "Deleted",
            "booked_by": user.name or user.email if user else "Unknown",
            "notes": m.notes,
        })
    return result_data


@router.delete("/meetings/{meeting_id}")
async def cancel_meeting(
    meeting_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Meeting).where(Meeting.id == meeting_id))
    meeting = result.scalar_one_or_none()
    if not meeting:
        raise HTTPException(404, "Meeting not found")

    c_result = await db.execute(select(Company).where(Company.id == meeting.company_id))
    company = c_result.scalar_one_or_none()
    if company:
        company.call_status = "new"

    await db.delete(meeting)
    await db.commit()
    return {"status": "ok"}


@router.get("/meetings/by-company/{company_id}")
async def get_meeting_by_company(
    company_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Meeting).where(Meeting.company_id == company_id).order_by(Meeting.date.desc())
    )
    meeting = result.scalars().first()
    if not meeting:
        raise HTTPException(404, "No meeting found for this company")

    u_result = await db.execute(select(User).where(User.id == meeting.booked_by))
    user = u_result.scalar_one_or_none()

    return {
        "id": str(meeting.id),
        "date": meeting.date.isoformat(),
        "hour": meeting.hour,
        "booked_by": user.name or user.email if user else "Unknown",
        "notes": meeting.notes,
    }


@router.patch("/meetings/{meeting_id}")
async def update_meeting(
    meeting_id: str,
    body: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Meeting).where(Meeting.id == meeting_id))
    meeting = result.scalar_one_or_none()
    if not meeting:
        raise HTTPException(404, "Meeting not found")
    if "notes" in body:
        meeting.notes = body["notes"]
    await db.commit()
    return {"status": "ok"}
