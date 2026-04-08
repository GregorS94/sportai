from __future__ import annotations

import sys
import os
from pathlib import Path
from typing import List

# Ensure project root is on sys.path (needed for Streamlit Cloud)
_root = str(Path(__file__).resolve().parent.parent)
if _root not in sys.path:
    sys.path.insert(0, _root)

import streamlit as st
from scraper.kicker import KickerScraper, Match, get_demo_data

# ─── Seiten-Konfiguration ───────────────────────────────────────────────
st.set_page_config(
    page_title="SportAI – Live Analyse",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─── BetScope-Style CSS ─────────────────────────────────────────────────
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    /* Global dark theme */
    .stApp, .main, section[data-testid="stSidebar"] {
        background-color: #0a0a0a !important;
        color: #e0e0e0 !important;
    }
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
        color: #e0e0e0;
    }
    header[data-testid="stHeader"] {
        background-color: #0a0a0a !important;
    }

    /* Hide Streamlit branding */
    #MainMenu, footer, header {visibility: hidden;}
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 0 !important;
        max-width: 1400px;
    }

    /* ─── Top Bar ─── */
    .topbar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0.8rem 1.5rem;
        border-bottom: 1px solid #1a1a1a;
        margin-bottom: 1rem;
    }
    .topbar-logo {
        font-size: 1.5rem;
        font-weight: 800;
        letter-spacing: 1px;
    }
    .topbar-logo span { color: #ffffff; }
    .topbar-logo .accent { color: #d4a017; }
    .live-badge {
        background: transparent;
        border: 1px solid #d4a017;
        color: #d4a017;
        padding: 0.3rem 1rem;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
        display: inline-flex;
        align-items: center;
        gap: 6px;
    }
    .live-dot {
        width: 8px;
        height: 8px;
        background: #e74c3c;
        border-radius: 50%;
        display: inline-block;
        animation: blink 1.2s infinite;
    }
    @keyframes blink {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.3; }
    }

    /* ─── Stats Table ─── */
    .stats-table-wrapper {
        background: #111111;
        border: 1px solid #2a2a1a;
        border-radius: 12px;
        overflow-x: auto;
        margin-top: 0.5rem;
    }
    .stats-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 0.82rem;
        min-width: 1100px;
    }
    .stats-table thead th {
        background: #151515;
        color: #888;
        font-weight: 500;
        padding: 10px 6px;
        text-align: center;
        border-bottom: 1px solid #222;
        font-size: 1rem;
        position: sticky;
        top: 0;
        z-index: 10;
    }
    .stats-table thead th.col-teams {
        text-align: left;
        padding-left: 12px;
        color: #d4a017;
        font-weight: 600;
        font-size: 0.75rem;
        letter-spacing: 1px;
        text-transform: uppercase;
    }

    /* Row styles */
    .stats-table tbody tr {
        border-bottom: 1px solid #1a1a1a;
        transition: background 0.15s;
    }
    .stats-table tbody tr:hover {
        background: #1a1a12;
    }
    .stats-table tbody td {
        padding: 6px 6px;
        text-align: center;
        vertical-align: middle;
        color: #ccc;
        font-variant-numeric: tabular-nums;
    }

    /* Pinned rows */
    .pinned-section {
        border-bottom: 2px solid #d4a01744;
    }
    .pinned-label {
        background: #151515;
        color: #d4a017;
        font-size: 0.7rem;
        font-weight: 600;
        padding: 6px 12px;
        letter-spacing: 0.5px;
    }
    .row-pinned {
        background: #14140e !important;
    }
    .row-pinned:hover {
        background: #1c1c12 !important;
    }

    /* Minute column */
    .col-minute {
        color: #d4a017 !important;
        font-weight: 700;
        font-size: 0.9rem !important;
        width: 50px;
        white-space: nowrap;
    }

    /* Score column */
    .col-score {
        font-weight: 600;
        width: 30px;
        font-size: 0.85rem !important;
    }

    /* Team column */
    .col-team {
        text-align: left !important;
        padding-left: 8px !important;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        max-width: 180px;
    }
    .team-home { color: #e0e0e0; font-weight: 500; }
    .team-away { color: #999; font-weight: 400; }

    /* Flag */
    .flag {
        font-size: 0.9rem;
        margin-right: 4px;
    }

    /* Stat cells */
    .stat-val { color: #bbb; }
    .stat-highlight {
        color: #d4a017 !important;
        font-weight: 700;
        background: #d4a01718;
        border-radius: 4px;
        padding: 2px 6px;
    }

    /* Possession bar */
    .poss-text {
        font-size: 0.8rem;
        font-weight: 500;
    }
    .poss-dominant { color: #d4a017; font-weight: 600; }

    /* Two-row per match layout */
    .match-row-home td { padding-top: 8px; padding-bottom: 2px; }
    .match-row-away td { padding-top: 2px; padding-bottom: 8px; }

    /* Separator between minute group */
    .minute-cell {
        vertical-align: middle;
    }

    /* Cards colors */
    .yellow-card { color: #f1c40f; }
    .red-card { color: #e74c3c; }

    /* Feature cards */
    .feature-cards {
        display: flex;
        gap: 1rem;
        margin: 1.5rem 0;
        flex-wrap: wrap;
    }
    .feature-card {
        background: #151515;
        border: 1px solid #222;
        border-radius: 10px;
        padding: 1.2rem 1.5rem;
        flex: 1;
        min-width: 150px;
        text-align: center;
    }
    .feature-card .fc-icon {
        font-size: 1.5rem;
        margin-bottom: 0.5rem;
    }
    .feature-card .fc-title {
        color: #fff;
        font-weight: 600;
        font-size: 0.9rem;
    }
    .feature-card .fc-sub {
        color: #d4a017;
        font-weight: 600;
        font-size: 0.85rem;
    }

    /* Button overrides */
    .stButton > button {
        background: #1a1a1a !important;
        color: #d4a017 !important;
        border: 1px solid #d4a017 !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        transition: all 0.2s !important;
    }
    .stButton > button:hover {
        background: #d4a017 !important;
        color: #000 !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ─── Top Bar ─────────────────────────────────────────────────────────────
st.markdown(
    """
    <div class="topbar">
        <div class="topbar-logo">
            <span>SPORT</span><span class="accent">AI</span>
        </div>
        <div class="live-badge">
            <span class="live-dot"></span>
            LIVE SOFTWARE
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)


# ─── Feature Cards ───────────────────────────────────────────────────────
st.markdown(
    """
    <div class="feature-cards">
        <div class="feature-card">
            <div class="fc-icon">🎯</div>
            <div class="fc-title">Bewährte</div>
            <div class="fc-sub">Strategien</div>
        </div>
        <div class="feature-card">
            <div class="fc-icon">✅</div>
            <div class="fc-title">Erfolgreich</div>
            <div class="fc-sub">Backtested</div>
        </div>
        <div class="feature-card">
            <div class="fc-icon">⚡</div>
            <div class="fc-title">Intelligente</div>
            <div class="fc-sub">KI-Analyse</div>
        </div>
        <div class="feature-card">
            <div class="fc-icon">📊</div>
            <div class="fc-title">Live</div>
            <div class="fc-sub">Statistiken</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)


# ─── Buttons ─────────────────────────────────────────────────────────────
col1, col2, col3 = st.columns([1, 1, 4])
with col1:
    load_live = st.button("🔄 Live-Daten laden", use_container_width=True)
with col2:
    load_demo = st.button("📋 Demo-Daten", use_container_width=True)

# ─── State Management ────────────────────────────────────────────────────
if "matches" not in st.session_state:
    st.session_state.matches = []  # type: List[Match]

if load_live:
    scraper = KickerScraper()
    with st.spinner("Lade Live-Daten von kicker.de..."):
        try:
            st.session_state.matches = scraper.fetch_live_scores()
            if not st.session_state.matches:
                st.info("Keine Live-Spiele gefunden.")
        except ConnectionError as e:
            st.error(str(e))

if load_demo:
    st.session_state.matches = get_demo_data()

matches = st.session_state.matches  # type: List[Match]


# ─── Render Table ────────────────────────────────────────────────────────
def highlight_val(val_home, val_away):
    """Returns CSS classes for home/away: highlight the higher value."""
    if val_home > val_away:
        return "stat-highlight", "stat-val"
    elif val_away > val_home:
        return "stat-val", "stat-highlight"
    return "stat-val", "stat-val"


def render_table(matches_list):
    """Rendert die BetScope-Style Statistik-Tabelle."""
    if not matches_list:
        return

    pinned = [m for m in matches_list if m.pinned]
    unpinned = [m for m in matches_list if not m.pinned]

    # Column headers with icons
    header = """
    <div class="stats-table-wrapper">
    <table class="stats-table">
    <thead>
        <tr>
            <th style="width:50px;">⏱</th>
            <th style="width:30px;"></th>
            <th class="col-teams" style="min-width:160px;">TEAMS</th>
            <th title="Angriffe">🔥</th>
            <th title="Gefährliche Angriffe">⚡</th>
            <th title="Ballbesitz">🏟️</th>
            <th title="Schüsse aufs Tor">🎯</th>
            <th title="Schüsse daneben">❌</th>
            <th title="Ecken">⚔️</th>
            <th title="Tore">🥅</th>
            <th title="Paraden">🧤</th>
            <th title="Fouls">🔨</th>
            <th title="Gelbe Karten">🟨</th>
            <th title="Rote Karten">🟥</th>
            <th title="Abseits">🚫</th>
        </tr>
    </thead>
    <tbody>
    """

    rows = ""

    # Pinned section
    if pinned:
        rows += '<tr class="pinned-section"><td colspan="15" class="pinned-label">📌 FIXIERT (%d)</td></tr>' % len(pinned)
        for m in pinned:
            rows += _render_match_rows(m, pinned=True)

    # Regular matches
    for m in unpinned:
        rows += _render_match_rows(m, pinned=False)

    footer = """
    </tbody>
    </table>
    </div>
    """

    st.markdown(header + rows + footer, unsafe_allow_html=True)


def _render_match_rows(m, pinned=False):
    """Rendert zwei Zeilen (Home + Away) für ein Match."""
    row_class = "row-pinned" if pinned else ""
    h = m.stats_home
    a = m.stats_away

    # Determine highlights per stat
    atk_h, atk_a = highlight_val(h.attacks, a.attacks)
    datk_h, datk_a = highlight_val(h.dangerous_attacks, a.dangerous_attacks)
    poss_h_cls = "poss-dominant" if h.possession > a.possession else "poss-text"
    poss_a_cls = "poss-dominant" if a.possession > h.possession else "poss-text"
    sot_h, sot_a = highlight_val(h.shots_on_target, a.shots_on_target)
    soff_h, soff_a = highlight_val(h.shots_off_target, a.shots_off_target)
    cor_h, cor_a = highlight_val(h.corners, a.corners)
    g_h, g_a = highlight_val(h.goals, a.goals)
    sv_h, sv_a = highlight_val(h.saves, a.saves)
    fl_h, fl_a = highlight_val(h.fouls, a.fouls)

    # Home row
    home_row = (
        '<tr class="match-row-home %s">'
        '<td class="col-minute minute-cell" rowspan="2">%s</td>'
        '<td class="col-score">%d</td>'
        '<td class="col-team"><span class="flag">%s</span><span class="team-home">%s</span></td>'
        '<td class="%s">%d</td>'
        '<td class="%s">%d</td>'
        '<td class="%s">%d%%</td>'
        '<td class="%s">%d</td>'
        '<td class="%s">%d</td>'
        '<td class="%s">%d</td>'
        '<td class="%s">%d</td>'
        '<td class="%s">%d</td>'
        '<td class="%s">%d</td>'
        '<td class="yellow-card">%d</td>'
        '<td class="red-card">%d</td>'
        '<td class="stat-val">%d</td>'
        '</tr>'
    ) % (
        row_class, m.minute, m.score_home,
        m.country_home, m.team_home,
        atk_h, h.attacks, datk_h, h.dangerous_attacks,
        poss_h_cls, h.possession,
        sot_h, h.shots_on_target, soff_h, h.shots_off_target,
        cor_h, h.corners, g_h, h.goals, sv_h, h.saves,
        fl_h, h.fouls,
        h.yellow_cards, h.red_cards, h.offsides,
    )

    # Away row
    away_row = (
        '<tr class="match-row-away %s">'
        '<td class="col-score">%d</td>'
        '<td class="col-team"><span class="flag">%s</span><span class="team-away">%s</span></td>'
        '<td class="%s">%d</td>'
        '<td class="%s">%d</td>'
        '<td class="%s">%d%%</td>'
        '<td class="%s">%d</td>'
        '<td class="%s">%d</td>'
        '<td class="%s">%d</td>'
        '<td class="%s">%d</td>'
        '<td class="%s">%d</td>'
        '<td class="%s">%d</td>'
        '<td class="yellow-card">%d</td>'
        '<td class="red-card">%d</td>'
        '<td class="stat-val">%d</td>'
        '</tr>'
    ) % (
        row_class, m.score_away,
        m.country_away, m.team_away,
        atk_a, a.attacks, datk_a, a.dangerous_attacks,
        poss_a_cls, a.possession,
        sot_a, a.shots_on_target, soff_a, a.shots_off_target,
        cor_a, a.corners, g_a, a.goals, sv_a, a.saves,
        fl_a, a.fouls,
        a.yellow_cards, a.red_cards, a.offsides,
    )

    return home_row + away_row


# ─── Main Content ────────────────────────────────────────────────────────
if matches:
    render_table(matches)

    st.markdown(
        '<p style="text-align:center; color:#555; font-size:0.75rem; margin-top:1rem;">'
        'SportAI – Live-Analyse | Daten werden nicht automatisch aktualisiert</p>',
        unsafe_allow_html=True,
    )
else:
    st.markdown(
        """
        <div style="text-align:center; padding: 4rem 0;">
            <div style="font-size: 3.5rem; margin-bottom: 1rem;">⚽</div>
            <h2 style="color: #fff; font-weight: 800; font-size: 2.5rem; margin-bottom: 0.5rem;">
                Bet Like a Pro
            </h2>
            <p style="color: #888; font-size: 1.1rem; margin-bottom: 2rem;">
                Finde Live-Analyse Chancen in Sekunden mit <span style="color:#fff;font-weight:700;">SPORT</span><span style="color:#d4a017;font-weight:700;">AI</span>
            </p>
            <p style="color: #555; font-size: 0.9rem;">
                Klicke oben auf <strong style="color:#d4a017;">Demo-Daten</strong> um die App zu testen
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
