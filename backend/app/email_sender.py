"""Send emails via SMTP."""
import logging
import smtplib
from email.mime.text import MIMEText
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
):
    msg = MIMEMultipart("alternative")
    msg["From"] = Header(sender_name, "utf-8").encode() + f" <{sender_email}>"
    msg["To"] = recipient_email
    msg["Subject"] = subject
    msg["Reply-To"] = sender_email
    msg["X-Mailer"] = "Novel CRM"
    msg["Precedence"] = "bulk"
    msg["List-Unsubscribe"] = f"<mailto:{sender_email}?subject=unsubscribe>"
    if message_id:
        msg["Message-ID"] = message_id

    if text_body:
        msg.attach(MIMEText(text_body, "plain"))
    if html_body:
        msg.attach(MIMEText(html_body, "html"))

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
    )
