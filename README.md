# SportAI

Live-Spiel-Analyse mit genau den Stats aus der Referenz-Grafik:
**Scope Score**, **Gefahr-Score**, Ballbesitz, Torschüsse, Gef. Angriffe,
Ecken, xG sowie Torschüsse der letzten 10 Minuten.

> Datenquelle aktuell: **Mock-Data** (`app/core/mock_data.py`). Eine echte
> Stats-API (z. B. API-Football) lässt sich später anstelle der Mock-Quelle
> einhängen, ohne dass sich Layout oder Scores ändern.

## Projektstruktur

```
app/
  core/
    models.py      # Datenmodell (TeamStats, Match)
    scoring.py     # Scope Score & Gefahr-Score (Formeln + Gewichte)
    formatting.py  # exaktes Stat-Layout (Telegram-Block)
    mock_data.py   # Beispiel-Spiele (1. Spiel = Referenz-Grafik)
  streamlit_app.py # Dashboard
bot/
  telegram_bot.py  # postet das Layout pro Spiel nach Telegram
scraper/
  kicker.py        # Basis-Scraper (Teams/Spielstand/Minute)
```

## Starten

### Dashboard (Streamlit)
```
pip install -r requirements.txt
streamlit run app/streamlit_app.py
```

### Telegram-Bot
```
# Vorschau ohne Versand:
python -m bot.telegram_bot --dry-run

# Echter Versand:
export TELEGRAM_BOT_TOKEN="<token von @BotFather>"
export TELEGRAM_CHAT_ID="<chat-/kanal-id>"
python -m bot.telegram_bot
```

## Score-Formeln

Beide Kennzahlen werden pro Team aus den Basis-Stats berechnet. Die Gewichte
stehen als Konstanten in `app/core/scoring.py` und lassen sich frei anpassen.

**Gefahr-Score** – akute Torgefahr:
```
20 · xG  +  3 · Torschüsse  +  2 · Ecken
```

**Scope Score** – Gesamt-Dominanz (Torgefahr + Momentum + Ballkontrolle):
```
20 · xG  +  6 · Torschüsse  +  4 · Ecken
       +  4 · Torschüsse(letzte 10 Min)
       +  2 · (Ballbesitz% − 50, min. 0)
```

Mit den Default-Gewichten ergeben sich für die Referenz-Grafik exakt die
gezeigten Werte:

| Team     | Scope | Gefahr |
|----------|------:|-------:|
| Colombia |   104 |     29 |
| Congo DR |     0 |      0 |
