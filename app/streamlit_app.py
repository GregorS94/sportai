from __future__ import annotations

import streamlit as st
from scraper.kicker import KickerScraper, Match, get_demo_data
from typing import List, Dict


# ─── Seiten-Konfiguration ───────────────────────────────────────────────
st.set_page_config(
    page_title="SportAI – Live-Fußball",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─── Custom CSS ──────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    .main-header {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
        padding: 2rem 2.5rem;
        border-radius: 16px;
        margin-bottom: 2rem;
        color: white;
    }
    .main-header h1 {
        margin: 0;
        font-size: 2.2rem;
        font-weight: 700;
    }
    .main-header p {
        margin: 0.5rem 0 0 0;
        opacity: 0.8;
        font-size: 1rem;
    }

    .league-header {
        background: linear-gradient(90deg, #0f3460 0%, transparent 100%);
        color: white;
        padding: 0.6rem 1.2rem;
        border-radius: 8px;
        margin: 1.5rem 0 0.8rem 0;
        font-weight: 600;
        font-size: 1rem;
    }

    .match-card {
        background: white;
        border: 1px solid #e8e8e8;
        border-radius: 12px;
        padding: 1rem 1.5rem;
        margin-bottom: 0.6rem;
        display: flex;
        align-items: center;
        justify-content: space-between;
        transition: box-shadow 0.2s;
    }
    .match-card:hover {
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
    }

    .team-name {
        font-weight: 600;
        font-size: 1rem;
        min-width: 180px;
    }
    .team-home { text-align: right; }
    .team-away { text-align: left; }

    .score-box {
        background: #1a1a2e;
        color: white;
        padding: 0.5rem 1.2rem;
        border-radius: 8px;
        font-size: 1.3rem;
        font-weight: 700;
        min-width: 80px;
        text-align: center;
        letter-spacing: 2px;
    }
    .score-box.pending {
        background: #6c757d;
        font-size: 0.9rem;
        letter-spacing: 0;
    }

    .status-badge {
        font-size: 0.75rem;
        font-weight: 600;
        padding: 0.25rem 0.6rem;
        border-radius: 20px;
        text-align: center;
        min-width: 60px;
    }
    .status-live {
        background: #e74c3c;
        color: white;
        animation: pulse 1.5s infinite;
    }
    .status-finished {
        background: #2ecc71;
        color: white;
    }
    .status-upcoming {
        background: #f39c12;
        color: white;
    }
    .status-halftime {
        background: #3498db;
        color: white;
    }

    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.6; }
    }

    .stat-card {
        background: white;
        border: 1px solid #e8e8e8;
        border-radius: 12px;
        padding: 1.5rem;
        text-align: center;
    }
    .stat-number {
        font-size: 2rem;
        font-weight: 700;
        color: #0f3460;
    }
    .stat-label {
        font-size: 0.85rem;
        color: #666;
        margin-top: 0.3rem;
    }

    /* Dark mode support */
    @media (prefers-color-scheme: dark) {
        .match-card { background: #1e1e1e; border-color: #333; }
        .stat-card { background: #1e1e1e; border-color: #333; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ─── Header ─────────────────────────────────────────────────────────────
st.markdown(
    """
    <div class="main-header">
        <h1>⚽ SportAI</h1>
        <p>Live-Fußball Ergebnisse &amp; Analyse – powered by kicker.de</p>
    </div>
    """,
    unsafe_allow_html=True,
)


# ─── Daten laden ────────────────────────────────────────────────────────
def get_status_class(status: str) -> str:
    """Bestimmt die CSS-Klasse basierend auf dem Spielstatus."""
    s = status.lower()
    if "beendet" in s or "ende" in s:
        return "status-finished"
    if "hz" in s or "halb" in s or "pause" in s:
        return "status-halftime"
    if "'" in status or "live" in s:
        return "status-live"
    return "status-upcoming"


def render_match(match: Match):
    """Rendert eine einzelne Spielkarte."""
    score_display = (
        f"{match.score_home} : {match.score_away}"
        if match.score_home is not None
        else "– : –"
    )
    score_class = "score-box" if match.score_home is not None else "score-box pending"
    status_class = get_status_class(match.status)

    st.markdown(
        f"""
        <div class="match-card">
            <span class="team-name team-home">{match.team_home}</span>
            <div style="display: flex; flex-direction: column; align-items: center; gap: 4px;">
                <div class="{score_class}">{score_display}</div>
                <span class="status-badge {status_class}">{match.status}</span>
            </div>
            <span class="team-name team-away">{match.team_away}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ─── Toolbar ─────────────────────────────────────────────────────────────
col_btn1, col_btn2, col_spacer = st.columns([1, 1, 4])

with col_btn1:
    load_live = st.button("🔄 Live-Daten laden", use_container_width=True)
with col_btn2:
    load_demo = st.button("📋 Demo-Daten", use_container_width=True)

# State management
if "matches" not in st.session_state:
    st.session_state.matches = []
    st.session_state.source = None

if load_live:
    scraper = KickerScraper()
    with st.spinner("Lade Live-Daten von kicker.de..."):
        try:
            st.session_state.matches = scraper.fetch_live_scores()
            st.session_state.source = "live"
            if not st.session_state.matches:
                st.info(
                    "Keine Live-Spiele gefunden. "
                    "Möglicherweise finden gerade keine Spiele statt."
                )
        except ConnectionError as e:
            st.error(f"Verbindungsfehler: {e}")
            st.session_state.matches = []

if load_demo:
    st.session_state.matches = get_demo_data()
    st.session_state.source = "demo"

matches: List[Match] = st.session_state.matches

# ─── Statistik-Karten ────────────────────────────────────────────────────
if matches:
    live_count = sum(1 for m in matches if "'" in m.status or "live" in m.status.lower())
    finished_count = sum(
        1 for m in matches if "beendet" in m.status.lower() or "ende" in m.status.lower()
    )
    total_goals = sum(
        (m.score_home or 0) + (m.score_away or 0) for m in matches
    )
    leagues = len(set(m.league for m in matches))

    st.markdown("")
    c1, c2, c3, c4 = st.columns(4)
    for col, number, label in [
        (c1, len(matches), "Spiele gesamt"),
        (c2, live_count, "Live jetzt"),
        (c3, total_goals, "Tore gesamt"),
        (c4, leagues, "Ligen"),
    ]:
        with col:
            st.markdown(
                f"""
                <div class="stat-card">
                    <div class="stat-number">{number}</div>
                    <div class="stat-label">{label}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # ─── Spiele nach Ligen gruppiert ─────────────────────────────────────
    st.markdown("")

    # Gruppiere nach Liga
    leagues_dict: Dict[str, List[Match]] = {}
    for m in matches:
        leagues_dict.setdefault(m.league, []).append(m)

    for league_name, league_matches in leagues_dict.items():
        st.markdown(
            f'<div class="league-header">🏆 {league_name}</div>',
            unsafe_allow_html=True,
        )
        for match in league_matches:
            render_match(match)

    # ─── Datenquelle ─────────────────────────────────────────────────────
    st.markdown("")
    if st.session_state.source == "demo":
        st.caption("📋 Demo-Daten – Klicke 'Live-Daten laden' für echte Ergebnisse")
    else:
        st.caption("🔄 Quelle: kicker.de – Live-Daten")
else:
    # ─── Willkommens-Screen ──────────────────────────────────────────────
    st.markdown("")
    st.markdown("")
    col_l, col_c, col_r = st.columns([1, 2, 1])
    with col_c:
        st.markdown(
            """
            <div style="text-align: center; padding: 3rem 0;">
                <div style="font-size: 4rem; margin-bottom: 1rem;">⚽</div>
                <h3 style="color: #0f3460;">Willkommen bei SportAI</h3>
                <p style="color: #666; max-width: 400px; margin: 0 auto;">
                    Klicke oben auf <strong>Live-Daten laden</strong> um aktuelle
                    Fußball-Ergebnisse von kicker.de abzurufen, oder nutze
                    <strong>Demo-Daten</strong> um die App zu testen.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
