"""SMTP mailer with all-inkl.com defaults and background campaign sender."""
import os
import smtplib
import ssl
import time
from datetime import datetime
from email.message import EmailMessage
from email.utils import formataddr, make_msgid

from database import get_db
from renderer import personalize, render_newsletter_html

# all-inkl.com defaults
DEFAULT_SETTINGS = {
    "smtp_host": "smtp.kasserver.com",
    "smtp_port": "465",
    "smtp_security": "ssl",
    "smtp_user": "",
    "smtp_password": "",
    "from_email": "",
    "from_name": "",
}

MASKED = "********"


def get_smtp_settings() -> dict:
    """Load SMTP settings from DB; env vars override DB values."""
    settings = dict(DEFAULT_SETTINGS)
    with get_db() as db:
        rows = db.execute("SELECT key, value FROM settings").fetchall()
        for row in rows:
            settings[row["key"]] = row["value"]
    for key in DEFAULT_SETTINGS:
        env_val = os.environ.get(f"NEWSLETTER_{key.upper()}")
        if env_val:
            settings[key] = env_val
    try:
        settings["smtp_port"] = int(settings.get("smtp_port") or 465)
    except (TypeError, ValueError):
        settings["smtp_port"] = 465
    return settings


def save_smtp_settings(data: dict) -> None:
    with get_db() as db:
        for key, value in (data or {}).items():
            if value is None:
                continue
            if key == "smtp_password" and value == MASKED:
                continue
            db.execute(
                "INSERT INTO settings (key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, str(value)),
            )
        db.commit()


def _build_message(settings: dict, to_email: str, to_name: str, subject: str, html: str) -> EmailMessage:
    msg = EmailMessage()
    msg["Subject"] = subject
    from_email = settings.get("from_email") or settings.get("smtp_user") or ""
    from_name = settings.get("from_name") or ""
    msg["From"] = formataddr((from_name, from_email))
    msg["To"] = formataddr((to_name, to_email)) if to_name else to_email
    msg["Message-ID"] = make_msgid()
    msg["Date"] = datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S +0000")
    msg.set_content(
        "Diese E-Mail enthält HTML-Inhalte. "
        "Bitte verwenden Sie einen E-Mail-Client mit HTML-Unterstützung."
    )
    msg.add_alternative(html, subtype="html")
    return msg


def _connect(settings: dict) -> smtplib.SMTP:
    host = settings["smtp_host"]
    port = int(settings["smtp_port"])
    security = (settings.get("smtp_security") or "ssl").lower()
    if not host:
        raise RuntimeError("SMTP-Host ist nicht konfiguriert")
    if security == "ssl":
        context = ssl.create_default_context()
        smtp = smtplib.SMTP_SSL(host, port, context=context, timeout=30)
    else:
        smtp = smtplib.SMTP(host, port, timeout=30)
        smtp.ehlo()
        if security == "starttls":
            smtp.starttls(context=ssl.create_default_context())
            smtp.ehlo()
    user = settings.get("smtp_user")
    password = settings.get("smtp_password")
    if user and password:
        smtp.login(user, password)
    return smtp


def send_test_mail(to_email: str, subject: str, html: str) -> None:
    settings = get_smtp_settings()
    if not settings.get("smtp_host") or not (settings.get("from_email") or settings.get("smtp_user")):
        raise RuntimeError("SMTP-Einstellungen unvollständig – bitte zuerst speichern.")
    msg = _build_message(settings, to_email, "", f"[TEST] {subject}", html)
    smtp = _connect(settings)
    try:
        smtp.send_message(msg)
    finally:
        try:
            smtp.quit()
        except Exception:
            pass


def _log(campaign_id: int, email: str, status: str, error: str | None) -> None:
    with get_db() as db:
        db.execute(
            "INSERT INTO campaign_logs (campaign_id, email, status, error, sent_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (campaign_id, email, status, error, datetime.utcnow().isoformat()),
        )
        db.commit()


def _update_counts(campaign_id: int, success: int, failed: int) -> None:
    with get_db() as db:
        db.execute(
            "UPDATE campaigns SET success = ?, failed = ? WHERE id = ?",
            (success, failed, campaign_id),
        )
        db.commit()


def send_campaign(campaign_id: int, newsletter: dict, recipients: list) -> None:
    """Background task: send newsletter to every recipient, log each attempt."""
    settings = get_smtp_settings()
    success = 0
    failed = 0

    try:
        smtp = _connect(settings)
    except Exception as exc:
        for rcpt in recipients:
            _log(campaign_id, rcpt["email"], "failed", f"SMTP-Verbindung fehlgeschlagen: {exc}")
        with get_db() as db:
            db.execute(
                "UPDATE campaigns SET status = ?, success = ?, failed = ?, finished_at = ? "
                "WHERE id = ?",
                ("failed", 0, len(recipients), datetime.utcnow().isoformat(), campaign_id),
            )
            db.commit()
        return

    try:
        for rcpt in recipients:
            email = rcpt["email"]
            name = rcpt.get("name") or ""
            try:
                personalized = personalize(
                    newsletter["blocks"], {"name": name, "email": email}
                )
                html = render_newsletter_html(
                    personalized,
                    newsletter.get("subject", ""),
                    newsletter.get("preheader", ""),
                )
                msg = _build_message(
                    settings, email, name, newsletter.get("subject", ""), html
                )
                try:
                    smtp.send_message(msg)
                except (smtplib.SMTPServerDisconnected, smtplib.SMTPConnectError):
                    try:
                        smtp.quit()
                    except Exception:
                        pass
                    smtp = _connect(settings)
                    smtp.send_message(msg)
                success += 1
                _log(campaign_id, email, "sent", None)
            except Exception as exc:  # noqa: BLE001
                failed += 1
                _log(campaign_id, email, "failed", str(exc))
            _update_counts(campaign_id, success, failed)
            # Throttle a bit to avoid tripping SMTP rate limits at all-inkl.
            time.sleep(0.2)
    finally:
        try:
            smtp.quit()
        except Exception:
            pass
        if failed == 0:
            status = "completed"
        elif success > 0:
            status = "partial"
        else:
            status = "failed"
        with get_db() as db:
            db.execute(
                "UPDATE campaigns SET status = ?, finished_at = ? WHERE id = ?",
                (status, datetime.utcnow().isoformat(), campaign_id),
            )
            db.commit()
