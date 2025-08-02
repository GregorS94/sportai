{\rtf1\ansi\ansicpg1252\cocoartf2822
\cocoatextscaling0\cocoaplatform0{\fonttbl\f0\fswiss\fcharset0 Helvetica;}
{\colortbl;\red255\green255\blue255;}
{\*\expandedcolortbl;;}
\paperw11900\paperh16840\margl1440\margr1440\vieww11520\viewh8400\viewkind0
\pard\tx566\tx1133\tx1700\tx2267\tx2834\tx3401\tx3968\tx4535\tx5102\tx5669\tx6236\tx6803\pardirnatural\partightenfactor0

\f0\fs24 \cf0 import streamlit as st\
from scraper.kicker import fetch_kicker_data\
\
st.set_page_config(page_title="SportAI \'96 Tor-Prognose", layout="wide")\
st.title("\uc0\u9917  SportAI: Analyse Live-Spiele")\
\
st.write("Dieses Dashboard zeigt Live-Spieldaten (aktuell nur von kicker.de).")\
st.write("Weitere Quellen und Vorhersagemodell folgen.")\
\
if st.button("\uc0\u55357 \u56580  Daten aktualisieren"):\
    spiele = fetch_kicker_data()\
    if spiele:\
        st.subheader("Aktuelle Spiele (Kicker.de):")\
        for spiel in spiele:\
            st.write(f"\uc0\u55356 \u56730  \{spiel['team1']\} vs \{spiel['team2']\}")\
            st.write(f"\uc0\u9201  \{spiel['minute']\}, Spielstand: \{spiel['score']\}")\
            st.markdown("---")\
    else:\
        st.warning("Keine Spieldaten gefunden oder Fehler beim Abruf.")\
}