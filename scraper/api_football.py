from __future__ import annotations

import requests
from typing import Optional, List, Dict, Any
from scraper.kicker import Match, MatchStats, FLAGS


class APIFootball:
    """Client für API-Football (v3) – Free Tier: 100 requests/Tag."""

    BASE_URL = "https://v3.football.api-sports.io"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {
            "x-apisports-key": api_key,
        }

    def _get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Führt einen API-Request aus."""
        resp = requests.get(
            f"{self.BASE_URL}/{endpoint}",
            headers=self.headers,
            params=params or {},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()

        if data.get("errors"):
            errors = data["errors"]
            if isinstance(errors, dict):
                msg = ", ".join(str(v) for v in errors.values())
            else:
                msg = str(errors)
            raise ConnectionError(f"API-Football Fehler: {msg}")

        return data

    def get_live_matches(self) -> List[Match]:
        """Holt alle aktuell laufenden Spiele mit Statistiken."""
        data = self._get("fixtures", params={"live": "all"})
        fixtures = data.get("response", [])

        matches = []  # type: List[Match]
        for fix in fixtures:
            match = self._parse_fixture(fix)
            if match:
                matches.append(match)

        # Statistiken für jedes Spiel laden
        for match_obj in matches:
            self._enrich_with_stats(match_obj, fixtures)

        return matches

    def get_todays_matches(self) -> List[Match]:
        """Holt alle heutigen Spiele (auch geplante)."""
        import datetime
        today = datetime.date.today().isoformat()
        data = self._get("fixtures", params={"date": today})
        fixtures = data.get("response", [])

        matches = []  # type: List[Match]
        for fix in fixtures:
            match = self._parse_fixture(fix)
            if match:
                matches.append(match)

        return matches

    def get_fixture_stats(self, fixture_id: int) -> Dict[str, MatchStats]:
        """Holt detaillierte Statistiken für ein Spiel."""
        data = self._get("fixtures/statistics", params={"fixture": fixture_id})
        response = data.get("response", [])

        result = {}  # type: Dict[str, MatchStats]
        for team_data in response:
            team_name = team_data.get("team", {}).get("name", "")
            stats = self._parse_stats(team_data.get("statistics", []))
            result[team_name] = stats

        return result

    def check_api_status(self) -> Dict[str, Any]:
        """Prüft API-Status und verbleibende Requests."""
        data = self._get("status")
        response = data.get("response", {})
        account = response.get("account", {})
        subscription = response.get("subscription", {})
        requests_info = response.get("requests", {})

        return {
            "name": account.get("firstname", ""),
            "plan": subscription.get("plan", "Free"),
            "requests_today": requests_info.get("current", 0),
            "requests_limit": requests_info.get("limit_day", 100),
        }

    def _parse_fixture(self, fix: Dict[str, Any]) -> Optional[Match]:
        """Parsed ein einzelnes Fixture in ein Match-Objekt."""
        try:
            fixture = fix.get("fixture", {})
            status = fixture.get("status", {})
            teams = fix.get("teams", {})
            goals = fix.get("goals", {})
            league = fix.get("league", {})

            # Spielminute bestimmen
            elapsed = status.get("elapsed")
            short_status = status.get("short", "")

            if short_status in ("1H", "2H", "ET"):
                minute = f"{elapsed}'" if elapsed else "0'"
            elif short_status == "HT":
                minute = "HZ"
            elif short_status == "FT":
                minute = "Ende"
            elif short_status == "NS":
                minute = status.get("long", "Geplant")
            else:
                minute = f"{elapsed}'" if elapsed else short_status

            # Country code -> Flag
            country_code = league.get("country", "")
            flag = _country_to_flag(country_code)

            home = teams.get("home", {})
            away = teams.get("away", {})

            return Match(
                minute=minute,
                team_home=home.get("name", "?"),
                team_away=away.get("name", "?"),
                score_home=goals.get("home") or 0,
                score_away=goals.get("away") or 0,
                country_home=flag,
                country_away=flag,
                league=league.get("name", ""),
                pinned=False,
                stats_home=MatchStats(),
                stats_away=MatchStats(),
            )
        except Exception:
            return None

    def _enrich_with_stats(self, match: Match, fixtures: List[Dict[str, Any]]):
        """Reichert ein Match mit Statistiken an."""
        # Finde fixture_id
        for fix in fixtures:
            teams = fix.get("teams", {})
            if teams.get("home", {}).get("name") == match.team_home:
                fixture_id = fix.get("fixture", {}).get("id")
                if fixture_id:
                    try:
                        stats_map = self.get_fixture_stats(fixture_id)
                        if match.team_home in stats_map:
                            match.stats_home = stats_map[match.team_home]
                        if match.team_away in stats_map:
                            match.stats_away = stats_map[match.team_away]
                    except Exception:
                        pass
                break

    def _parse_stats(self, statistics: List[Dict[str, Any]]) -> MatchStats:
        """Parsed API-Football Statistiken in unser MatchStats-Format."""
        stats = MatchStats()
        stat_map = {}  # type: Dict[str, Any]

        for s in statistics:
            stat_type = s.get("type", "")
            value = s.get("value")
            stat_map[stat_type] = value

        stats.possession = _parse_pct(stat_map.get("Ball Possession"))
        stats.shots_on_target = _parse_int(stat_map.get("Shots on Goal"))
        stats.shots_off_target = _parse_int(stat_map.get("Shots off Goal"))
        stats.corners = _parse_int(stat_map.get("Corner Kicks"))
        stats.offsides = _parse_int(stat_map.get("Offsides"))
        stats.fouls = _parse_int(stat_map.get("Fouls"))
        stats.yellow_cards = _parse_int(stat_map.get("Yellow Cards"))
        stats.red_cards = _parse_int(stat_map.get("Red Cards"))
        stats.saves = _parse_int(stat_map.get("Goalkeeper Saves"))

        # API-Football hat keine "Angriffe" direkt, berechne aus Total Shots + Blocked
        total_shots = _parse_int(stat_map.get("Total Shots"))
        blocked = _parse_int(stat_map.get("Blocked Shots"))
        total_passes = _parse_int(stat_map.get("Total passes"))

        # Angriffe schätzen: basierend auf Pässe und Schüsse
        stats.attacks = max(total_shots * 3, int(total_passes * 0.15)) if total_passes else total_shots * 4
        stats.dangerous_attacks = total_shots + blocked

        return stats


def _parse_int(value) -> int:
    """Parsed einen Wert zu int, gibt 0 bei None/Fehler zurück."""
    if value is None:
        return 0
    try:
        return int(str(value).replace("%", "").strip())
    except (ValueError, TypeError):
        return 0


def _parse_pct(value) -> int:
    """Parsed einen Prozent-String wie '64%' zu int."""
    if value is None:
        return 50
    try:
        return int(str(value).replace("%", "").strip())
    except (ValueError, TypeError):
        return 50


# Country name -> flag emoji mapping
_COUNTRY_FLAGS = {
    "Germany": "🇩🇪", "Italy": "🇮🇹", "Spain": "🇪🇸", "England": "🇬🇧",
    "France": "🇫🇷", "Netherlands": "🇳🇱", "Belgium": "🇧🇪", "Portugal": "🇵🇹",
    "Austria": "🇦🇹", "Switzerland": "🇨🇭", "Turkey": "🇹🇷", "Greece": "🇬🇷",
    "Ireland": "🇮🇪", "Colombia": "🇨🇴", "Uruguay": "🇺🇾", "Argentina": "🇦🇷",
    "Brazil": "🇧🇷", "Sweden": "🇸🇪", "Norway": "🇳🇴", "Denmark": "🇩🇰",
    "Poland": "🇵🇱", "Czech-Republic": "🇨🇿", "Croatia": "🇭🇷", "Serbia": "🇷🇸",
    "Romania": "🇷🇴", "Saudi-Arabia": "🇸🇦", "Japan": "🇯🇵", "South-Korea": "🇰🇷",
    "USA": "🇺🇸", "Mexico": "🇲🇽", "Scotland": "🏴󠁧󠁢󠁳󠁣󠁴󠁿", "Wales": "🏴󠁧󠁢󠁷󠁬󠁳󠁿",
    "Russia": "🇷🇺", "Ukraine": "🇺🇦", "China": "🇨🇳", "Australia": "🇦🇺",
    "World": "🌍",
}


def _country_to_flag(country: str) -> str:
    """Konvertiert Country-Name zu Flag-Emoji."""
    return _COUNTRY_FLAGS.get(country, "🏳️")
