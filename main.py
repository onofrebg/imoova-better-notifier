import requests
from bs4 import BeautifulSoup
import sys
import argparse
import unicodedata
import json
import os
import time
from datetime import datetime, timedelta

# Default configuration values
DEFAULT_CONFIG_FILE = "config.json"
DEFAULT_SEEN_FILE = "seen_offers.json"

def load_config():
    """Load configuration from config.json file or environment variables."""
    config = {
        "telegram_token": os.getenv("TELEGRAM_TOKEN", ""),
        "telegram_chats": [c.strip() for c in os.getenv("TELEGRAM_CHATS", "").split(",") if c.strip()],
        "default_cities": [c.strip() for c in os.getenv("DEFAULT_CITIES", "").split(",") if c.strip()],
        "heartbeat_days": int(os.getenv("HEARTBEAT_DAYS", "7"))
    }
    
    config_file = os.getenv("CONFIG_FILE", DEFAULT_CONFIG_FILE)
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                file_config = json.load(f)
                config.update(file_config)
        except Exception as e:
            print(f"Warning: Could not load {config_file}: {e}")
    
    return config

# Load configuration
config = load_config()


def fetch_imoova_campers():
    url = "https://www.imoova.com/en/relocations/table?region=EU"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    response = requests.get(url, headers=headers, timeout=15)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    campers = []
    seen_ids = set()

    # Strategy: look for table rows and use columns
    for tr in soup.select("table tr"):
        cols = tr.find_all("td")
        # sample table: [id, origin, arrival, start, end, model, ...]
        if len(cols) >= 3:
            # Get both the ID and URL from first column
            offer_id = cols[0].get_text(strip=True)
            offer_url = ""
            link_elem = cols[0].find("a")
            if link_elem and link_elem.get("href"):
                offer_url = "https://www.imoova.com" + link_elem["href"] if not link_elem["href"].startswith("http") else link_elem["href"]
            
            origin = cols[1].get_text(strip=True)
            arrival = cols[2].get_text(strip=True)
            start = cols[3].get_text(strip=True) if len(cols) > 3 else ""
            end = cols[4].get_text(strip=True) if len(cols) > 4 else ""
            model = cols[5].get_text(strip=True) if len(cols) > 5 else ""
            days = cols[7].get_text(strip=True) if len(cols) > 7 else ""
            if offer_id and origin and arrival and origin.lower() != "origin":
                if offer_id not in seen_ids:
                    campers.append({
                        "id": offer_id,
                        "url": offer_url,
                        "origin": origin,
                        "arrival": arrival,
                        "start": start,
                        "end": end,
                        "model": model,
                        "days": days,
                    })
                    seen_ids.add(offer_id)
    return campers



def load_seen(path: str):
    if not os.path.exists(path):
        return set()
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return set(data if isinstance(data, list) else [])
    except Exception:
        return set()


def save_seen(seen_ids, path: str):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(list(seen_ids), f)
    except Exception:
        pass


def send_telegram_message(token: str, chat_id: str, text: str):
    if not token or not chat_id:
        return False, "missing token or chat_id"
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    try:
        r = requests.post(url, json=payload, timeout=10)
        if r.status_code == 200:
            return True, r.json()
        return False, r.text
    except Exception as e:
        return False, str(e)


def update_last_message_time():
    """Update the timestamp of the last sent message."""
    try:
        with open("last_message.json", "w", encoding='utf-8') as f:
            json.dump({"last_message_time": time.time()}, f)
    except Exception:
        pass

def get_last_message_time():
    """Get the timestamp of the last sent message."""
    try:
        with open("last_message.json", "r", encoding='utf-8') as f:
            data = json.load(f)
            return data.get("last_message_time")
    except Exception:
        return None

def check_and_send_alive_message(token: str, chats, heartbeat_days=7):
    """Check if we need to send a 'still alive' message and send it if needed."""
    last_time = get_last_message_time()
    if last_time is None:
        update_last_message_time()
        return
    
    now = time.time()
    seconds_ago = now - (heartbeat_days * 24 * 60 * 60)  # Convert days to seconds
    
    if last_time < seconds_ago:
        text = "🤖 ¡Sigo vivo! No he encontrado nuevas ofertas de campers esta semana, pero sigo buscando."
        results = send_to_chats(token, chats, text)
        if any(ok for _, ok, _ in results):
            update_last_message_time()

def send_to_chats(token: str, chats, text: str):
    """Send `text` to multiple chat ids. Returns a list of (chat_id, ok, resp) tuples."""
    results = []
    if not token or not chats:
        return results
    for chat in chats:
        ok, resp = send_telegram_message(token, chat, text)
        results.append((chat, ok, resp))
    if any(ok for _, ok, _ in results):
        update_last_message_time()
    return results


