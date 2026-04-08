from __future__ import annotations

import requests
from bs4 import BeautifulSoup
from dataclasses import dataclass, field
from typing import Optional, List
import random


@dataclass
class MatchStats:
    attacks: int = 0
    dangerous_attacks: int = 0
    possession: int = 50
    shots_on_target: int = 0
    shots_off_target: int = 0
    corners: int = 0
    goals: int = 0
    yellow_cards: int = 0
    red_cards: int = 0
    offsides: int = 0
    fouls: int = 0
    saves: int = 0


@dataclass
class Match:
    minute: str
    team_home: str
    team_away: str
    score_home: int
    score_away: int
    country_home: str  # Emoji flag or country code
    country_away: str
    stats_home: MatchStats = field(default_factory=MatchStats)
    stats_away: MatchStats = field(default_factory=MatchStats)
    league: str = ""
    pinned: bool = False


# Country flag mapping
FLAGS = {
    "DE": "🇩🇪", "IT": "🇮🇹", "ES": "🇪🇸", "EN": "🇬🇧", "FR": "🇫🇷",
    "NL": "🇳🇱", "BE": "🇧🇪", "PT": "🇵🇹", "AT": "🇦🇹", "CH": "🇨🇭",
    "TR": "🇹🇷", "GR": "🇬🇷", "IE": "🇮🇪", "CO": "🇨🇴", "UY": "🇺🇾",
    "AR": "🇦🇷", "BR": "🇧🇷", "SE": "🇸🇪", "NO": "🇳🇴", "DK": "🇩🇰",
    "PL": "🇵🇱", "CZ": "🇨🇿", "HR": "🇭🇷", "RS": "🇷🇸", "RO": "🇷🇴",
    "SA": "🇸🇦", "JP": "🇯🇵", "KR": "🇰🇷", "US": "🇺🇸", "MX": "🇲🇽",
    "SC": "🏴󠁧󠁢󠁳󠁣󠁴󠁿",
}


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
        matches = []  # type: List[Match]
        current_league = "Unbekannt"

        for section in soup.select(
            "[class*='LiveScores'], [class*='livescore'], "
            "[class*='kick__v100'], section, .kick__module"
        ):
            league_el = section.select_one(
                "h3, [class*='league'], [class*='Liga'], "
                "[class*='competition'], .kick__module__header"
            )
            if league_el:
                current_league = league_el.get_text(strip=True)

            for row in section.select(
                "[class*='MatchRow'], [class*='matchRow'], "
                "[class*='kick__v100__game'], tr[class*='match'], "
                ".kick__v100__topgame, [class*='livebox']"
            ):
                match = self._parse_match_row(row, current_league)
                if match:
                    matches.append(match)

        if not matches:
            matches = self._parse_fallback(soup)

        return matches

    def _parse_match_row(self, row, league: str) -> Optional[Match]:
        """Parsed eine einzelne Spielzeile."""
        try:
            teams = row.select(
                "[class*='team'], [class*='Team'], "
                "span.team, td.team, .kick__v100__gameCell__team"
            )
            if len(teams) < 2:
                team_links = row.select("a[href*='/verein/']")
                if len(team_links) >= 2:
                    teams = team_links

            if len(teams) < 2:
                return None

            team_home = teams[0].get_text(strip=True)
            team_away = teams[1].get_text(strip=True)

            if not team_home or not team_away:
                return None

            score_el = row.select_one(
                "[class*='score'], [class*='Score'], "
                "[class*='result'], .kick__v100__gameCell__scores"
            )
            score_home, score_away = 0, 0
            if score_el:
                score_text = score_el.get_text(strip=True)
                parts = score_text.replace(":", "-").split("-")
                if len(parts) == 2:
                    try:
                        score_home = int(parts[0].strip())
                        score_away = int(parts[1].strip())
                    except ValueError:
                        pass

            status_el = row.select_one(
                "[class*='minute'], [class*='time'], [class*='status'], "
                "[class*='Minute'], [class*='Time'], [class*='Status'], "
                ".kick__v100__gameCell__matchTime"
            )
            minute = status_el.get_text(strip=True) if status_el else "0'"

            return Match(
                minute=minute,
                team_home=team_home,
                team_away=team_away,
                score_home=score_home,
                score_away=score_away,
                country_home="🏳️",
                country_away="🏳️",
                league=league,
            )
        except Exception:
            return None

    def _parse_fallback(self, soup: BeautifulSoup) -> List[Match]:
        """Fallback-Parser."""
        matches = []  # type: List[Match]

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
                        minute="0'",
                        team_home=team_texts[0],
                        team_away=team_texts[1],
                        score_home=0,
                        score_away=0,
                        country_home="🏳️",
                        country_away="🏳️",
                    )
                )

        return matches


