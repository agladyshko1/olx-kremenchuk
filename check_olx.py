"""–Я–µ—А–µ–≤—Ц—А—П—Ф –љ–Њ–≤—Ц –Њ–≥–Њ–ї–Њ—И–µ–љ–љ—П –Њ—А–µ–љ–і–Є –Ї–≤–∞—А—В–Є—А –љ–∞ OLX —Ц –љ–∞–і—Б–Є–ї–∞—Ф —Ч—Е —Г Telegram."""
import json
import os
import time
from html import escape

import requests
from bs4 import BeautifulSoup

DEFAULT_URL = (
    "https://www.olx.ua/uk/nedvizhimost/kvartiry/dolgosrochnaya-arenda-kvartir/kremenchug/"
    "?currency=UAH&search%5Border%5D=created_at:desc&search%5Bfilter_float_price:to%5D=12000"
)
OLX_URL = os.environ.get("OLX_URL") or DEFAULT_URL
TG_TOKEN = os.environ["TELEGRAM_TOKEN"]
TG_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

STATE_FILE = "seen.json"
MAX_SEEN = 3000
FAILS_BEFORE_ALERT = 3
# –Ю–≥–Њ–ї–Њ—И–µ–љ–љ—П –Ј —Ж–Є–Љ–Є —Б–ї–Њ–≤–∞–Љ–Є –≤ –љ–∞–Ј–≤—Ц –њ—А–Њ–њ—Г—Б–Ї–∞—Ф–Љ–Њ
EXCLUDE_WORDS = ["–њ–Њ–і–Њ–±–Њ–≤", "–њ–Њ—Б—Г—В–Њ—З", "–Ї—Ц–Љ–љ–∞—В", "–Ї–Њ–Љ–љ–∞—В", "–≥—Г—А—В–Њ–ґ–Є—В", "–Њ–±—Й–µ–ґ–Є—В", "–ї—Ц–ґ–Ї–Њ-–Љ—Ц—Б—Ж–µ", "–Ї–Њ–є–Ї–Њ"]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "uk-UA,uk;q=0.9",
}


def load_state():
    try:
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return None


def save_state(state):
    state["ids"] = state["ids"][-MAX_SEEN:]
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=0)


def text_of(card, selector):
    el = card.select_one(selector)
    return el.get_text(" ", strip=True) if el else ""


def fetch_ads():
    resp = requests.get(OLX_URL, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    ads = []
    for card in soup.select('div[data-cy="l-card"]'):
        link_el = card.select_one('[data-testid="card-title-link"]') or card.find("a", href=True)
        if not link_el:
            continue
        link = link_el["href"].split("#")[0].split("?")[0]
        if link.startswith("/"):
            link = "https://www.olx.ua" + link
        ads.append({
            "id": card.get("id") or link,
            "link": link,
            "title": text_of(card, '[data-testid="card-title-link"]') or text_of(card, "h4, h6") or "–С–µ–Ј –љ–∞–Ј–≤–Є",
            "price": text_of(card, '[data-testid="ad-price"]'),
            "place": text_of(card, '[data-testid="location-date"]'),
        })
    return ads


def send(text):
    r = requests.post(
        f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
        json={"chat_id": TG_CHAT_ID, "text": text, "parse_mode": "HTML"},
        timeout=30,
    )
    if not r.ok:
        print("Telegram error:", r.status_code, r.text[:300])


def main():
    state = load_state() or {"ids": [], "fails": 0}
    # –Я–Њ—А–Њ–ґ–љ—Ц–є —Б–њ–Є—Б–Њ–Ї = —Й–µ –ґ–Њ–і–љ–Њ–≥–Њ —А–∞–Ј—Г –љ–µ –њ—А–Њ—З–Є—В–∞–ї–Є OLX (–љ–∞–≤—Ц—В—М —П–Ї—Й–Њ seen.json –≤–ґ–µ —Ф –њ—Ц—Б–ї—П –њ–Њ–Љ–Є–ї–Ї–Є)
    first_run = not state["ids"]

    try:
        ads = fetch_ads()
        if not ads:
            raise RuntimeError("–љ–∞ —Б—В–Њ—А—Ц–љ—Ж—Ц –љ–µ –Ј–љ–∞–є–і–µ–љ–Њ –ґ–Њ–і–љ–Њ–≥–Њ –Њ–≥–Њ–ї–Њ—И–µ–љ–љ—П")
    except Exception as e:  # –Љ–µ—А–µ–ґ–∞, –±–ї–Њ–Ї—Г–≤–∞–љ–љ—П, –Ј–Љ—Ц–љ–∞ —Б—В–Њ—А—Ц–љ–Ї–Є OLX
        state["fails"] = state.get("fails", 0) + 1
        print("–Я–Њ–Љ–Є–ї–Ї–∞:", e)
        if state["fails"] == FAILS_BEFORE_ALERT:
            send(f"вЪ†пЄП –С–Њ—В –љ–µ –Љ–Њ–ґ–µ –њ—А–Њ—З–Є—В–∞—В–Є OLX —Г–ґ–µ {FAILS_BEFORE_ALERT} —А–∞–Ј–Є –њ–Њ—Б–њ—Ц–ї—М.\n–Я—А–Є—З–Є–љ–∞: {escape(str(e))}")
        save_state(state)
        return

    if state.get("fails", 0) >= FAILS_BEFORE_ALERT:
        send("вЬЕ –С–Њ—В –Ј–љ–Њ–≤—Г —З–Є—В–∞—Ф OLX.")
    state["fails"] = 0

    seen = set(state["ids"])
    new_ads = [a for a in ads if a["id"] not in seen]
    state["ids"].extend(a["id"] for a in new_ads)

    if first_run:
        send(f"рЯ§Ц –С–Њ—В –Ј–∞–њ—Г—Й–µ–љ–Њ. –Ч–∞—А–∞–Ј –љ–∞ OLX {len(ads)} –Њ–≥–Њ–ї–Њ—И–µ–љ—М –Ј–∞ —В–≤–Њ—Ч–Љ –њ–Њ—И—Г–Ї–Њ–Љ вАФ "
             "—П —Ч—Е –Ј–∞–њ–∞–Љ'—П—В–∞–≤ —Ц –љ–∞–і—Б–Є–ї–∞—В–Є–Љ—Г —В—Ц–ї—М–Ї–Є –љ–Њ–≤—Ц.")
        save_state(state)
        return

    for ad in reversed(new_ads):  # —Б—В–∞—А—Ц—И—Ц —Б–њ–Њ—З–∞—В–Ї—Г
        if any(w in ad["title"].lower() for w in EXCLUDE_WORDS):
            continue
        send(
            f"рЯП† <b>{escape(ad['title'])}</b>\n"
            f"рЯТ∞ {escape(ad['price'])}\n"
            f"рЯУН {escape(ad['place'])}\n"
            f"{ad['link']}"
        )
        time.sleep(1)

    print(f"–Ю–≥–Њ–ї–Њ—И–µ–љ—М –љ–∞ —Б—В–Њ—А—Ц–љ—Ж—Ц: {len(ads)}, –љ–Њ–≤–Є—Е: {len(new_ads)}")
    save_state(state)


if __name__ == "__main__":
    main()
