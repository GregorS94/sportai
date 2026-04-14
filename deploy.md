# Seelenmut – Deployment Guide

Drei Container, ein `docker compose up -d`:

| Service    | Image / Build        | Zweck                                    |
|------------|----------------------|------------------------------------------|
| `cms`      | `./cms` (FastAPI)    | Admin UI + JSON API, SQLite-Persistenz   |
| `frontend` | `./frontend` (Astro) | Öffentliche Seite, SSR aus CMS-Daten     |
| `caddy`    | `caddy:2-alpine`     | HTTPS-Reverse-Proxy, holt LE-Zertifikate |

```
          Internet (443)
               │
             Caddy
           ┌───┴───────────────────────────┐
           ▼                               ▼
  seelenmut.net  ─────►  frontend (Astro)  │
                                           │
  admin.seelenmut.net ───►  cms (FastAPI)  │
  seelenmut.net/media/* ─►  cms (FastAPI)  │
```

## 1. VPS-Vorbereitung

Empfehlung: **Hetzner Cloud CX22** (~4 €/Monat, Standort Falkenstein/Nürnberg → DSGVO-freundlich).
Alternativ Netcup, Contabo oder ein vorhandener Server.

Auf dem frischen Server:

```bash
# Docker installieren (Debian/Ubuntu)
curl -fsSL https://get.docker.com | sh

# Repo klonen
git clone https://github.com/GregorS94/sportai.git
cd sportai
git checkout claude/newsletter-web-app-TjSSK   # bis der Branch auf main ist
```

## 2. DNS

Lege beim Domain-Registrar zwei A-Records an (beide zeigen auf die VPS-IP):

| Name                   | Typ | Wert          |
|------------------------|-----|---------------|
| `seelenmut.net`        | A   | VPS-IPv4      |
| `www.seelenmut.net`    | A   | VPS-IPv4      |
| `admin.seelenmut.net`  | A   | VPS-IPv4      |

Optional zusätzlich die AAAA-Records auf die IPv6.

## 3. Konfiguration

```bash
cp .env.example .env
```

Anschließend `.env` öffnen und setzen:

```env
CMS_ADMIN_USER=dein-benutzer
CMS_ADMIN_PASSWORD=ein-starkes-passwort
CMS_SECRET_KEY=<openssl rand -hex 32>
CMS_CORS_ORIGINS=https://seelenmut.net,https://www.seelenmut.net
```

Danach `Caddyfile` öffnen und `ADMIN_EMAIL` durch deine E-Mail-Adresse ersetzen
(wird für Let's-Encrypt-Benachrichtigungen verwendet).

## 4. Start

```bash
docker compose up -d --build
```

Was jetzt passiert:

1. `cms` baut das Python-Image und startet uvicorn auf Port 8000 (intern)
2. `frontend` baut das Astro-SSR-Image und startet Node auf Port 4321 (intern)
3. `caddy` bindet 80/443, holt automatisch LE-Zertifikate für alle drei Domains

Ersten Status checken:

```bash
docker compose ps
docker compose logs -f caddy
```

## 5. Erster Login

Öffne `https://admin.seelenmut.net` im Browser, logge dich mit deinen
`.env`-Credentials ein und lege an:

- **Seiten**: „Über mich", „Angebote", „Kontakt", „Impressum", „Datenschutz"
- **Blogposts**: erste Einträge nach Lust und Laune
- **Medien**: Bilder hochladen, werden im `cms_data`-Volume gespeichert

Sobald etwas als „Veröffentlicht" gespeichert ist, erscheint es automatisch auf
`seelenmut.net` — Astro holt die Daten bei jedem Request frisch vom CMS.

## 6. Updates deployen

```bash
git pull
docker compose up -d --build
```

Nur der betroffene Container wird neu gebaut (Astro-Änderungen → nur `frontend`,
CMS-Änderungen → nur `cms`).

## 7. Backup

Die kompletten Nutzdaten liegen im Docker-Volume `sportai_cms_data`
(`/app/data/cms.db` + `/app/data/media/`).

Einfachstes Backup:

```bash
docker run --rm -v sportai_cms_data:/data -v $PWD:/backup alpine \
  tar czf /backup/seelenmut-$(date +%F).tar.gz -C /data .
```

Cron-Job ergänzen und die Archive z. B. per `rclone` auf einen zweiten Ort
schieben.

## 8. Lokale Entwicklung

```bash
# CMS
cd cms
pip install -r requirements.txt
CMS_ADMIN_USER=admin CMS_ADMIN_PASSWORD=admin \
CMS_SECRET_KEY=dev CMS_DB=./data/cms.db \
uvicorn main:app --reload --port 8000

# In einem zweiten Terminal: Frontend
cd frontend
npm install
CMS_URL=http://localhost:8000 npm run dev
# → http://localhost:4321
```

## Troubleshooting

**`caddy` kann kein Zertifikat holen** → DNS-Eintrag noch nicht propagiert,
Port 80 ist durch eine Firewall blockiert oder Caddy erreicht LE nicht.
`docker compose logs caddy` zeigt den genauen Grund.

**Frontend zeigt „CMS /api/... -> 502"** → `cms` ist noch nicht bereit oder
abgestürzt. `docker compose logs cms` prüfen.

**Bilder brechen** → Der Pfad `/media/*` wird auf dem Public-Host direkt auf
den CMS-Container durchgereicht. Falls die Bilder 404 liefern, prüfe, ob der
Caddy-Block für `/media/*` im `Caddyfile` korrekt ist.
