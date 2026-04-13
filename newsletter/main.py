"""Newsletter Mailing – FastAPI entry point."""
import csv
import io
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from database import get_db, init_db
from mailer import (
    MASKED,
    get_smtp_settings,
    save_smtp_settings,
    send_campaign,
    send_test_mail,
)
from renderer import render_newsletter_html

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(title="Newsletter Mailing", version="1.0.0")


@app.on_event("startup")
def on_startup() -> None:
    init_db()


# ---------- Static pages ----------
@app.get("/", response_class=HTMLResponse)
def page_index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/designer", response_class=HTMLResponse)
def page_designer():
    return FileResponse(STATIC_DIR / "designer.html")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# ---------- Pydantic models ----------
class NewsletterIn(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    subject: str = ""
    preheader: str = ""
    blocks: list = Field(default_factory=list)


class ListIn(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)


class RecipientIn(BaseModel):
    email: str
    name: str = ""
    list_id: Optional[int] = None


class SettingsIn(BaseModel):
    smtp_host: str
    smtp_port: int = 465
    smtp_user: str = ""
    smtp_password: Optional[str] = None
    smtp_security: str = "ssl"
    from_email: str = ""
    from_name: str = ""


class SendIn(BaseModel):
    list_id: Optional[int] = None
    test_email: Optional[str] = None


# ---------- Newsletters ----------
@app.get("/api/newsletters")
def api_list_newsletters():
    with get_db() as db:
        rows = db.execute(
            "SELECT id, name, subject, preheader, created_at, updated_at "
            "FROM newsletters ORDER BY updated_at DESC"
        ).fetchall()
        return [dict(row) for row in rows]


@app.post("/api/newsletters")
def api_create_newsletter(data: NewsletterIn):
    now = datetime.utcnow().isoformat()
    with get_db() as db:
        cur = db.execute(
            "INSERT INTO newsletters (name, subject, preheader, blocks, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (data.name, data.subject, data.preheader, json.dumps(data.blocks), now, now),
        )
        db.commit()
        return {"id": cur.lastrowid}


@app.get("/api/newsletters/{nid}")
def api_get_newsletter(nid: int):
    with get_db() as db:
        row = db.execute("SELECT * FROM newsletters WHERE id = ?", (nid,)).fetchone()
        if not row:
            raise HTTPException(404, "Newsletter nicht gefunden")
        data = dict(row)
        data["blocks"] = json.loads(data["blocks"] or "[]")
        return data


@app.put("/api/newsletters/{nid}")
def api_update_newsletter(nid: int, data: NewsletterIn):
    now = datetime.utcnow().isoformat()
    with get_db() as db:
        res = db.execute(
            "UPDATE newsletters SET name = ?, subject = ?, preheader = ?, "
            "blocks = ?, updated_at = ? WHERE id = ?",
            (data.name, data.subject, data.preheader, json.dumps(data.blocks), now, nid),
        )
        db.commit()
        if res.rowcount == 0:
            raise HTTPException(404, "Newsletter nicht gefunden")
        return {"ok": True}


@app.delete("/api/newsletters/{nid}")
def api_delete_newsletter(nid: int):
    with get_db() as db:
        db.execute("DELETE FROM newsletters WHERE id = ?", (nid,))
        db.commit()
        return {"ok": True}


@app.post("/api/newsletters/{nid}/duplicate")
def api_duplicate_newsletter(nid: int):
    with get_db() as db:
        row = db.execute("SELECT * FROM newsletters WHERE id = ?", (nid,)).fetchone()
        if not row:
            raise HTTPException(404)
        now = datetime.utcnow().isoformat()
        cur = db.execute(
            "INSERT INTO newsletters (name, subject, preheader, blocks, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (f"{row['name']} (Kopie)", row["subject"], row["preheader"],
             row["blocks"], now, now),
        )
        db.commit()
        return {"id": cur.lastrowid}


