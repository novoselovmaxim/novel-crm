"""Email communications — send, list, detail."""
import asyncio
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import get_current_user
from ..database import get_db, settings
from ..email_sender import send_email
from ..models import Company, EmailCommunication, EmailEvent, User
from ..schemas import (
    EmailCommunicationResponse,
    EmailEventResponse,
    EmailSendRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/communications", tags=["communications"])


@router.post("/send", response_model=EmailCommunicationResponse)
async def send_email_endpoint(
    req: EmailSendRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Company).where(Company.id == req.company_id, Company.is_deleted == False)
    )
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    comm = EmailCommunication(
        company_id=req.company_id,
        user_id=current_user.id,
        sender_email=settings.smtp_user or "info@intpaypro.ru",
        recipient_email=req.recipient_email,
        subject=req.subject,
        body_html=req.body_html,
        body_text=req.body_text,
    )
    db.add(comm)
    await db.commit()
    await db.refresh(comm)

    comm_id = comm.id
    hostname = settings.base_url.replace("https://", "").replace("http://", "").split("/")[0]
    message_id = f"<{comm_id}@{hostname}>"
    comm.message_id = message_id
    await db.commit()
    modified_html = _inject_tracking(req.body_html, comm_id)

    def _send():
        from ..email_sender import _send_via_smtp
        try:
            _send_via_smtp(
                recipient_email=req.recipient_email,
                subject=req.subject,
                html_body=modified_html,
                text_body=req.body_text,
                message_id=message_id,
            )
        except Exception as e:
            logger.exception(f"Failed to send email {comm_id}")
            raise

    try:
        await asyncio.to_thread(_send)
        comm.status = "sent"
    except Exception:
        comm.status = "failed"
        await db.commit()
        raise HTTPException(status_code=500, detail="Ошибка отправки email")

    await db.commit()
    await db.refresh(comm)
    return comm


@router.get("/{company_id}", response_model=list[EmailCommunicationResponse])
async def list_communications(
    company_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(EmailCommunication)
        .where(EmailCommunication.company_id == company_id)
        .order_by(EmailCommunication.sent_at.desc())
    )
    return result.scalars().all()


@router.get("/detail/{comm_id}", response_model=EmailCommunicationResponse)
async def get_communication(
    comm_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(EmailCommunication).where(EmailCommunication.id == comm_id))
    comm = result.scalar_one_or_none()
    if not comm:
        raise HTTPException(status_code=404, detail="Email not found")
    return comm


@router.get("/{company_id}/events", response_model=list[EmailEventResponse])
async def list_communication_events(
    company_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(EmailEvent)
        .join(EmailCommunication)
        .where(EmailCommunication.company_id == company_id)
        .order_by(EmailEvent.created_at.desc())
    )
    return result.scalars().all()


def _inject_tracking(html: str, comm_id: uuid.UUID) -> str:
    tracking_url = f"{settings.base_url}/api/track/open/{comm_id}"
    base_click_url = f"{settings.base_url}/api/track/click/{comm_id}"

    import re
    def replace_link(match):
        href = match.group(1)
        import urllib.parse
        new_href = f"{base_click_url}?url={urllib.parse.quote(href, safe='')}"
        return f'href="{new_href}"'

    html = re.sub(r'href="([^"]+)"', replace_link, html)
    pixel = f'<img src="{tracking_url}" width="1" height="1" style="display:none" alt=""/>'
    html = html.replace("</body>", f"{pixel}</body>") if "</body>" in html else html + pixel
    return html
