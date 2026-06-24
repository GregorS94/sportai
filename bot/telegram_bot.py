"""Telegram-Bot: postet pro Spiel exakt das Stat-Layout aus der Grafik.

Konfiguration über Umgebungsvariablen:

    TELEGRAM_BOT_TOKEN   – Token von @BotFather (Pflicht)
    TELEGRAM_CHAT_ID     – Ziel-Chat/Kanal-ID (Pflicht)

Nutzung:

    # Einmalig alle aktuellen Spiele posten:
    python -m bot.telegram_bot

    # Nur die Nachricht(en) in der Konsole ausgeben (kein Versand):
    python -m bot.telegram_bot --dry-run
"""

from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests

from app.core import format_match, get_matches

TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"


def send_message(token: str, chat_id: str, text: str) -> dict:
    """Sendet eine Nachricht an einen Telegram-Chat."""
    response = requests.post(
        TELEGRAM_API.format(token=token),
        json={"chat_id": chat_id, "text": text},
        timeout=15,
    )
    response.raise_for_status()
    return response.json()


def main() -> int:
    parser = argparse.ArgumentParser(description="SportAI Telegram-Bot")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Nachrichten nur ausgeben statt senden",
    )
    args = parser.parse_args()

    matches = get_matches()
    if not matches:
        print("Keine Spiele gefunden.")
        return 0

    if args.dry_run:
        for match in matches:
            print(format_match(match))
            print("\n" + "=" * 40 + "\n")
        return 0

    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print(
            "Fehler: TELEGRAM_BOT_TOKEN und TELEGRAM_CHAT_ID müssen gesetzt sein.\n"
            "Tipp: Zum Testen ohne Versand `--dry-run` verwenden.",
            file=sys.stderr,
        )
        return 1

    for match in matches:
        result = send_message(token, chat_id, format_match(match))
        ok = result.get("ok", False)
        print(f"Gesendet: {match.home.name} vs {match.away.name} -> ok={ok}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