def normalize_city(name: str) -> str:
    """Normalize a city name for comparison: lowercase, strip accents and whitespace."""
    if not name:
        return ""
    name = name.strip().lower()
    name = unicodedata.normalize("NFKD", name)
    name = "".join(ch for ch in name if not unicodedata.combining(ch))
    return name


def filter_campers(campers, cities):
    """Return campers where origin or arrival matches any city in 'cities'.

    'cities' should be an iterable of raw city names; matching is accent- and case-insensitive.
    """
    # Use substring matching on normalized names for flexibility (captures variants)
    norm_cities = [normalize_city(c) for c in cities]
    filtered = []
    for c in campers:
        o = normalize_city(c.get("origin", ""))
        a = normalize_city(c.get("arrival", ""))
        for nc in norm_cities:
            if nc and (nc in o or nc in a):
                filtered.append(c)
                break
    return filtered


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape imoova relocations and optionally filter by cities")
    parser.add_argument("--config", help="Path to configuration file",
                        default=DEFAULT_CONFIG_FILE)
    parser.add_argument("--cities", help="Comma-separated list of cities to filter by (e.g. Madrid,Barcelona,Zurich)",
                        default=",".join(config["default_cities"]))
    parser.add_argument("--telegram-token", help="Telegram bot token to send notifications", 
                        default=config["telegram_token"])
    parser.add_argument("--telegram-chats", help="Comma-separated list of Telegram chat ids to send notifications to", 
                        default=",".join(str(chat) for chat in config["telegram_chats"]))
    parser.add_argument("--seen-file", help="Path to seen offers JSON file", 
                        default=DEFAULT_SEEN_FILE)
    args = parser.parse_args()

    # Build list of chat ids to send notifications to (comma-separated)
    chats = []
    if getattr(args, "telegram_chats", None):
        chats = [c.strip() for c in args.telegram_chats.split(",") if c.strip()]

    # Get and filter campers
    try:
        campers = fetch_imoova_campers()
        if not campers:
            error_msg = "No campers found. The page structure may have changed."
            print(error_msg)
            if args.telegram_token and chats:
                send_to_chats(args.telegram_token, chats, f"❌ Error: {error_msg}")
            sys.exit(1)
    except Exception as e:
        error_msg = f"Error fetching campers: {str(e)}"
        print(error_msg)
        if args.telegram_token and chats:
            send_to_chats(args.telegram_token, chats, f"❌ Error: {error_msg}")
        sys.exit(1)

    cities = [c.strip() for c in args.cities.split(",") if c.strip()]
    filtered = filter_campers(campers, cities) if cities else campers

    print(f"Found {len(filtered)} campers matching cities: {', '.join(cities)}")
    
    # Load seen offers before printing to show notification status
    # Always load the seen file so we can prune IDs that no longer exist on the site.
    seen = load_seen(args.seen_file)

    # Remove any seen IDs that no longer appear on the fetched campers (prune stale entries)
    current_ids = set(c.get('id') for c in campers if c.get('id'))
    stale = seen - current_ids
    if stale:
        for sid in list(stale):
            seen.discard(sid)
        save_seen(seen, args.seen_file)
        print(f"Removed {len(stale)} stale offers from {args.seen_file}: {', '.join(sorted(stale))}")
    
    for camper in filtered:
        camper_id = camper.get('id')
        was_seen = camper_id in seen if camper_id else False
        status = "🔔 Already notified" if was_seen else "🆕 Not yet notified"
        print(f"[{camper_id}] Origin: {camper['origin']} -> Arrival: {camper['arrival']} | {camper.get('start','')} - {camper.get('end','')} | {camper.get('model','')} | {status}")

    # If telegram args provided, send notifications for any new offers (not in seen file)
    if args.telegram_token and chats:
        # Check if we need to send a "still alive" message
        check_and_send_alive_message(args.telegram_token, chats, config.get("heartbeat_days", 7))
        
        seen = load_seen(args.seen_file)
        new = [c for c in filtered if c.get('id') and c.get('id') not in seen]
        for c in new:
            days_info = f"\nDuración: {c.get('days', '')} días" if c.get('days') else ""
            text = f"✨ <b>{c.get('origin')} -> {c.get('arrival')}</b>\n{c.get('start','')} - {c.get('end','')}\n{c.get('model','')}{days_info}\n\n<a href='{c.get('url', '')}'>Ver oferta</a>"
            # send and report result
            results = send_to_chats(args.telegram_token, chats, text)
            success_count = sum(1 for _chat, ok, _resp in results if ok)
            print(f"Offer [{c.get('id')}] notified to {success_count}/{len(results) if results else 0} chats")
            # mark as seen only if ALL notifications were successful
            if success_count == len(chats):
                seen.add(c.get('id'))
                print(f"✅ Offer [{c.get('id')}] successfully notified to all chats")
            else:
                print(f"⚠️ Offer [{c.get('id')}] not marked as seen - some notifications failed")
        save_seen(seen, args.seen_file)