@app.get("/api/newsletters/{nid}/preview", response_class=HTMLResponse)
def api_preview_newsletter(nid: int):
    with get_db() as db:
        row = db.execute("SELECT * FROM newsletters WHERE id = ?", (nid,)).fetchone()
        if not row:
            raise HTTPException(404)
        blocks = json.loads(row["blocks"] or "[]")
        html = render_newsletter_html(blocks, row["subject"], row["preheader"])
        return HTMLResponse(html)


class PreviewIn(BaseModel):
    blocks: list = Field(default_factory=list)
    subject: str = ""
    preheader: str = ""


@app.post("/api/preview", response_class=HTMLResponse)
def api_preview(data: PreviewIn):
    html = render_newsletter_html(data.blocks, data.subject, data.preheader)
    return HTMLResponse(html)


# ---------- Lists ----------
@app.get("/api/lists")
def api_list_lists():
    with get_db() as db:
        rows = db.execute(
            "SELECT l.id, l.name, l.created_at, "
            "COUNT(r.id) AS recipient_count "
            "FROM lists l LEFT JOIN recipients r ON r.list_id = l.id "
            "GROUP BY l.id ORDER BY l.name"
        ).fetchall()
        return [dict(r) for r in rows]


@app.post("/api/lists")
def api_create_list(data: ListIn):
    with get_db() as db:
        try:
            cur = db.execute(
                "INSERT INTO lists (name, created_at) VALUES (?, ?)",
                (data.name, datetime.utcnow().isoformat()),
            )
            db.commit()
            return {"id": cur.lastrowid}
        except sqlite3.IntegrityError:
            raise HTTPException(400, "Liste mit diesem Namen existiert bereits")


@app.delete("/api/lists/{lid}")
def api_delete_list(lid: int):
    with get_db() as db:
        db.execute("DELETE FROM lists WHERE id = ?", (lid,))
        db.commit()
        return {"ok": True}


# ---------- Recipients ----------
@app.get("/api/recipients")
def api_list_recipients(list_id: Optional[int] = None):
    with get_db() as db:
        if list_id is not None:
            rows = db.execute(
                "SELECT * FROM recipients WHERE list_id = ? ORDER BY email",
                (list_id,),
            ).fetchall()
        else:
            rows = db.execute(
                "SELECT * FROM recipients ORDER BY email"
            ).fetchall()
        return [dict(r) for r in rows]


def _validate_email(email: str) -> str:
    email = (email or "").strip().lower()
    if "@" not in email or "." not in email.split("@")[-1]:
        raise HTTPException(400, "Ungültige E-Mail-Adresse")
    return email


@app.post("/api/recipients")
def api_add_recipient(data: RecipientIn):
    email = _validate_email(data.email)
    with get_db() as db:
        try:
            cur = db.execute(
                "INSERT INTO recipients (email, name, list_id, created_at) "
                "VALUES (?, ?, ?, ?)",
                (email, data.name or "", data.list_id, datetime.utcnow().isoformat()),
            )
            db.commit()
            return {"id": cur.lastrowid}
        except sqlite3.IntegrityError:
            raise HTTPException(400, "Diese Adresse ist bereits in der Liste")


@app.delete("/api/recipients/{rid}")
def api_delete_recipient(rid: int):
    with get_db() as db:
        db.execute("DELETE FROM recipients WHERE id = ?", (rid,))
        db.commit()
        return {"ok": True}


@app.post("/api/recipients/import")
async def api_import_recipients(
    list_id: int = Form(...),
    file: UploadFile = File(...),
):
    raw = await file.read()
    text = raw.decode("utf-8", errors="ignore")
    # Handle both comma and semicolon (common in German CSVs).
    sample = text[:2048]
    delim = ";" if sample.count(";") > sample.count(",") else ","
    reader = csv.DictReader(io.StringIO(text), delimiter=delim)
    added = skipped = 0
    with get_db() as db:
        for row in reader:
            # accept common column header variants
            email = (
                row.get("email")
                or row.get("Email")
                or row.get("E-Mail")
                or row.get("e-mail")
                or row.get("EMAIL")
                or ""
            ).strip().lower()
            name = (row.get("name") or row.get("Name") or "").strip()
            if "@" not in email:
                skipped += 1
                continue
            try:
                db.execute(
                    "INSERT INTO recipients (email, name, list_id, created_at) "
                    "VALUES (?, ?, ?, ?)",
                    (email, name, list_id, datetime.utcnow().isoformat()),
                )
                added += 1
            except sqlite3.IntegrityError:
                skipped += 1
        db.commit()
    return {"added": added, "skipped": skipped}


