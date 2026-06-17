"""Send CP via SMTP email."""

import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header

from .database import settings

logger = logging.getLogger(__name__)


def send_cp_email(recipient_email: str, html_body: str, company_name: str) -> None:
    """Send CP HTML as email body via SMTP."""
    msg = MIMEMultipart("alternative")
    msg["From"] = f"{Header('ИНТПЭЙ', 'utf-8')} <info@intpaypro.ru>"
    msg["To"] = recipient_email
    msg["Subject"] = "КП — о валютных платежах — ИНТПЭЙ — ГК НОВЕЛЬ"
    msg["X-Mailer"] = "Novel CRM"
    msg["Precedence"] = "bulk"

    text = f"""Коммерческое предложение — валютные платежи от ИНТПЭЙ / ГК НОВЕЛЬ

Компания: {company_name}

Уважаемый клиент!

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
    msg.attach(MIMEText(text, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as server:
        server.set_debuglevel(1)
        server.starttls()
        server.login(settings.smtp_user, settings.smtp_password)
        server.send_message(msg)
        logger.info(f"Email sent to {recipient_email}")
