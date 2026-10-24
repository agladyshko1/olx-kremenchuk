"""Одноразово: шле в Telegram відправників і теми останніх листів від OLX."""
import email
import imaplib
import os
from email.header import decode_header, make_header

import requests

imap = imaplib.IMAP4_SSL("imap.gmail.com")
imap.login(os.environ["GMAIL_USER"], os.environ["GMAIL_APP_PASSWORD"])
imap.select("INBOX", readonly=True)
_, data = imap.search(None, "X-GM-RAW", '"from:olx.ua newer_than:30d"')
ids = data[0].split()[-15:]
lines = []
for num in ids:
    _, f = imap.fetch(num, "(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE)])")
    m = email.message_from_bytes(f[0][1])
    hdr = lambda k: str(make_header(decode_header(m.get(k, ""))))
    lines.append(f"{hdr('Date')[:22]} | {hdr('From')[:40]} | {hdr('Subject')[:80]}")
text = f"Листів від OLX за 30 днів: {len(data[0].split())}\n\n" + "\n".join(lines)
r = requests.post(
    f"https://api.telegram.org/bot{os.environ['TELEGRAM_TOKEN']}/sendMessage",
    json={"chat_id": os.environ["TELEGRAM_CHAT_ID"], "text": text[:4000]},
    timeout=30,
)
print("Telegram:", r.status_code)
