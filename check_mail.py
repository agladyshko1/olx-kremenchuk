"""Пересилає в Telegram листи OLX про нові оголошення з Gmail (за IMAP)."""
import email
import imaplib
import os
import re
import time
from email.header import decode_header, make_header
from html import escape, unescape

import requests

GMAIL_USER = os.environ["GMAIL_USER"]
GMAIL_APP_PASSWORD = os.environ["GMAIL_APP_PASSWORD"]
TG_TOKEN = os.environ["TELEGRAM_TOKEN"]
TG_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

# Листи від OLX за останні дні, які бот ще не позначив своєю міткою
LABEL = "tg-sent"
GMAIL_QUERY = f"from:olx.ua newer_than:3d -label:{LABEL}"
AD_LINK = re.compile(r"https?://(?:www\.)?olx\.ua/d/[^\s\"'<>)\]]+")


def body_of(msg):
    parts = []
    for part in msg.walk():
        if part.get_content_type() in ("text/html", "text/plain"):
            payload = part.get_payload(decode=True) or b""
            parts.append(payload.decode(part.get_content_charset() or "utf-8", errors="replace"))
    return unescape("\n".join(parts))


def send(text):
    r = requests.post(
        f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
        json={"chat_id": TG_CHAT_ID, "text": text, "parse_mode": "HTML"},
        timeout=30,
    )
    if not r.ok:
        raise RuntimeError(f"Telegram {r.status_code}: {r.text[:300]}")


def main():
    imap = imaplib.IMAP4_SSL("imap.gmail.com")
    imap.login(GMAIL_USER, GMAIL_APP_PASSWORD)
    imap.select("INBOX")
    _, data = imap.search(None, "X-GM-RAW", f'"{GMAIL_QUERY}"')
    ids = data[0].split()
    print(f"Нових листів від OLX: {len(ids)}")

    for num in ids:
        _, fetched = imap.fetch(num, "(BODY.PEEK[])")
        msg = email.message_from_bytes(fetched[0][1])
        subject = str(make_header(decode_header(msg.get("Subject", "")))) or "Нові оголошення OLX"
        body = body_of(msg)
        links = list(dict.fromkeys(m.split("?")[0] for m in AD_LINK.findall(body)))

        text = f"🏠 <b>{escape(subject)}</b>\n"
        if links:
            text += "\n".join(links[:10])
        else:  # формат листа невідомий — шлемо хоча б початок тексту
            plain = re.sub(r"<[^>]+>|\s+", " ", body).strip()
            text += escape(plain[:500])
        send(text)
        imap.store(num, "+X-GM-LABELS", LABEL)  # позначаємо лише після успішної відправки
        time.sleep(1)

    imap.logout()


if __name__ == "__main__":
    main()
