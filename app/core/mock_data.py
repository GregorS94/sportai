"""Mock-Datenquelle für die Entwicklung.

Liefert Beispiel-Spiele im gleichen Format, das später eine echte
Stats-API (z. B. API-Football) befüllen würde. Das erste Spiel
entspricht 1:1 der Referenz-Grafik.
"""

from __future__ import annotations

from .models import Match, TeamStats


def get_matches() -> list[Match]:
    """Gibt die aktuell 'laufenden' Mock-Spiele zurück."""
    return [
        Match(
            stadium="🏟",
            minute=19,
            score_home=0,
            score_away=0,
            home=TeamStats(
                name="Colombia",
                flag="🇨🇴",
                possession=70,
                shots=5,
                dangerous_attacks=5,
                corners=2,
                xg=0.49,
                shots_last10=4,
            ),
            away=TeamStats(
                name="Congo DR",
                flag="🇨🇩",
                possession=30,
                shots=0,
                dangerous_attacks=1,
                corners=0,
                xg=0.02,
                shots_last10=0,
            ),
        ),
        Match(
            stadium="🏟",
            minute=63,
            score_home=1,
            score_away=1,
            home=TeamStats(
                name="Germany",
                flag="🇩🇪",
                possession=58,
                shots=9,
                dangerous_attacks=11,
                corners=4,
                xg=1.34,
                shots_last10=2,
            ),
            away=TeamStats(
                name="France",
                flag="🇫🇷",
                possession=42,
                shots=6,
                dangerous_attacks=7,
                corners=3,
                xg=0.88,
                shots_last10=3,
            ),
        ),
    ]