# ---------- Settings ----------
@app.get("/api/settings")
def api_get_settings():
    settings = get_smtp_settings()
    if settings.get("smtp_password"):
        settings["smtp_password"] = MASKED
    return settings


@app.post("/api/settings")
def api_save_settings(data: SettingsIn):
    save_smtp_settings(data.model_dump())
    return {"ok": True}


# ---------- Sending ----------
@app.post("/api/newsletters/{nid}/test")
def api_test_send(nid: int, data: SendIn):
    if not data.test_email:
        raise HTTPException(400, "test_email ist erforderlich")
    email = _validate_email(data.test_email)
    with get_db() as db:
        row = db.execute("SELECT * FROM newsletters WHERE id = ?", (nid,)).fetchone()
        if not row:
            raise HTTPException(404)
        blocks = json.loads(row["blocks"] or "[]")
        html = render_newsletter_html(blocks, row["subject"], row["preheader"])
    try:
        send_test_mail(email, row["subject"] or row["name"], html)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(500, f"Versand fehlgeschlagen: {exc}")
    return {"ok": True}


@app.post("/api/newsletters/{nid}/send")
def api_send_newsletter(nid: int, data: SendIn, background: BackgroundTasks):
    with get_db() as db:
        row = db.execute("SELECT * FROM newsletters WHERE id = ?", (nid,)).fetchone()
        if not row:
            raise HTTPException(404)
        if data.list_id is not None:
            rcpt_rows = db.execute(
                "SELECT email, name FROM recipients WHERE list_id = ?",
                (data.list_id,),
            ).fetchall()
        else:
            rcpt_rows = db.execute(
                "SELECT email, name FROM recipients"
            ).fetchall()
        recipients = [dict(r) for r in rcpt_rows]
        if not recipients:
            raise HTTPException(400, "Keine Empfänger in der gewählten Liste")
        cur = db.execute(
            "INSERT INTO campaigns (newsletter_id, list_id, total, status, started_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (nid, data.list_id, len(recipients), "running",
             datetime.utcnow().isoformat()),
        )
        campaign_id = cur.lastrowid
        db.commit()
        newsletter = {
            "id": row["id"],
            "subject": row["subject"],
            "preheader": row["preheader"],
            "blocks": json.loads(row["blocks"] or "[]"),
        }
    background.add_task(send_campaign, campaign_id, newsletter, recipients)
    return {"campaign_id": campaign_id, "recipients": len(recipients)}


# ---------- Campaigns / history ----------
@app.get("/api/campaigns")
def api_list_campaigns():
    with get_db() as db:
        rows = db.execute(
            "SELECT c.*, n.name AS newsletter_name, l.name AS list_name "
            "FROM campaigns c "
            "LEFT JOIN newsletters n ON n.id = c.newsletter_id "
            "LEFT JOIN lists l ON l.id = c.list_id "
            "ORDER BY c.started_at DESC LIMIT 200"
        ).fetchall()
        return [dict(r) for r in rows]


@app.get("/api/campaigns/{cid}")
def api_get_campaign(cid: int):
    with get_db() as db:
        row = db.execute("SELECT * FROM campaigns WHERE id = ?", (cid,)).fetchone()
        if not row:
            raise HTTPException(404)
        logs = db.execute(
            "SELECT * FROM campaign_logs WHERE campaign_id = ? ORDER BY id DESC",
            (cid,),
        ).fetchall()
        return {**dict(row), "logs": [dict(log) for log in logs]}