def _rand_stats(minute: int, is_dominant: bool = False) -> MatchStats:
    """Generiert realistische Statistiken basierend auf Spielminute."""
    factor = minute / 90.0
    base_attacks = int(random.gauss(35, 10) * factor)
    base_dangerous = int(base_attacks * random.uniform(0.15, 0.35))

    if is_dominant:
        base_attacks = int(base_attacks * 1.4)
        base_dangerous = int(base_dangerous * 1.5)

    return MatchStats(
        attacks=max(0, base_attacks),
        dangerous_attacks=max(0, base_dangerous),
        possession=0,  # wird separat gesetzt
        shots_on_target=max(0, int(random.gauss(4, 2) * factor)),
        shots_off_target=max(0, int(random.gauss(5, 3) * factor)),
        corners=max(0, int(random.gauss(5, 2) * factor)),
        goals=0,  # wird vom Score gesetzt
        yellow_cards=random.choices([0, 0, 0, 1, 1, 2], weights=[30, 25, 20, 15, 8, 2])[0],
        red_cards=random.choices([0, 0, 0, 0, 0, 1], weights=[90, 5, 2, 1, 1, 1])[0],
        offsides=max(0, int(random.gauss(2, 1.5) * factor)),
        fouls=max(0, int(random.gauss(10, 3) * factor)),
        saves=max(0, int(random.gauss(3, 2) * factor)),
    )


def get_demo_data() -> List[Match]:
    """Liefert Demo-Daten im BetScope-Stil."""
    raw = [
        ("79'", "Cesena", "Venezia", 0, 3, "IT", "IT", False, True),
        ("37'", "Dynamo Dresden", "Elversberg", 1, 0, "DE", "DE", True, False),
        ("21'", "Standard Liege", "Union Saint Gilloise", 1, 0, "BE", "BE", True, False),
        ("20'", "Sligo Rovers", "Bohemians Dublin", 0, 1, "IE", "IE", False, True),
        ("7'", "Real San Andres", "Real Soacha Cundi...", 0, 0, "CO", "CO", True, False),
        ("20'", "Inter Milan", "Juventus", 1, 0, "IT", "IT", False, False),
        ("7'", "Granada", "Valladolid", 1, 0, "ES", "ES", True, False),
        ("7'", "Liverpool", "Brighton", 0, 0, "EN", "EN", False, True),
        ("8'", "Deportivo Maldon...", "Club Atletico Progr...", 0, 0, "UY", "UY", True, False),
        ("50'", "Genk II", "RFC Liege", 2, 0, "BE", "BE", True, False),
        ("34'", "Young Boys", "Winterthur", 0, 0, "CH", "CH", True, False),
        ("47'", "Ajax", "Fortuna Sittard", 3, 1, "NL", "NL", True, False),
        ("50'", "KV Kortrijk", "KFCO Beerschot Wi...", 0, 0, "BE", "BE", False, False),
    ]

    matches = []
    for i, (minute, home, away, sh, sa, ch, ca, home_dom, away_dom) in enumerate(raw):
        min_val = int(minute.replace("'", "").replace("+", ""))

        stats_h = _rand_stats(min_val, home_dom)
        stats_a = _rand_stats(min_val, away_dom)

        # Ballbesitz aufteilen
        poss_h = random.randint(35, 65)
        if home_dom:
            poss_h = random.randint(55, 75)
        elif away_dom:
            poss_h = random.randint(25, 45)
        stats_h.possession = poss_h
        stats_a.possession = 100 - poss_h

        stats_h.goals = sh
        stats_a.goals = sa

        match = Match(
            minute=minute,
            team_home=home,
            team_away=away,
            score_home=sh,
            score_away=sa,
            country_home=FLAGS.get(ch, "🏳️"),
            country_away=FLAGS.get(ca, "🏳️"),
            stats_home=stats_h,
            stats_away=stats_a,
            league="",
            pinned=(i < 2),  # Erste 2 fixiert
        )
        matches.append(match)

    return matches
