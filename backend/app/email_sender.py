"""Send emails via SMTP."""
import logging
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.header import Header

from .database import settings

logger = logging.getLogger(__name__)


def _send_via_smtp(
    recipient_email: str,
    subject: str,
    html_body: str,
    text_body: str | None = None,
    sender_name: str = "ИНТПЭЙ",
    sender_email: str = "info@intpaypro.ru",
    message_id: str | None = None,
    attachments: list[tuple[str, str]] | None = None,
    inline_images: list[tuple[str, str]] | None = None,
):
    msg = MIMEMultipart("mixed")
    msg["From"] = Header(sender_name, "utf-8").encode() + f" <{sender_email}>"
    msg["To"] = recipient_email
    msg["Subject"] = subject
    msg["Reply-To"] = sender_email
    msg["X-Mailer"] = "Novel CRM"
    msg["Precedence"] = "bulk"
    msg["List-Unsubscribe"] = f"<mailto:{sender_email}?subject=unsubscribe>"
    if message_id:
        msg["Message-ID"] = message_id

    alternative = MIMEMultipart("alternative")
    if text_body:
        alternative.attach(MIMEText(text_body, "plain"))
    if html_body:
        alternative.attach(MIMEText(html_body, "html"))
    msg.attach(alternative)

    for path, filename in (attachments or []):
        with open(path, "rb") as f:
            part = MIMEApplication(f.read(), _subtype="pdf")
        part.add_header(
            "Content-Disposition",
            "attachment",
            filename=filename,
        )
        msg.attach(part)

    for path, cid in (inline_images or []):
        if not os.path.exists(path):
            continue
        with open(path, "rb") as f:
            img = MIMEImage(f.read())
        img.add_header("Content-ID", f"<{cid}>")
        img.add_header("Content-Disposition", "inline", filename=os.path.basename(path))
        msg.attach(img)

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as server:
        server.set_debuglevel(1)
        server.starttls()
        server.login(settings.smtp_user, settings.smtp_password)
        server.send_message(msg)
    logger.info(f"Email sent to {recipient_email}: {subject}")


def send_email(
    recipient_email: str,
    subject: str,
    html_body: str,
    text_body: str | None = None,
) -> None:
    _send_via_smtp(
        recipient_email=recipient_email,
        subject=subject,
        html_body=html_body,
        text_body=text_body,
    )


def send_cp_email(
    recipient_email: str,
    html_body: str,
    company_name: str,
    greeting: str = "Уважаемый",
    lpr_display_name: str = "клиент",
    message_id: str | None = None,
    inline_images: list[tuple[str, str]] | None = None,
) -> None:
    text = f"""Коммерческое предложение — валютные платежи от ИНТПЭЙ / ГК НОВЕЛЬ

Компания: {company_name}

{greeting} {lpr_display_name}!

Мы — ИНТПЭЙ, платёжное подразделение международного холдинга NOVEL GROUP.
Партнёрство с Арабским валютным фондом (AMF) гарантирует полную юридическую чистоту каждого перевода.

НАШИ ПРЕИМУЩЕСТВА:
- Экономия до 70% (комиссия от 0,5%)
- Скорость 1-3 дня
- Валютный контроль
- Любые направления

СХЕМА РАБОТЫ:
01 Заявка → ответ за 30 минут
02 Договор → тариф под ваш объём
03 Перевод → зачисление за 1-3 дня

ПОЧЕМУ НАМ ДОВЕРЯЮТ:
✓ 24 года на рынке
✓ Партнёрство с AMF
✓ Работаем через крупнейшие банки-партнёры

БАНКИ-ПАРТНЁРЫ: Альфа-Банк, Совкомбанк, МТС Банк

P.S. Пришлите один платёж — сделаем перевод за 0,5% и покажем разницу.

Сайт: intpaypro.ru
E-mail: info@intpaypro.ru
Telegram: @in_veritate (https://t.me/in_veritate)

Отправлено ИНТПЭЙ / ГК НОВЕЛЬ"""
    _send_via_smtp(
        recipient_email=recipient_email,
        subject="КП — о валютных платежах — ИНТПЭЙ — ГК НОВЕЛЬ",
        html_body=html_body,
        text_body=text,
        message_id=message_id,
        inline_images=inline_images,
    )


def send_presentation_email(
    recipient_email: str,
    html_body: str,
    attachment_path: str,
    company_name: str = "",
    greeting: str = "Уважаемый",
    lpr_display_name: str = "клиент",
    message_id: str | None = None,
    inline_images: list[tuple[str, str]] | None = None,
) -> None:
    if not os.path.exists(attachment_path):
        raise FileNotFoundError(f"Attachment not found: {attachment_path}")

    text = f"""Презентация — валютные платежи от ИНТПЭЙ / ГК НОВЕЛЬ

Компания: {company_name}

{greeting} {lpr_display_name}!

Направляем вам презентацию ИНТПЭЙ — платёжного подразделения международного холдинга NOVEL GROUP.
Партнёрство с Арабским валютным фондом (AMF) гарантирует полную юридическую чистоту каждого перевода.

НАШИ ПРЕИМУЩЕСТВА:
- Экономия до 70% (комиссия от 0,5%)
- Скорость 1-3 дня
- Валютный контроль
- Любые направления

СХЕМА РАБОТЫ:
01 Заявка → ответ за 30 минут
02 Договор → тариф под ваш объём
03 Перевод → зачисление за 1-3 дня

ПОЧЕМУ НАМ ДОВЕРЯЮТ:
✓ 24 года на рынке
✓ Партнёрство с AMF
✓ Работаем через крупнейшие банки-партнёры

БАНКИ-ПАРТНЁРЫ: Альфа-Банк, Совкомбанк, МТС Банк

Презентация компании — во вложении к этому письму.

Сайт: intpaypro.ru
E-mail: info@intpaypro.ru
Telegram: @in_veritate (https://t.me/in_veritate)

Отправлено ИНТПЭЙ / ГК НОВЕЛЬ"""
    _send_via_smtp(
        recipient_email=recipient_email,
        subject="Презентация — валютные платежи — ИНТПЭЙ — ГК НОВЕЛЬ",
        html_body=html_body,
        text_body=text,
        message_id=message_id,
        attachments=[(attachment_path, "ГК Новель.pdf")],
        inline_images=inline_images,
    )
