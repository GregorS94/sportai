"""Berechnung der eigenen Kennzahlen *Scope Score* und *Gefahr-Score*.

Beide Werte werden ausschließlich aus den Basis-Stats eines Teams
berechnet. Die Gewichte sind bewusst als Konstanten ausgelagert, damit
du sie jederzeit ohne Code-Verständnis anpassen kannst.

Die Default-Gewichte sind so gewählt, dass sie die Werte aus der
Referenz-Grafik exakt reproduzieren:

    Colombia: Scope 104 / Gefahr 29
    Congo DR: Scope   0 / Gefahr  0
"""

from __future__ import annotations

from .models import TeamStats

# --- Gefahr-Score -----------------------------------------------------------
# Reine "Torgefahr": wie nah ist das Team aktuell an einem Tor?
GEFAHR_W_XG = 20.0       # je xG
GEFAHR_W_SHOTS = 3.0     # je Torschuss
GEFAHR_W_CORNERS = 2.0   # je Ecke

# --- Scope Score ------------------------------------------------------------
# Breiteres "Dominanz"-Maß: Torgefahr + Spielkontrolle + Momentum.
SCOPE_W_XG = 20.0          # je xG
SCOPE_W_SHOTS = 6.0        # je Torschuss
SCOPE_W_CORNERS = 4.0      # je Ecke
SCOPE_W_LAST10 = 4.0       # je Torschuss der letzten 10 Min (Momentum)
SCOPE_W_DOMINANCE = 2.0    # je Ballbesitz-%-Punkt über 50 %


def gefahr_score(team: TeamStats) -> int:
    """Akute Torgefahr eines Teams (ganzzahlig gerundet)."""
    value = (
        GEFAHR_W_XG * team.xg
        + GEFAHR_W_SHOTS * team.shots
        + GEFAHR_W_CORNERS * team.corners
    )
    return round(value)


def scope_score(team: TeamStats) -> int:
    """Gesamt-Dominanz eines Teams (ganzzahlig gerundet).

    Enthält neben der Torgefahr auch das Momentum (Schüsse der letzten
    10 Min) und einen Bonus für Ballbesitz über 50 %.
    """
    dominance = max(0.0, team.possession - 50.0)
    value = (
        SCOPE_W_XG * team.xg
        + SCOPE_W_SHOTS * team.shots
        + SCOPE_W_CORNERS * team.corners
        + SCOPE_W_LAST10 * team.shots_last10
        + SCOPE_W_DOMINANCE * dominance
    )
    return round(value)
