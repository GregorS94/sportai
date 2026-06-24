"""Einfacher kicker.de-Scraper (Basis-Daten: Teams, Spielstand, Minute).

Hinweis: kicker.de liefert keine Detail-Stats wie xG, Ballbesitz oder
Gef. Angriffe. Für die vollständigen Stats wird später eine echte
Stats-API angebunden – aktuell kommen die Detail-Daten aus
`app.core.mock_data`.
"""

from __future__ import annotations

import requests
from bs4 import BeautifulSoup


def fetch_kicker_data() -> list[dict]:
    """Holt grundlegende Live-Spieldaten von kicker.de."""
    url = "https://www.kicker.de/livescores/fussball"
    try:
        response = requests.get(
            url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15
        )
        soup = BeautifulSoup(response.text, "html.parser")

        spiele: list[dict] = []
        for container in soup.select("div.livebox"):
            try:
                team1 = container.select_one("span.team.left").get_text(strip=True)
                team2 = container.select_one("span.team.right").get_text(strip=True)
                score = container.select_one("div.score").get_text(strip=True)
                minute = container.select_one("div.time").get_text(strip=True)
                spiele.append(
                    {
                        "team1": team1,
                        "team2": team2,
                        "score": score,
                        "minute": minute,
                    }
                )
            except AttributeError:
                continue

        return spiele

    except Exception as exc:  # noqa: BLE001 - bewusst breit für Robustheit
        return [{"error": str(exc)}]
