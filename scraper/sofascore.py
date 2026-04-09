from __future__ import annotations

import time
import requests
from typing import Optional, List, Dict, Any
from scraper.kicker import Match, MatchStats


class SofascoreClient:
    """Client für Sofascore Live-Daten. Kein API-Key nötig."""

    BASE_URL = "https://api.sofascore.com/api/v1"
    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json",
        "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
        "Referer": "https://www.sofascore.com/",
        "Origin": "https://www.sofascore.com",
        "Cache-Control": "no-cache",
    }

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)
        self._last_request = 0.0

    def _get(self, path: str) -> Dict[str, Any]:
        """GET-Request mit Rate-Limiting."""
        # Mindestens 1s zwischen Requests
        now = time.time()
        elapsed = now - self._last_request
        if elapsed < 1.0:
            time.sleep(1.0 - elapsed)

        url = f"{self.BASE_URL}/{path}"
        resp = self.session.get(url, timeout=15)
        self._last_request = time.time()

        if resp.status_code == 403:
            raise ConnectionError(
                "Sofascore hat den Zugriff blockiert (403). "
                "Bitte warte einige Minuten und versuche es erneut."
            )
        resp.raise_for_status()
        return resp.json()

    def get_live_matches(self) -> List[Match]:
        """Holt alle aktuell laufenden Fußball-Spiele."""
        data = self._get("sport/football/events/live")
        events = data.get("events", [])

        matches = []  # type: List[Match]
        for ev in events:
            match = self._parse_event(ev)
            if match:
                matches.append(match)

        return matches

    def load_stats(self, matches: List[Match], max_count: int = 20) -> int:
        """Lädt Statistiken für Spiele nach. Gibt Anzahl geladener Stats zurück."""
        loaded = 0
        for m in matches:
            if loaded >= max_count:
                break
            event_id = getattr(m, "_event_id", None)
            if not event_id:
                continue
            try:
                self._load_event_stats(m, event_id)
                loaded += 1
            except Exception:
                continue
        return loaded

    def _parse_event(self, ev: Dict[str, Any]) -> Optional[Match]:
        """Parsed ein Sofascore-Event in ein Match-Objekt."""
        try:
            home_team = ev.get("homeTeam", {})
            away_team = ev.get("awayTeam", {})
            home_score = ev.get("homeScore", {})
            away_score = ev.get("awayScore", {})
            status = ev.get("status", {})
            tournament = ev.get("tournament", {})
            category = tournament.get("category", {})

            # Spielminute berechnen
            minute = self._calc_minute(ev, status)

            # Nur laufende Spiele
            status_type = status.get("type", "")
            if status_type not in ("inprogress", ""):
                # Halbzeit auch einbeziehen
                desc = status.get("description", "").lower()
                if "halftime" not in desc and status_type != "inprogress":
                    pass  # Trotzdem einbeziehen

            # Länderflagge
            country = category.get("name", "")
            flag = country_to_flag(country)

            match = Match(
                minute=minute,
                team_home=home_team.get("name", "?"),
                team_away=away_team.get("name", "?"),
                score_home=home_score.get("current", 0) or 0,
                score_away=away_score.get("current", 0) or 0,
                country_home=flag,
                country_away=flag,
                league=tournament.get("name", ""),
                pinned=False,
                stats_home=MatchStats(),
                stats_away=MatchStats(),
            )
            match._event_id = ev.get("id")  # type: ignore[attr-defined]
            return match
        except Exception:
            return None

    def _calc_minute(self, ev: Dict[str, Any], status: Dict[str, Any]) -> str:
        """Berechnet die aktuelle Spielminute."""
        desc = status.get("description", "").lower()

        if "halftime" in desc:
            return "HZ"
        if "ended" in desc or status.get("type") == "finished":
            return "Ende"

        # Minute aus statusTime oder Berechnung
        status_time = ev.get("statusTime", {})
        if status_time:
            minute = status_time.get("played", 0)
            if minute and minute > 0:
                return "%d'" % minute

        # Berechnung über Timestamps
        start_ts = ev.get("startTimestamp", 0)
        if start_ts > 0:
            now = int(time.time())
            elapsed_sec = now - start_ts
            elapsed_min = max(0, int(elapsed_sec / 60))
            if elapsed_min > 90:
                return "90+%d'" % (elapsed_min - 90)
            if elapsed_min > 45 and desc and "2nd" not in desc:
                return "HZ"
            return "%d'" % min(elapsed_min, 90)

        return "Live"

    def _load_event_stats(self, match: Match, event_id: int):
        """Lädt und parsed Statistiken für ein Event."""
        data = self._get("event/%d/statistics" % event_id)
        statistics = data.get("statistics", [])

        # Suche nach "ALL" (Gesamtstatistik)
        for period in statistics:
            if period.get("period") == "ALL":
                groups = period.get("groups", [])
                self._apply_stats(match, groups)
                return

        # Fallback: nimm die erste verfügbare Periode
        if statistics:
            groups = statistics[0].get("groups", [])
            self._apply_stats(match, groups)

    def _apply_stats(self, match: Match, groups: List[Dict[str, Any]]):
        """Wendet Stats-Gruppen auf das Match an."""
        stat_map = {}  # type: Dict[str, tuple]

        for group in groups:
            items = group.get("statisticsItems", [])
            for item in items:
                name = item.get("name", "").lower()
                home_val = item.get("home", item.get("homeValue", "0"))
                away_val = item.get("away", item.get("awayValue", "0"))
                stat_map[name] = (home_val, away_val)

        h = match.stats_home
        a = match.stats_away

        # Ballbesitz
        poss = stat_map.get("ball possession", stat_map.get("possession", None))
        if poss:
            h.possession = _pct(poss[0])
            a.possession = _pct(poss[1])

        # Angriffe
        atk = stat_map.get("attacks", None)
        if atk:
            h.attacks = _int(atk[0])
            a.attacks = _int(atk[1])

        # Gefährliche Angriffe
        datk = stat_map.get("dangerous attacks", None)
        if datk:
            h.dangerous_attacks = _int(datk[0])
            a.dangerous_attacks = _int(datk[1])

        # Schüsse aufs Tor
        sot = stat_map.get("shots on goal", stat_map.get("shots on target", None))
        if sot:
            h.shots_on_target = _int(sot[0])
            a.shots_on_target = _int(sot[1])

        # Schüsse daneben
        soff = stat_map.get("shots off goal", stat_map.get("shots off target", None))
        if soff:
            h.shots_off_target = _int(soff[0])
            a.shots_off_target = _int(soff[1])

        # Ecken
        cor = stat_map.get("corner kicks", stat_map.get("corners", None))
        if cor:
            h.corners = _int(cor[0])
            a.corners = _int(cor[1])

        # Fouls
        fouls = stat_map.get("fouls", None)
        if fouls:
            h.fouls = _int(fouls[0])
            a.fouls = _int(fouls[1])

        # Gelbe Karten
        yc = stat_map.get("yellow cards", None)
        if yc:
            h.yellow_cards = _int(yc[0])
            a.yellow_cards = _int(yc[1])

        # Rote Karten
        rc = stat_map.get("red cards", None)
        if rc:
            h.red_cards = _int(rc[0])
            a.red_cards = _int(rc[1])

        # Abseits
        off = stat_map.get("offsides", None)
        if off:
            h.offsides = _int(off[0])
            a.offsides = _int(off[1])

        # Paraden
        saves = stat_map.get("goalkeeper saves", stat_map.get("saves", None))
        if saves:
            h.saves = _int(saves[0])
            a.saves = _int(saves[1])

        # Tore aus Score
        h.goals = match.score_home
        a.goals = match.score_away


