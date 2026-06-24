"""Formatierung eines Spiels in das gewünschte Stat-Layout.

Erzeugt exakt den Textblock aus der Referenz-Grafik – verwendet sowohl
vom Telegram-Bot als auch (als Fallback/Vorschau) im Streamlit-Dashboard.
"""

from __future__ import annotations

from .models import Match
from .scoring import gefahr_score, scope_score


def _pair(home: object, away: object, suffix: str = "") -> str:
    """Formatiert ein Heim/Auswärts-Wertepaar als 'home / away'."""
    return f"{home}{suffix} / {away}{suffix}"


def _xg(value: float) -> str:
    """xG immer mit zwei Nachkommastellen."""
    return f"{value:.2f}"


def format_match(match: Match) -> str:
    """Baut den kompletten Stat-Block für ein Spiel."""
    h, a = match.home, match.away

    scope = _pair(scope_score(h), scope_score(a))
    gefahr = _pair(gefahr_score(h), gefahr_score(a))
    possession = _pair(round(h.possession), round(a.possession), suffix="%")
    shots = _pair(h.shots, a.shots)
    attacks = _pair(h.dangerous_attacks, a.dangerous_attacks)
    corners = _pair(h.corners, a.corners)
    xg = _pair(_xg(h.xg), _xg(a.xg))
    last10_shots = _pair(h.shots_last10, a.shots_last10)

    lines = [
        f"{match.stadium} {h.flag} {h.name} vs {a.flag} {a.name}",
        f"⏱ {match.minute}' | ⚽ {match.score_home} : {match.score_away}",
        "",
        f"📊 Scope Score: {scope}",
        f"🎯 Gefahr-Score: {gefahr}",
        "",
        f"🔵 Ballbesitz: {possession}",
        f"🎯 Torschüsse: {shots}",
        f"⚡ Gef. Angriffe: {attacks}",
        f"🚩 Ecken: {corners}",
        f"📐 xG: {xg}",
        "",
        "🔥 Letzte 10 Min:",
        f"Torschüsse: {last10_shots}",
    ]
    return "\n".join(lines)
