"""Перевіряє нові оголошення оренди квартир на OLX і надсилає їх у Telegram."""
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
# Оголошення з цими словами в назві пропускаємо
EXCLUDE_WORDS = ["подобов", "посуточ", "кімнат", "комнат", "гуртожит", "общежит", "ліжко-місце", "койко"]

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
            "title": text_of(card, '[data-testid="card-title-link"]') or text_of(card, "h4, h6") or "Без назви",
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
    state = load_state()
    first_run = state is None
    if first_run:
        state = {"ids": [], "fails": 0}

    try:
        ads = fetch_ads()
        if not ads:
            raise RuntimeError("на сторінці не знайдено жодного оголошення")
    except Exception as e:  # мережа, блокування, зміна сторінки OLX
        state["fails"] = state.get("fails", 0) + 1
        print("Помилка:", e)
        if state["fails"] == FAILS_BEFORE_ALERT:
            send(f"⚠️ Бот не може прочитати OLX уже {FAILS_BEFORE_ALERT} рази поспіль.\nПричина: {escape(str(e))}")
        save_state(state)
        return

    if state.get("fails", 0) >= FAILS_BEFORE_ALERT:
        send("✅ Бот знову читає OLX.")
    state["fails"] = 0

    seen = set(state["ids"])
    new_ads = [a for a in ads if a["id"] not in seen]
    state["ids"].extend(a["id"] for a in new_ads)

    if first_run:
        send(f"🤖 Бот запущено. Зараз на OLX {len(ads)} оголошень за твоїм пошуком — "
             "я їх запам'ятав і надсилатиму тільки нові.")
        save_state(state)
        return

    for ad in reversed(new_ads):  # старіші спочатку
        if any(w in ad["title"].lower() for w in EXCLUDE_WORDS):
            continue
        send(
            f"🏠 <b>{escape(ad['title'])}</b>\n"
            f"💰 {escape(ad['price'])}\n"
            f"📍 {escape(ad['place'])}\n"
            f"{ad['link']}"
        )
        time.sleep(1)

    print(f"Оголошень на сторінці: {len(ads)}, нових: {len(new_ads)}")
    save_state(state)


if __name__ == "__main__":
    main()
