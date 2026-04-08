from __future__ import annotations

import requests
from bs4 import BeautifulSoup
from dataclasses import dataclass
from typing import Optional, List


@dataclass
class Match:
    league: str
    team_home: str
    team_away: str
    score_home: Optional[int]
    score_away: Optional[int]
    status: str  # z.B. "Live", "45'", "Beendet", "18:30"


class KickerScraper:
    """Scraper für Live-Ergebnisse von kicker.de"""

    BASE_URL = "https://www.kicker.de"
    LIVESCORES_URL = f"{BASE_URL}/livescores/fussball"
    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "de-DE,de;q=0.9",
    }

    def fetch_live_scores(self) -> List[Match]:
        """Holt aktuelle Live-Ergebnisse von kicker.de."""
        try:
            resp = requests.get(
                self.LIVESCORES_URL, headers=self.HEADERS, timeout=10
            )
            resp.raise_for_status()
        except requests.RequestException as e:
            raise ConnectionError(f"Fehler beim Abruf von kicker.de: {e}") from e

        return self._parse_html(resp.text)

    def _parse_html(self, html: str) -> List[Match]:
        """Parsed HTML und extrahiert Spieldaten."""
        soup = BeautifulSoup(html, "html.parser")
        matches: List[Match] = []
        current_league = "Unbekannt"

        # Kicker strukturiert nach Ligen-Blöcken
        for section in soup.select(
            "[class*='LiveScores'], [class*='livescore'], "
            "[class*='kick__v100'], section, .kick__module"
        ):
            # Liga-Header finden
            league_el = section.select_one(
                "h3, [class*='league'], [class*='Liga'], "
                "[class*='competition'], .kick__module__header"
            )
            if league_el:
                current_league = league_el.get_text(strip=True)

            # Spiele in dieser Sektion
            for row in section.select(
                "[class*='MatchRow'], [class*='matchRow'], "
                "[class*='kick__v100__game'], tr[class*='match'], "
                ".kick__v100__topgame, [class*='livebox']"
            ):
                match = self._parse_match_row(row, current_league)
                if match:
                    matches.append(match)

        # Fallback: Wenn strukturierte Suche nichts findet,
        # versuche generische Suche
        if not matches:
            matches = self._parse_fallback(soup)

        return matches

    def _parse_match_row(self, row, league: str) -> Optional[Match]:
        """Parsed eine einzelne Spielzeile."""
        try:
            # Teams finden
            teams = row.select(
                "[class*='team'], [class*='Team'], "
                "span.team, td.team, .kick__v100__gameCell__team"
            )
            if len(teams) < 2:
                # Alternative: Links zu Mannschaftsseiten
                team_links = row.select("a[href*='/verein/']")
                if len(team_links) >= 2:
                    teams = team_links

            if len(teams) < 2:
                return None

            team_home = teams[0].get_text(strip=True)
            team_away = teams[1].get_text(strip=True)

            if not team_home or not team_away:
                return None

            # Score finden
            score_el = row.select_one(
                "[class*='score'], [class*='Score'], "
                "[class*='result'], .kick__v100__gameCell__scores"
            )
            score_home, score_away = None, None
            if score_el:
                score_text = score_el.get_text(strip=True)
                parts = score_text.replace(":", "-").split("-")
                if len(parts) == 2:
                    try:
                        score_home = int(parts[0].strip())
                        score_away = int(parts[1].strip())
                    except ValueError:
                        pass

            # Status finden (Minute, Live, Beendet, etc.)
            status_el = row.select_one(
                "[class*='minute'], [class*='time'], [class*='status'], "
                "[class*='Minute'], [class*='Time'], [class*='Status'], "
                ".kick__v100__gameCell__matchTime"
            )
            status = status_el.get_text(strip=True) if status_el else "—"

            return Match(
                league=league,
                team_home=team_home,
                team_away=team_away,
                score_home=score_home,
                score_away=score_away,
                status=status,
            )
        except Exception:
            return None

    def _parse_fallback(self, soup: BeautifulSoup) -> List[Match]:
        """Fallback-Parser wenn die strukturierte Suche nichts findet."""
        matches: List[Match] = []

        for container in soup.select(
            "div[class*='live'], div[class*='match'], "
            "div[class*='game'], div[class*='spiel']"
        ):
            teams = container.select(
                "span, a[href*='/verein/'], [class*='team']"
            )
            team_texts = [
                t.get_text(strip=True)
                for t in teams
                if len(t.get_text(strip=True)) > 2
            ]

            if len(team_texts) >= 2:
                matches.append(
                    Match(
                        league="Fußball",
                        team_home=team_texts[0],
                        team_away=team_texts[1],
                        score_home=None,
                        score_away=None,
                        status="—",
                    )
                )

        return matches


def get_demo_data() -> List[Match]:
    """Liefert Demo-Daten für Entwicklung und Tests."""
    return [
        Match("Bundesliga", "Bayern München", "Borussia Dortmund", 2, 1, "67'"),
        Match("Bundesliga", "RB Leipzig", "Bayer Leverkusen", 0, 0, "32'"),
        Match("Bundesliga", "VfB Stuttgart", "Eintracht Frankfurt", 1, 3, "HZ"),
        Match("2. Bundesliga", "Hamburger SV", "1. FC Köln", 1, 0, "55'"),
        Match("2. Bundesliga", "Hertha BSC", "Schalke 04", None, None, "18:30"),
        Match("Champions League", "Real Madrid", "Manchester City", 1, 1, "78'"),
        Match("Champions League", "PSG", "Inter Mailand", 0, 2, "Beendet"),
        Match("Premier League", "Arsenal", "Liverpool", 2, 2, "90+3'"),
    ]