def _int(val) -> int:
    """Parsed Wert zu int."""
    if val is None:
        return 0
    try:
        return int(str(val).replace("%", "").strip())
    except (ValueError, TypeError):
        return 0


def _pct(val) -> int:
    """Parsed Prozent-String."""
    return _int(val)


# ─── Länderflaggen ───────────────────────────────────────────────────────
_FLAGS = {
    "Germany": "🇩🇪", "Italy": "🇮🇹", "Spain": "🇪🇸", "England": "🇬🇧",
    "France": "🇫🇷", "Netherlands": "🇳🇱", "Belgium": "🇧🇪", "Portugal": "🇵🇹",
    "Austria": "🇦🇹", "Switzerland": "🇨🇭", "Turkey": "🇹🇷", "Greece": "🇬🇷",
    "Ireland": "🇮🇪", "Colombia": "🇨🇴", "Uruguay": "🇺🇾", "Argentina": "🇦🇷",
    "Brazil": "🇧🇷", "Sweden": "🇸🇪", "Norway": "🇳🇴", "Denmark": "🇩🇰",
    "Poland": "🇵🇱", "Czech Republic": "🇨🇿", "Croatia": "🇭🇷", "Serbia": "🇷🇸",
    "Romania": "🇷🇴", "Saudi Arabia": "🇸🇦", "Japan": "🇯🇵", "South Korea": "🇰🇷",
    "USA": "🇺🇸", "Mexico": "🇲🇽", "Scotland": "🏴󠁧󠁢󠁳󠁣󠁴󠁿", "Wales": "🏴󠁧󠁢󠁷󠁬󠁳󠁿",
    "Russia": "🇷🇺", "Ukraine": "🇺🇦", "China": "🇨🇳", "Australia": "🇦🇺",
    "Egypt": "🇪🇬", "Morocco": "🇲🇦", "Tunisia": "🇹🇳", "Algeria": "🇩🇿",
    "South Africa": "🇿🇦", "Nigeria": "🇳🇬", "Ghana": "🇬🇭", "Kenya": "🇰🇪",
    "India": "🇮🇳", "Indonesia": "🇮🇩", "Thailand": "🇹🇭", "Vietnam": "🇻🇳",
    "Iran": "🇮🇷", "Iraq": "🇮🇶", "Qatar": "🇶🇦", "UAE": "🇦🇪",
    "Hungary": "🇭🇺", "Bulgaria": "🇧🇬", "Slovakia": "🇸🇰", "Slovenia": "🇸🇮",
    "Bosnia & Herzegovina": "🇧🇦", "Montenegro": "🇲🇪", "Albania": "🇦🇱",
    "Finland": "🇫🇮", "Iceland": "🇮🇸", "Estonia": "🇪🇪", "Latvia": "🇱🇻",
    "Lithuania": "🇱🇹", "Belarus": "🇧🇾", "Georgia": "🇬🇪",
    "Peru": "🇵🇪", "Chile": "🇨🇱", "Ecuador": "🇪🇨", "Venezuela": "🇻🇪",
    "Bolivia": "🇧🇴", "Paraguay": "🇵🇾", "Costa Rica": "🇨🇷", "Panama": "🇵🇦",
    "Honduras": "🇭🇳", "El Salvador": "🇸🇻", "Guatemala": "🇬🇹",
    "Jamaica": "🇯🇲", "Canada": "🇨🇦", "New Zealand": "🇳🇿",
    "Cyprus": "🇨🇾", "Malta": "🇲🇹", "Luxembourg": "🇱🇺",
    "North Macedonia": "🇲🇰", "Kosovo": "🇽🇰",
    "World": "🌍", "Europe": "🇪🇺", "Africa": "🌍", "Asia": "🌏",
    "South America": "🌎", "North America": "🌎",
}


def country_to_flag(country: str) -> str:
    """Konvertiert Country-Name zu Flag-Emoji."""
    if not country:
        return "🏳️"
    # Exakter Match
    if country in _FLAGS:
        return _FLAGS[country]
    # Case-insensitiv
    lower = country.lower()
    for k, v in _FLAGS.items():
        if k.lower() == lower:
            return v
    return "🏳️"
