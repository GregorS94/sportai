{\rtf1\ansi\ansicpg1252\cocoartf2822
\cocoatextscaling0\cocoaplatform0{\fonttbl\f0\fswiss\fcharset0 Helvetica;}
{\colortbl;\red255\green255\blue255;}
{\*\expandedcolortbl;;}
\paperw11900\paperh16840\margl1440\margr1440\vieww11520\viewh8400\viewkind0
\pard\tx566\tx1133\tx1700\tx2267\tx2834\tx3401\tx3968\tx4535\tx5102\tx5669\tx6236\tx6803\pardirnatural\partightenfactor0

\f0\fs24 \cf0 import requests\
from bs4 import BeautifulSoup\
\
def fetch_kicker_data():\
    url = "https://www.kicker.de/livescores/fussball"\
    try:\
        response = requests.get(url, headers=\{"User-Agent": "Mozilla/5.0"\})\
        soup = BeautifulSoup(response.text, "html.parser")\
\
        spiele = []\
\
        for container in soup.select("div.livebox"):\
            try:\
                team1 = container.select_one("span.team.left").get_text(strip=True)\
                team2 = container.select_one("span.team.right").get_text(strip=True)\
                score = container.select_one("div.score").get_text(strip=True)\
                minute = container.select_one("div.time").get_text(strip=True)\
                spiele.append(\{\
                    "team1": team1,\
                    "team2": team2,\
                    "score": score,\
                    "minute": minute\
                \})\
            except:\
                continue\
\
        return spiele\
\
    except Exception as e:\
        return [\{"error": str(e)\}]\
}