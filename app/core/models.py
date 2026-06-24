"""Datenmodell für Live-Spiel-Statistiken.

Alle Felder entsprechen genau den Stats aus dem gewünschten Layout:
Ballbesitz, Torschüsse, Gef. Angriffe, Ecken, xG sowie die Torschüsse
der letzten 10 Minuten.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TeamStats:
    """Statistiken eines einzelnen Teams in einem laufenden Spiel."""

    name: str
    flag: str = "🏳"          # Flaggen-Emoji (z. B. 🇨🇴)
    possession: float = 0.0    # Ballbesitz in Prozent
    shots: int = 0             # Torschüsse (gesamt)
    dangerous_attacks: int = 0  # Gef. Angriffe
    corners: int = 0           # Ecken
    xg: float = 0.0            # Expected Goals (xG)
    shots_last10: int = 0      # Torschüsse in den letzten 10 Minuten


@dataclass
class Match:
    """Ein laufendes Spiel mit Stats für Heim- und Auswärtsteam."""

    home: TeamStats
    away: TeamStats
    minute: int = 0            # aktuelle Spielminute
    score_home: int = 0
    score_away: int = 0
    stadium: str = "🏟"        # optionales Stadion-/Wetter-Emoji
