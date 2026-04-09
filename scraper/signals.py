from __future__ import annotations

from dataclasses import dataclass
from typing import List
from scraper.kicker import Match


@dataclass
class Signal:
    type: str       # "over", "comeback", "corner", "cards"
    strength: int   # 1-3 (1=schwach, 2=mittel, 3=stark)
    label: str      # Kurzbeschreibung z.B. "OVER 2.5"
    reason: str     # Erklärung z.B. "8 Schüsse, 0 Tore"


# ─── Signal Colors ───────────────────────────────────────────────────────
SIGNAL_COLORS = {
    "over": "#e74c3c",       # Rot
    "comeback": "#3498db",   # Blau
    "corner": "#f39c12",     # Orange
    "cards": "#f1c40f",      # Gelb
    "btts": "#2ecc71",       # Grün
}

SIGNAL_ICONS = {
    "over": "🔴",
    "comeback": "🔵",
    "corner": "🟠",
    "cards": "🟡",
    "btts": "🟢",
}


def analyze_match(match: Match) -> List[Signal]:
    """Analysiert ein Spiel und gibt alle aktiven Signale zurück."""
    signals = []  # type: List[Signal]

    minute = _parse_minute(match.minute)
    if minute <= 0:
        return signals

    h = match.stats_home
    a = match.stats_away
    total_goals = match.score_home + match.score_away

    # ─── OVER-Signale ────────────────────────────────────────────────
    signals.extend(_check_over(match, minute, total_goals))

    # ─── COMEBACK-Signale ────────────────────────────────────────────
    signals.extend(_check_comeback(match, minute))

    # ─── CORNER-Signale ──────────────────────────────────────────────
    signals.extend(_check_corners(match, minute))

    # ─── KARTEN-Signale ──────────────────────────────────────────────
    signals.extend(_check_cards(match, minute))

    # ─── BTTS-Signale (Both Teams to Score) ──────────────────────────
    signals.extend(_check_btts(match, minute, total_goals))

    return signals


def _check_over(match: Match, minute: int, total_goals: int) -> List[Signal]:
    """Prüft auf Over-Signale (weitere Tore wahrscheinlich)."""
    signals = []  # type: List[Signal]
    h = match.stats_home
    a = match.stats_away

    total_sot = h.shots_on_target + a.shots_on_target
    total_attacks = h.attacks + a.attacks
    total_dangerous = h.dangerous_attacks + a.dangerous_attacks

    # Signal: Viele Schüsse, wenig Tore
    if total_sot >= 6 and total_goals == 0 and minute >= 20:
        signals.append(Signal(
            type="over",
            strength=3,
            label="OVER 0.5",
            reason=f"{total_sot} Schüsse aufs Tor, noch 0:0",
        ))
    elif total_sot >= 8 and total_goals <= 1 and minute >= 30:
        signals.append(Signal(
            type="over",
            strength=3,
            label="OVER 1.5",
            reason=f"{total_sot} SOT bei nur {total_goals} Tor(en)",
        ))

    # Signal: Einseitiger Druck
    for team, stats, name in [
        ("home", h, match.team_home),
        ("away", a, match.team_away),
    ]:
        if stats.attacks >= 30 and stats.dangerous_attacks >= 10 and minute <= 50:
            strength = 3 if stats.dangerous_attacks >= 15 else 2
            signals.append(Signal(
                type="over",
                strength=strength,
                label="OVER",
                reason=f"{name}: {stats.attacks} ATK, {stats.dangerous_attacks} gef.",
            ))
            break

    # Signal: Hoher Ballbesitz + Schüsse = Druck
    for stats, name in [(h, match.team_home), (a, match.team_away)]:
        if stats.possession >= 65 and stats.shots_on_target >= 4 and minute >= 25:
            signals.append(Signal(
                type="over",
                strength=2,
                label="OVER",
                reason=f"{name}: {stats.possession}% Besitz, {stats.shots_on_target} SOT",
            ))
            break

    return signals


def _check_comeback(match: Match, minute: int) -> List[Signal]:
    """Prüft auf Comeback-Signale."""
    signals = []  # type: List[Signal]
    h = match.stats_home
    a = match.stats_away

    # Wer liegt hinten?
    if match.score_home == match.score_away:
        return signals  # Gleichstand, kein Comeback

    if match.score_home < match.score_away:
        losing_stats, losing_name = h, match.team_home
        winning_stats = a
    else:
        losing_stats, losing_name = a, match.team_away
        winning_stats = h

    # Verlierer dominiert die Stats
    dominance_score = 0
    reasons = []

    if losing_stats.possession > winning_stats.possession + 10:
        dominance_score += 1
        reasons.append(f"{losing_stats.possession}% Besitz")

    if losing_stats.shots_on_target > winning_stats.shots_on_target:
        dominance_score += 1
        reasons.append(f"{losing_stats.shots_on_target} SOT")

    if losing_stats.attacks > winning_stats.attacks + 5:
        dominance_score += 1
        reasons.append(f"{losing_stats.attacks} ATK")

    if losing_stats.corners > winning_stats.corners:
        dominance_score += 1
        reasons.append(f"{losing_stats.corners} Ecken")

    if dominance_score >= 2 and minute >= 15:
        strength = min(3, dominance_score)
        signals.append(Signal(
            type="comeback",
            strength=strength,
            label="COMEBACK",
            reason=f"{losing_name}: {', '.join(reasons[:3])}",
        ))

    return signals


