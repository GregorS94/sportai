"""Seelenmut CMS – FastAPI entry point.

Provides:
- Public JSON API for a frontend to consume pages, posts, tags and media.
- Protected admin endpoints for CRUD on the same resources.
- A tiny HTML admin UI (static files served from ./static).
"""
from __future__ import annotations

import mimetypes
import os
import re
import secrets
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

import markdown as md
from dotenv import load_dotenv
from fastapi import (
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    Request,
    Response,
    UploadFile,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from auth import (
    COOKIE_NAME,
    make_session_token,
    optional_admin,
    require_admin,
    verify_credentials,
)
from database import get_db, init_db, row_to_dict

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
MEDIA_DIR = Path(os.environ.get("CMS_MEDIA_DIR", str(BASE_DIR / "data" / "media")))
MEDIA_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_IMAGE_MIMES = {
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
    "image/svg+xml",
}
MAX_UPLOAD_MB = 10

app = FastAPI(title="Seelenmut CMS", version="1.0.0")

# CORS so a separate frontend (e.g. Astro, Next, or a static site) can call us.
_cors_origins_env = os.environ.get("CMS_CORS_ORIGINS", "*")
if _cors_origins_env.strip() == "*":
    cors_origins = ["*"]
else:
    cors_origins = [o.strip() for o in _cors_origins_env.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()


# ---------- Static assets / admin UI ----------
@app.get("/", include_in_schema=False)
def root(request: Request):
    username = optional_admin(request)
    if username:
        return RedirectResponse("/admin", status_code=302)
    return RedirectResponse("/login", status_code=302)


@app.get("/login", include_in_schema=False)
def login_page():
    return FileResponse(STATIC_DIR / "login.html")


@app.get("/admin", include_in_schema=False)
def admin_page(request: Request):
    if not optional_admin(request):
        return RedirectResponse("/login", status_code=302)
    return FileResponse(STATIC_DIR / "admin.html")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/media", StaticFiles(directory=MEDIA_DIR), name="media")


# ---------- Helpers ----------
SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify(text: str) -> str:
    text = (text or "").strip().lower()
    replacements = {
        "ä": "ae",
        "ö": "oe",
        "ü": "ue",
        "ß": "ss",
    }
    for a, b in replacements.items():
        text = text.replace(a, b)
    text = SLUG_RE.sub("-", text).strip("-")
    return text or secrets.token_hex(4)


def now_iso() -> str:
    return datetime.utcnow().isoformat()


def render_markdown(text: str) -> str:
    return md.markdown(
        text or "",
        extensions=["extra", "sane_lists", "smarty", "toc"],
        output_format="html5",
    )


def _tags_for_post(db, post_id: int) -> list[dict]:
    rows = db.execute(
        "SELECT t.id, t.slug, t.name FROM tags t "
        "JOIN post_tags pt ON pt.tag_id = t.id WHERE pt.post_id = ? "
        "ORDER BY t.name",
        (post_id,),
    ).fetchall()
    return [row_to_dict(r) for r in rows]


def _set_post_tags(db, post_id: int, tag_names: list[str]) -> None:
    db.execute("DELETE FROM post_tags WHERE post_id = ?", (post_id,))
    seen = set()
    for raw in tag_names or []:
        name = (raw or "").strip()
        if not name:
            continue
        slug = slugify(name)
        if slug in seen:
            continue
        seen.add(slug)
        row = db.execute("SELECT id FROM tags WHERE slug = ?", (slug,)).fetchone()
        if row:
            tag_id = row["id"]
        else:
            cur = db.execute(
                "INSERT INTO tags (slug, name) VALUES (?, ?)", (slug, name)
            )
            tag_id = cur.lastrowid
        db.execute(
            "INSERT OR IGNORE INTO post_tags (post_id, tag_id) VALUES (?, ?)",
            (post_id, tag_id),
        )


def _ensure_unique_slug(db, table: str, slug: str, ignore_id: Optional[int] = None) -> str:
    base = slug
    n = 1
    while True:
        if ignore_id is not None:
            row = db.execute(
                f"SELECT id FROM {table} WHERE slug = ? AND id != ?",
                (slug, ignore_id),
            ).fetchone()
        else:
            row = db.execute(
                f"SELECT id FROM {table} WHERE slug = ?", (slug,)
            ).fetchone()
        if not row:
            return slug
        n += 1
        slug = f"{base}-{n}"


def _public_post(row: dict, tags: list[dict]) -> dict:
    return {
        "slug": row["slug"],
        "title": row["title"],
        "excerpt": row["excerpt"],
        "content": row["content"],
        "content_html": render_markdown(row["content"]),
        "cover_image": row["cover_image"],
        "published_at": row["published_at"],
        "tags": tags,
        "meta": {
            "title": row["meta_title"] or row["title"],
            "description": row["meta_description"] or row["excerpt"],
        },
    }


def _public_page(row: dict) -> dict:
    return {
        "slug": row["slug"],
        "title": row["title"],
        "content": row["content"],
        "content_html": render_markdown(row["content"]),
        "excerpt": row["excerpt"],
        "show_in_menu": bool(row["show_in_menu"]),
        "sort_order": row["sort_order"],
        "updated_at": row["updated_at"],
        "meta": {
            "title": row["meta_title"] or row["title"],
            "description": row["meta_description"] or row["excerpt"],
        },
    }


# ---------- Auth endpoints ----------
class LoginIn(BaseModel):
    username: str
    password: str


@app.post("/api/login")
def api_login(data: LoginIn, response: Response):
    if not verify_credentials(data.username, data.password):
        raise HTTPException(401, "Ungültige Zugangsdaten")
    token = make_session_token(data.username)
    response.set_cookie(
        COOKIE_NAME,
        token,
        max_age=12 * 3600,
        httponly=True,
        samesite="lax",
    )
    return {"ok": True, "user": data.username}


@app.post("/api/logout")
def api_logout(response: Response):
    response.delete_cookie(COOKIE_NAME)
    return {"ok": True}


@app.get("/api/me")
def api_me(request: Request):
    user = optional_admin(request)
    return {"user": user}


# ---------- Public API: pages ----------
@app.get("/api/pages")
def public_list_pages():
    with get_db() as db:
        rows = db.execute(
            "SELECT * FROM pages WHERE status = 'published' "
            "ORDER BY sort_order, title"
        ).fetchall()
        return [_public_page(row_to_dict(r)) for r in rows]


@app.get("/api/pages/{slug}")
def public_get_page(slug: str):
    with get_db() as db:
        row = db.execute(
            "SELECT * FROM pages WHERE slug = ? AND status = 'published'",
            (slug,),
        ).fetchone()
        if not row:
            raise HTTPException(404, "Seite nicht gefunden")
        return _public_page(row_to_dict(row))


# ---------- Public API: posts ----------
@app.get("/api/posts")
def public_list_posts(
    limit: int = 20,
    offset: int = 0,
    tag: Optional[str] = None,
):
    limit = max(1, min(limit, 100))
    offset = max(0, offset)
    with get_db() as db:
        params: list = []
        where = "WHERE p.status = 'published'"
        join = ""
        if tag:
            join = "JOIN post_tags pt ON pt.post_id = p.id JOIN tags t ON t.id = pt.tag_id"
            where += " AND t.slug = ?"
            params.append(tag)
        sql = (
            f"SELECT DISTINCT p.* FROM posts p {join} {where} "
            f"ORDER BY COALESCE(p.published_at, p.created_at) DESC "
            f"LIMIT ? OFFSET ?"
        )
        rows = db.execute(sql, (*params, limit, offset)).fetchall()
        result = []
        for r in rows:
            d = row_to_dict(r)
            result.append(_public_post(d, _tags_for_post(db, d["id"])))
        total_sql = (
            f"SELECT COUNT(DISTINCT p.id) as c FROM posts p {join} {where}"
        )
        total = db.execute(total_sql, params).fetchone()["c"]
        return {"items": result, "total": total, "limit": limit, "offset": offset}


@app.get("/api/posts/{slug}")
def public_get_post(slug: str):
    with get_db() as db:
        row = db.execute(
            "SELECT * FROM posts WHERE slug = ? AND status = 'published'",
            (slug,),
        ).fetchone()
        if not row:
            raise HTTPException(404, "Blogpost nicht gefunden")
        d = row_to_dict(row)
        return _public_post(d, _tags_for_post(db, d["id"]))


@app.get("/api/tags")
def public_list_tags():
    with get_db() as db:
        rows = db.execute(
            "SELECT t.id, t.slug, t.name, COUNT(pt.post_id) as count "
            "FROM tags t LEFT JOIN post_tags pt ON pt.tag_id = t.id "
            "LEFT JOIN posts p ON p.id = pt.post_id AND p.status = 'published' "
            "GROUP BY t.id HAVING count > 0 ORDER BY t.name"
        ).fetchall()
        return [row_to_dict(r) for r in rows]


# ---------- Admin models ----------
class PageIn(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    slug: str = ""
    content: str = ""
    excerpt: str = ""
    meta_title: str = ""
    meta_description: str = ""
    status: str = "draft"
    sort_order: int = 0
    show_in_menu: bool = True


class PostIn(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    slug: str = ""
    content: str = ""
    excerpt: str = ""
    cover_image: str = ""
    meta_title: str = ""
    meta_description: str = ""
    status: str = "draft"
    published_at: Optional[str] = None
    tags: list[str] = Field(default_factory=list)


class MediaUpdateIn(BaseModel):
    alt: str = ""


class PreviewIn(BaseModel):
    content: str = ""


# ---------- Admin: pages ----------
@app.get("/api/admin/pages")
def admin_list_pages(_: str = Depends(require_admin)):
    with get_db() as db:
        rows = db.execute("SELECT * FROM pages ORDER BY sort_order, title").fetchall()
        return [row_to_dict(r) for r in rows]


@app.get("/api/admin/pages/{pid}")
def admin_get_page(pid: int, _: str = Depends(require_admin)):
    with get_db() as db:
        row = db.execute("SELECT * FROM pages WHERE id = ?", (pid,)).fetchone()
        if not row:
            raise HTTPException(404)
        return row_to_dict(row)


@app.post("/api/admin/pages")
def admin_create_page(data: PageIn, _: str = Depends(require_admin)):
    now = now_iso()
    slug = slugify(data.slug or data.title)
    with get_db() as db:
        slug = _ensure_unique_slug(db, "pages", slug)
        cur = db.execute(
            "INSERT INTO pages (slug, title, content, excerpt, meta_title, "
            "meta_description, status, sort_order, show_in_menu, created_at, "
            "updated_at, published_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                slug,
                data.title,
                data.content,
                data.excerpt,
                data.meta_title,
                data.meta_description,
                data.status,
                data.sort_order,
                1 if data.show_in_menu else 0,
                now,
                now,
                now if data.status == "published" else None,
            ),
        )
        db.commit()
        return {"id": cur.lastrowid, "slug": slug}


@app.put("/api/admin/pages/{pid}")
def admin_update_page(pid: int, data: PageIn, _: str = Depends(require_admin)):
    now = now_iso()
    slug = slugify(data.slug or data.title)
    with get_db() as db:
        existing = db.execute("SELECT * FROM pages WHERE id = ?", (pid,)).fetchone()
        if not existing:
            raise HTTPException(404)
        slug = _ensure_unique_slug(db, "pages", slug, ignore_id=pid)
        published_at = existing["published_at"]
        if data.status == "published" and not published_at:
            published_at = now
        db.execute(
            "UPDATE pages SET slug = ?, title = ?, content = ?, excerpt = ?, "
            "meta_title = ?, meta_description = ?, status = ?, sort_order = ?, "
            "show_in_menu = ?, updated_at = ?, published_at = ? WHERE id = ?",
            (
                slug,
                data.title,
                data.content,
                data.excerpt,
                data.meta_title,
                data.meta_description,
                data.status,
                data.sort_order,
                1 if data.show_in_menu else 0,
                now,
                published_at,
                pid,
            ),
        )
        db.commit()
        return {"ok": True, "slug": slug}


@app.delete("/api/admin/pages/{pid}")
def admin_delete_page(pid: int, _: str = Depends(require_admin)):
    with get_db() as db:
        db.execute("DELETE FROM pages WHERE id = ?", (pid,))
        db.commit()
        return {"ok": True}


# ---------- Admin: posts ----------
@app.get("/api/admin/posts")
def admin_list_posts(_: str = Depends(require_admin)):
    with get_db() as db:
        rows = db.execute(
            "SELECT * FROM posts ORDER BY COALESCE(published_at, created_at) DESC"
        ).fetchall()
        result = []
        for r in rows:
            d = row_to_dict(r)
            d["tags"] = _tags_for_post(db, d["id"])
            result.append(d)
        return result


@app.get("/api/admin/posts/{pid}")
def admin_get_post(pid: int, _: str = Depends(require_admin)):
    with get_db() as db:
        row = db.execute("SELECT * FROM posts WHERE id = ?", (pid,)).fetchone()
        if not row:
            raise HTTPException(404)
        d = row_to_dict(row)
        d["tags"] = _tags_for_post(db, d["id"])
        return d


@app.post("/api/admin/posts")
def admin_create_post(data: PostIn, _: str = Depends(require_admin)):
    now = now_iso()
    slug = slugify(data.slug or data.title)
    published_at = data.published_at
    if data.status == "published" and not published_at:
        published_at = now
    with get_db() as db:
        slug = _ensure_unique_slug(db, "posts", slug)
        cur = db.execute(
            "INSERT INTO posts (slug, title, excerpt, content, cover_image, "
            "meta_title, meta_description, status, published_at, created_at, "
            "updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (
                slug,
                data.title,
                data.excerpt,
                data.content,
                data.cover_image,
                data.meta_title,
                data.meta_description,
                data.status,
                published_at,
                now,
                now,
            ),
        )
        post_id = cur.lastrowid
        _set_post_tags(db, post_id, data.tags)
        db.commit()
        return {"id": post_id, "slug": slug}


@app.put("/api/admin/posts/{pid}")
def admin_update_post(pid: int, data: PostIn, _: str = Depends(require_admin)):
    now = now_iso()
    slug = slugify(data.slug or data.title)
    with get_db() as db:
        existing = db.execute("SELECT * FROM posts WHERE id = ?", (pid,)).fetchone()
        if not existing:
            raise HTTPException(404)
        slug = _ensure_unique_slug(db, "posts", slug, ignore_id=pid)
        published_at = data.published_at or existing["published_at"]
        if data.status == "published" and not published_at:
            published_at = now
        db.execute(
            "UPDATE posts SET slug = ?, title = ?, excerpt = ?, content = ?, "
            "cover_image = ?, meta_title = ?, meta_description = ?, status = ?, "
            "published_at = ?, updated_at = ? WHERE id = ?",
            (
                slug,
                data.title,
                data.excerpt,
                data.content,
                data.cover_image,
                data.meta_title,
                data.meta_description,
                data.status,
                published_at,
                now,
                pid,
            ),
        )
        _set_post_tags(db, pid, data.tags)
        db.commit()
        return {"ok": True, "slug": slug}


@app.delete("/api/admin/posts/{pid}")
def admin_delete_post(pid: int, _: str = Depends(require_admin)):
    with get_db() as db:
        db.execute("DELETE FROM posts WHERE id = ?", (pid,))
        db.commit()
        return {"ok": True}


# ---------- Admin: media ----------
@app.get("/api/admin/media")
def admin_list_media(_: str = Depends(require_admin)):
    with get_db() as db:
        rows = db.execute(
            "SELECT * FROM media ORDER BY uploaded_at DESC"
        ).fetchall()
        result = []
        for r in rows:
            d = row_to_dict(r)
            d["url"] = f"/media/{d['filename']}"
            result.append(d)
        return result


@app.post("/api/admin/media")
async def admin_upload_media(
    file: UploadFile = File(...),
    alt: str = Form(""),
    _: str = Depends(require_admin),
):
    mime = file.content_type or mimetypes.guess_type(file.filename or "")[0] or ""
    if mime not in ALLOWED_IMAGE_MIMES:
        raise HTTPException(400, f"Nicht unterstützter Dateityp: {mime}")
    data = await file.read()
    if len(data) > MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(400, f"Datei ist zu groß (max. {MAX_UPLOAD_MB} MB)")
    original = Path(file.filename or "upload.bin").name
    stem = slugify(Path(original).stem) or "upload"
    ext = Path(original).suffix.lower() or mimetypes.guess_extension(mime) or ""
    safe = f"{stem}-{secrets.token_hex(4)}{ext}"
    dest = MEDIA_DIR / safe
    with open(dest, "wb") as fh:
        fh.write(data)
    with get_db() as db:
        db.execute(
            "INSERT INTO media (filename, original_name, mime_type, size, alt, uploaded_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (safe, original, mime, len(data), alt, now_iso()),
        )
        db.commit()
    return {"filename": safe, "url": f"/media/{safe}", "size": len(data)}


@app.put("/api/admin/media/{mid}")
def admin_update_media(
    mid: int, data: MediaUpdateIn, _: str = Depends(require_admin)
):
    with get_db() as db:
        res = db.execute(
            "UPDATE media SET alt = ? WHERE id = ?", (data.alt, mid)
        )
        db.commit()
        if res.rowcount == 0:
            raise HTTPException(404)
        return {"ok": True}


@app.delete("/api/admin/media/{mid}")
def admin_delete_media(mid: int, _: str = Depends(require_admin)):
    with get_db() as db:
        row = db.execute("SELECT * FROM media WHERE id = ?", (mid,)).fetchone()
        if not row:
            raise HTTPException(404)
        try:
            (MEDIA_DIR / row["filename"]).unlink(missing_ok=True)
        except Exception:
            pass
        db.execute("DELETE FROM media WHERE id = ?", (mid,))
        db.commit()
        return {"ok": True}


# ---------- Admin: utilities ----------
@app.post("/api/admin/preview")
def admin_preview(data: PreviewIn, _: str = Depends(require_admin)):
    return {"html": render_markdown(data.content)}


@app.get("/api/admin/stats")
def admin_stats(_: str = Depends(require_admin)):
    with get_db() as db:
        pages_total = db.execute("SELECT COUNT(*) AS c FROM pages").fetchone()["c"]
        pages_pub = db.execute(
            "SELECT COUNT(*) AS c FROM pages WHERE status='published'"
        ).fetchone()["c"]
        posts_total = db.execute("SELECT COUNT(*) AS c FROM posts").fetchone()["c"]
        posts_pub = db.execute(
            "SELECT COUNT(*) AS c FROM posts WHERE status='published'"
        ).fetchone()["c"]
        media_total = db.execute("SELECT COUNT(*) AS c FROM media").fetchone()["c"]
    return {
        "pages": {"total": pages_total, "published": pages_pub},
        "posts": {"total": posts_total, "published": posts_pub},
        "media": {"total": media_total},
    }
