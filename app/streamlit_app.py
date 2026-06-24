"""SportAI – Live-Spiel-Dashboard.

Zeigt pro Spiel exakt die gewünschten Stats (Scope Score, Gefahr-Score,
Ballbesitz, Torschüsse, Gef. Angriffe, Ecken, xG sowie Torschüsse der
letzten 10 Minuten). Datenquelle ist aktuell Mock-Data.
"""

import os
import sys

# Repo-Root in den Pfad legen, damit "app.core" auch via
# `streamlit run app/streamlit_app.py` importierbar ist.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st

from app.core import format_match, gefahr_score, get_matches, scope_score
from app.core.models import Match

st.set_page_config(page_title="SportAI – Tor-Prognose", layout="wide")
st.title("⚽ SportAI: Analyse Live-Spiele")
st.caption("Live-Stats pro Spiel · Datenquelle: Mock-Data (echte API folgt)")


def render_match(match: Match) -> None:
    h, a = match.home, match.away

    st.subheader(f"{h.flag} {h.name} vs {a.flag} {a.name}")
    st.write(f"⏱ {match.minute}'  |  ⚽ {match.score_home} : {match.score_away}")

    # Eigene Kennzahlen prominent
    c1, c2 = st.columns(2)
    c1.metric("📊 Scope Score", f"{scope_score(h)} / {scope_score(a)}")
    c2.metric("🎯 Gefahr-Score", f"{gefahr_score(h)} / {gefahr_score(a)}")

    # Basis-Stats als Tabelle (Heim / Auswärts)
    st.table(
        {
            "Stat": [
                "🔵 Ballbesitz",
                "🎯 Torschüsse",
                "⚡ Gef. Angriffe",
                "🚩 Ecken",
                "📐 xG",
                "🔥 Torschüsse (letzte 10 Min)",
            ],
            h.name: [
                f"{round(h.possession)}%",
                h.shots,
                h.dangerous_attacks,
                h.corners,
                f"{h.xg:.2f}",
                h.shots_last10,
            ],
            a.name: [
                f"{round(a.possession)}%",
                a.shots,
                a.dangerous_attacks,
                a.corners,
                f"{a.xg:.2f}",
                a.shots_last10,
            ],
        }
    )

    # Exaktes Telegram-Layout als Vorschau
    with st.expander("📱 Telegram-Vorschau (exaktes Layout)"):
        st.code(format_match(match), language=None)

    st.markdown("---")


matches = get_matches()
if matches:
    for match in matches:
        render_match(match)
else:
    st.warning("Keine Spieldaten gefunden.")
