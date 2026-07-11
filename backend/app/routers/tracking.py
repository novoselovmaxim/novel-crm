"""Email tracking endpoints — open tracking pixel and click redirect."""
import base64
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import RedirectResponse, Response

from ..database import get_db
from ..models import EmailCommunication, EmailEvent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/track", tags=["tracking"])

TRACKING_PIXEL = base64.b64decode(
    "R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"
)


@router.get("/open/{comm_id}")
async def track_open(comm_id: uuid.UUID, request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(EmailCommunication).where(EmailCommunication.id == comm_id))
    comm = result.scalar_one_or_none()
    if not comm:
        return Response(content=TRACKING_PIXEL, media_type="image/gif")
    comm.opened_at = comm.opened_at or __import__("datetime").datetime.now()
    comm.status = "opened" if comm.status == "sent" else comm.status
    event = EmailEvent(
        communication_id=comm_id,
        event_type="open",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    db.add(event)
    await db.commit()
    return Response(content=TRACKING_PIXEL, media_type="image/gif")


@router.get("/click/{comm_id}")
async def track_click(comm_id: uuid.UUID, request: Request, db: AsyncSession = Depends(get_db)):
    url = request.query_params.get("url")
    if not url:
        raise HTTPException(status_code=400, detail="Missing url parameter")
    result = await db.execute(select(EmailCommunication).where(EmailCommunication.id == comm_id))
    comm = result.scalar_one_or_none()
    if comm:
        comm.clicked_at = comm.clicked_at or __import__("datetime").datetime.now()
        comm.status = "clicked" if comm.status in ("sent", "opened") else comm.status
        event = EmailEvent(
            communication_id=comm_id,
            event_type="click",
            link_url=url,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        db.add(event)
        await db.commit()
    return RedirectResponse(url=url)
