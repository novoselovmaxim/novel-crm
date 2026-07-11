"""IMAP bounce detection — poll mailbox for DSNs and update email status."""
import email as email_parser
import logging
import imaplib
import re
from datetime import datetime, timezone
from email.header import decode_header
from sqlalchemy import select

from .database import async_session, settings
from .models import EmailCommunication, EmailEvent

logger = logging.getLogger(__name__)

MESSAGE_ID_PATTERN = re.compile(r"<([a-f0-9\-]+)@novel\.maxnov\.ru>")


def _decode_str(val: str | bytes | None) -> str:
    if val is None:
        return ""
    if isinstance(val, bytes):
        val = val.decode("utf-8", errors="replace")
    decoded_parts = decode_header(val)
    parts = []
    for part, charset in decoded_parts:
        if isinstance(part, bytes):
            parts.append(part.decode(charset or "utf-8", errors="replace"))
        else:
            parts.append(str(part))
    return " ".join(parts)


def _extract_original_message_id(raw_email: bytes) -> str | None:
    msg = email_parser.message_from_bytes(raw_email)
    subject = _decode_str(msg.get("Subject", ""))
    logger.info(f"Bounce subject: {subject}")

    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            if ct == "message/delivery-status":
                payload = part.get_payload()
                if isinstance(payload, list):
                    for sub in payload:
                        if hasattr(sub, "as_string"):
                            for line in sub.as_string().split("\n"):
                                if "message-id" in line.lower():
                                    m = MESSAGE_ID_PATTERN.search(line)
                                    if m:
                                        return m.group(1)
                elif isinstance(payload, str):
                    for line in payload.split("\n"):
                        if "message-id" in line.lower():
                            m = MESSAGE_ID_PATTERN.search(line)
                            if m:
                                return m.group(1)

    for line in raw_email.decode("utf-8", errors="replace").split("\n"):
        m = MESSAGE_ID_PATTERN.search(line)
        if m:
            return m.group(1)

    return None


def _extract_bounce_info(raw_email: bytes) -> tuple[str | None, str | None]:
    msg = email_parser.message_from_bytes(raw_email)
    recipient = None
    status = None
    action = None

    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            if ct == "message/delivery-status":
                payload = part.get_payload()
                lines = ""
                if isinstance(payload, list):
                    for sub in payload:
                        if hasattr(sub, "as_string"):
                            lines += sub.as_string() + "\n"
                elif isinstance(payload, str):
                    lines = payload

                for line in lines.split("\n"):
                    if line.lower().startswith("final-recipient"):
                        recipient = line.split(":", 1)[1].strip().split()[-1]
                    elif line.lower().startswith("action"):
                        action = line.split(":", 1)[1].strip()
                    elif line.lower().startswith("status"):
                        status = line.split(":", 1)[1].strip()

    return recipient, status


async def poll_bounces():
    logger.info("Polling for bounces...")
    try:
        m = imaplib.IMAP4_SSL(settings.smtp_host, 993, timeout=30)
        m.login(settings.smtp_user, settings.smtp_password)
        m.select("INBOX")

        _, data = m.search(None, "UNSEEN")
        if not data[0]:
            logger.info("No unseen messages")
            m.logout()
            return

        ids = data[0].split()
        logger.info(f"Found {len(ids)} unseen messages")

        async with async_session() as db:
            for uid in ids:
                _, msg_data = m.fetch(uid, "(RFC822)")
                if not msg_data or not msg_data[0]:
                    continue
                raw_email = msg_data[0][1]
                if isinstance(raw_email, str):
                    raw_email = raw_email.encode("utf-8")

                comm_id = _extract_original_message_id(raw_email)
                if not comm_id:
                    continue

                try:
                    import uuid
                    comm_uuid = uuid.UUID(comm_id)
                except ValueError:
                    continue

                result = await db.execute(
                    select(EmailCommunication).where(EmailCommunication.id == comm_uuid)
                )
                comm = result.scalar_one_or_none()
                if not comm or comm.status == "bounced":
                    continue

                recipient, status_code = _extract_bounce_info(raw_email)
                comm.status = "bounced"
                comm.bounce_reason = status_code or "bounced"
                event = EmailEvent(
                    communication_id=comm_uuid,
                    event_type="bounce",
                    ip_address=None,
                    user_agent=None,
                )
                db.add(event)
                await db.commit()
                logger.info(f"Marked {comm_id} as bounced (recipient={recipient}, status={status_code})")

                m.store(uid, "+FLAGS", "\\Seen")
                m.copy(uid, "INBOX.Trash")
                m.store(uid, "+FLAGS", "\\Deleted")

        m.expunge()
        m.logout()
    except Exception:
        logger.exception("Bounce poll failed")
