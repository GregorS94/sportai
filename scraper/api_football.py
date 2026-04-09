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
        self.requests_used = 0

    def _get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Führt einen API-Request aus."""
        resp = requests.get(
            f"{self.BASE_URL}/{endpoint}",
            headers=self.headers,
            params=params or {},
            timeout=15,
        )
        resp.raise_for_status()
        self.requests_used += 1
        data = resp.json()

        if data.get("errors"):
            errors = data["errors"]
            if isinstance(errors, dict) and errors:
                msg = ", ".join(str(v) for v in errors.values())
                raise ConnectionError(f"API-Football Fehler: {msg}")

        return data

    def get_live_matches(self) -> List[Match]:
        """Holt alle aktuell laufenden Spiele. Nur 1 API-Request!

        Stats werden NICHT einzeln geladen (spart API-Quota).
        Nutze load_stats_for_matches() separat um Stats zu laden.
        """
        data = self._get("fixtures", params={"live": "all"})
        fixtures = data.get("response", [])

        if not fixtures:
            return []

        matches = []  # type: List[Match]

        for fix in fixtures:
            match = self._parse_fixture(fix)
            if match:
                fid = fix.get("fixture", {}).get("id")
                match._fixture_id = fid  # type: ignore[attr-defined]

                # Inline-Statistiken direkt aus dem Fixture parsen (falls vorhanden)
                stats_list = fix.get("statistics")
                if stats_list and isinstance(stats_list, list) and len(stats_list) >= 2:
                    match.stats_home = self._parse_stats(
                        stats_list[0].get("statistics", [])
                    )
                    match.stats_away = self._parse_stats(
                        stats_list[1].get("statistics", [])
                    )
                    self._fix_possession(match)

                matches.append(match)

        return matches

    def load_stats_for_matches(self, matches: List[Match], max_requests: int = 5) -> int:
        """Lädt Stats einzeln nach. Gibt Anzahl geladener Stats zurück.

        Nur für Spiele die noch keine Stats haben und mindestens 10 Min laufen.
        """
        loaded = 0
        for m in matches:
            if loaded >= max_requests:
                break
            # Nur Stats laden wenn noch keine da sind (alle 0)
            if m.stats_home.shots_on_target > 0 or m.stats_away.shots_on_target > 0:
                continue  # Hat schon Stats
            # Nur für Spiele die schon etwas laufen
            minute = _parse_minute(m.minute)
            if minute < 10:
                continue
            fid = getattr(m, "_fixture_id", None)
            if not fid:
                continue
            try:
                self._load_stats_for_match(m, fid)
                loaded += 1
            except Exception:
                pass
        return loaded

    def get_todays_matches(self) -> List[Match]:
        """Holt alle heutigen Spiele (auch geplante). 1 API-Request."""
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
        """Holt detaillierte Statistiken für ein Spiel. 1 API-Request."""
        data = self._get("fixtures/statistics", params={"fixture": fixture_id})
        response = data.get("response", [])

        result = {}  # type: Dict[str, MatchStats]
        for team_data in response:
            team_name = team_data.get("team", {}).get("name", "")
            stats = self._parse_stats(team_data.get("statistics", []))
            result[team_name] = stats

        return result

    def check_api_status(self) -> Dict[str, Any]:
        """Prüft API-Status und verbleibende Requests. 1 API-Request."""
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
                minute = "%d'" % (elapsed or 0)
            elif short_status == "HT":
                minute = "HZ"
            elif short_status == "FT":
                minute = "Ende"
            elif short_status == "NS":
                minute = status.get("long", "Geplant")
            else:
                minute = "%d'" % elapsed if elapsed else short_status

            # Country -> Flag
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

    def _load_stats_for_match(self, match: Match, fixture_id: int):
        """Lädt Statistiken für ein einzelnes Spiel. 1 API-Request."""
        stats_map = self.get_fixture_stats(fixture_id)
        if match.team_home in stats_map:
            match.stats_home = stats_map[match.team_home]
        if match.team_away in stats_map:
            match.stats_away = stats_map[match.team_away]
        self._fix_possession(match)

    def _fix_possession(self, match: Match):
        """Stellt sicher, dass Ballbesitz-Werte zusammen 100% ergeben."""
        h = match.stats_home.possession
        a = match.stats_away.possession
        if h == 0 and a == 0:
            match.stats_home.possession = 50
            match.stats_away.possession = 50
        elif h > 0 and a == 0:
            match.stats_away.possession = 100 - h
        elif a > 0 and h == 0:
            match.stats_home.possession = 100 - a

    def _parse_stats(self, statistics: List[Dict[str, Any]]) -> MatchStats:
        """Parsed API-Football Statistiken in unser MatchStats-Format."""
        stat_map = {}  # type: Dict[str, Any]
        for s in statistics:
            stat_type = s.get("type", "")
            value = s.get("value")
            stat_map[stat_type] = value

        possession = _parse_pct(stat_map.get("Ball Possession"))
        shots_on = _parse_int(stat_map.get("Shots on Goal"))
        shots_off = _parse_int(stat_map.get("Shots off Goal"))
        corners = _parse_int(stat_map.get("Corner Kicks"))
        offsides = _parse_int(stat_map.get("Offsides"))
        fouls = _parse_int(stat_map.get("Fouls"))
        yellows = _parse_int(stat_map.get("Yellow Cards"))
        reds = _parse_int(stat_map.get("Red Cards"))
        saves = _parse_int(stat_map.get("Goalkeeper Saves"))
        total_shots = _parse_int(stat_map.get("Total Shots"))
        blocked = _parse_int(stat_map.get("Blocked Shots"))
        total_passes = _parse_int(stat_map.get("Total passes"))
        pass_accuracy = _parse_int(stat_map.get("Passes %"))

        # Angriffe schätzen (API-Football liefert das nicht direkt)
        if total_passes > 0:
            attacks = max(total_shots * 3, int(total_passes * 0.15))
        else:
            attacks = total_shots * 4
        dangerous = total_shots + blocked

        return MatchStats(
            attacks=attacks,
            dangerous_attacks=dangerous,
            possession=possession,
            shots_on_target=shots_on,
            shots_off_target=shots_off,
            corners=corners,
            goals=0,
            yellow_cards=yellows,
            red_cards=reds,
            offsides=offsides,
            fouls=fouls,
            saves=saves,
        )


def _parse_minute(minute_str: str) -> int:
    """Parsed '45+2' oder '67'' zu int."""
    try:
        cleaned = minute_str.replace("'", "").strip()
        if "+" in cleaned:
            return int(cleaned.split("+")[0])
        return int(cleaned)
    except (ValueError, TypeError):
        return 0