def _check_corners(match: Match, minute: int) -> List[Signal]:
    """Prüft auf Ecken-Signale."""
    signals = []  # type: List[Signal]
    h = match.stats_home
    a = match.stats_away

    total_corners = h.corners + a.corners

    # Ecken-Rate: viele Ecken pro Minute = weiter geht's
    if minute >= 20:
        corner_rate = total_corners / minute * 90  # Hochrechnung auf 90 min

        if corner_rate >= 12:
            signals.append(Signal(
                type="corner",
                strength=3,
                label=f"OVER {total_corners + 2}.5 CK",
                reason=f"{total_corners} Ecken in {minute}' (Rate: {corner_rate:.0f}/Spiel)",
            ))
        elif corner_rate >= 9:
            signals.append(Signal(
                type="corner",
                strength=2,
                label=f"OVER {total_corners + 1}.5 CK",
                reason=f"{total_corners} Ecken in {minute}' (Rate: {corner_rate:.0f}/Spiel)",
            ))

    # Einseitig viele Angriffe + Schüsse daneben = Ecken kommen
    for stats, name in [(h, match.team_home), (a, match.team_away)]:
        if stats.attacks >= 25 and stats.shots_off_target >= 4:
            signals.append(Signal(
                type="corner",
                strength=2,
                label="CORNERS",
                reason=f"{name}: {stats.attacks} ATK, {stats.shots_off_target} daneben",
            ))
            break

    return signals


def _check_cards(match: Match, minute: int) -> List[Signal]:
    """Prüft auf Karten-Signale."""
    signals = []  # type: List[Signal]
    h = match.stats_home
    a = match.stats_away

    for stats, name in [(h, match.team_home), (a, match.team_away)]:
        # Viele Fouls = Karte wahrscheinlich
        if stats.fouls >= 8 and stats.yellow_cards == 0:
            signals.append(Signal(
                type="cards",
                strength=3,
                label="KARTE",
                reason=f"{name}: {stats.fouls} Fouls, noch keine Gelbe!",
            ))
        elif stats.fouls >= 6 and stats.yellow_cards == 0:
            signals.append(Signal(
                type="cards",
                strength=2,
                label="KARTE",
                reason=f"{name}: {stats.fouls} Fouls, 0 Gelbe",
            ))

    # Rückstand + viele Fouls = Frustration
    if match.score_home < match.score_away and h.fouls >= 5:
        signals.append(Signal(
            type="cards",
            strength=2,
            label="KARTE",
            reason=f"{match.team_home} hinten + {h.fouls} Fouls",
        ))
    elif match.score_away < match.score_home and a.fouls >= 5:
        signals.append(Signal(
            type="cards",
            strength=2,
            label="KARTE",
            reason=f"{match.team_away} hinten + {a.fouls} Fouls",
        ))

    return signals


def _check_btts(match: Match, minute: int, total_goals: int) -> List[Signal]:
    """Prüft auf Both Teams to Score Signale."""
    signals = []  # type: List[Signal]
    h = match.stats_home
    a = match.stats_away

    # Beide Teams haben schon getroffen -> kein Signal nötig
    if match.score_home > 0 and match.score_away > 0:
        return signals

    # Beide Teams haben Schüsse aufs Tor
    if h.shots_on_target >= 3 and a.shots_on_target >= 3 and minute >= 25:
        # Aber mindestens ein Team hat noch nicht getroffen
        if match.score_home == 0 or match.score_away == 0:
            signals.append(Signal(
                type="btts",
                strength=2,
                label="BTTS",
                reason=f"Beide aktiv: {h.shots_on_target} vs {a.shots_on_target} SOT",
            ))

    # Beide Teams haben hohen Ballbesitz-Anteil (ausgeglichen)
    if abs(h.possession - a.possession) <= 10 and h.shots_on_target >= 2 and a.shots_on_target >= 2:
        if match.score_home == 0 or match.score_away == 0:
            signals.append(Signal(
                type="btts",
                strength=1,
                label="BTTS",
                reason=f"Ausgeglichen: {h.possession}%-{a.possession}% Besitz",
            ))

    return signals


def _parse_minute(minute_str: str) -> int:
    """Parsed '45+2' oder '67'' zu int."""
    try:
        cleaned = minute_str.replace("'", "").replace("+", "").strip()
        # Handle "45+2" -> take first number
        if "+" in minute_str:
            parts = minute_str.replace("'", "").split("+")
            return int(parts[0].strip())
        return int(cleaned)
    except (ValueError, TypeError):
        return 0