def _parse_int(value) -> int:
    """Parsed einen Wert zu int, gibt 0 bei None/Fehler zurück."""
    if value is None:
        return 0
    try:
        return int(str(value).replace("%", "").strip())
    except (ValueError, TypeError):
        return 0


def _parse_pct(value) -> int:
    """Parsed einen Prozent-String wie '64%' zu int. Gibt 0 bei None."""
    if value is None:
        return 0
    try:
        return int(str(value).replace("%", "").strip())
    except (ValueError, TypeError):
        return 0


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
    "Egypt": "🇪🇬", "Morocco": "🇲🇦", "Tunisia": "🇹🇳", "Algeria": "🇩🇿",
    "South-Africa": "🇿🇦", "Nigeria": "🇳🇬", "Ghana": "🇬🇭", "Kenya": "🇰🇪",
    "India": "🇮🇳", "Indonesia": "🇮🇩", "Thailand": "🇹🇭", "Vietnam": "🇻🇳",
    "Malaysia": "🇲🇾", "Iran": "🇮🇷", "Iraq": "🇮🇶", "Qatar": "🇶🇦",
    "UAE": "🇦🇪", "Bahrain": "🇧🇭", "Kuwait": "🇰🇼", "Oman": "🇴🇲",
    "Jordan": "🇯🇴", "Lebanon": "🇱🇧", "Israel": "🇮🇱", "Palestine": "🇵🇸",
    "Hungary": "🇭🇺", "Bulgaria": "🇧🇬", "Slovakia": "🇸🇰", "Slovenia": "🇸🇮",
    "Bosnia": "🇧🇦", "Bosnia-and-Herzegovina": "🇧🇦", "Montenegro": "🇲🇪",
    "North-Macedonia": "🇲🇰", "Albania": "🇦🇱", "Kosovo": "🇽🇰",
    "Finland": "🇫🇮", "Iceland": "🇮🇸", "Estonia": "🇪🇪", "Latvia": "🇱🇻",
    "Lithuania": "🇱🇹", "Belarus": "🇧🇾", "Georgia": "🇬🇪", "Armenia": "🇦🇲",
    "Azerbaijan": "🇦🇿", "Kazakhstan": "🇰🇿", "Uzbekistan": "🇺🇿",
    "Peru": "🇵🇪", "Chile": "🇨🇱", "Ecuador": "🇪🇨", "Venezuela": "🇻🇪",
    "Bolivia": "🇧🇴", "Paraguay": "🇵🇾", "Costa-Rica": "🇨🇷", "Panama": "🇵🇦",
    "Honduras": "🇭🇳", "El-Salvador": "🇸🇻", "Guatemala": "🇬🇹",
    "Jamaica": "🇯🇲", "Trinidad-and-Tobago": "🇹🇹", "Canada": "🇨🇦",
    "New-Zealand": "🇳🇿", "Cyprus": "🇨🇾", "Malta": "🇲🇹", "Luxembourg": "🇱🇺",
    "World": "🌍",
}


def _country_to_flag(country: str) -> str:
    """Konvertiert Country-Name zu Flag-Emoji."""
    return _COUNTRY_FLAGS.get(country, "🏳️")
