"""Render block-based newsletter JSON to table-based HTML email."""
import html as _html
from copy import deepcopy
from typing import Iterable

EMAIL_BG = "#f4f5f7"
CONTAINER_BG = "#ffffff"
CONTAINER_WIDTH = 600


def _esc(text) -> str:
    if text is None:
        return ""
    return _html.escape(str(text))


def _attr(value: str) -> str:
    return _html.escape(str(value), quote=True)


def _render_block(block: dict) -> str:
    btype = block.get("type")
    props = block.get("props") or {}
    align = props.get("align", "left")

    if btype == "heading":
        level = props.get("level", "h2")
        color = props.get("color", "#111111")
        size = {"h1": "32px", "h2": "24px", "h3": "20px"}.get(level, "24px")
        text = _esc(props.get("text", ""))
        return (
            f'<tr><td align="{align}" style="padding:16px 24px 8px 24px;'
            f'font-family:Arial,Helvetica,sans-serif;font-size:{size};'
            f'font-weight:bold;color:{color};line-height:1.25;">{text}</td></tr>'
        )

    if btype == "text":
        color = props.get("color", "#333333")
        size = props.get("size", "16px")
        raw_html = props.get("html")
        if raw_html:
            body = raw_html  # editor-provided sanitized HTML
        else:
            body = _esc(props.get("text", "")).replace("\n", "<br />")
        return (
            f'<tr><td align="{align}" style="padding:8px 24px;'
            f'font-family:Arial,Helvetica,sans-serif;font-size:{size};'
            f'color:{color};line-height:1.6;">{body}</td></tr>'
        )

    if btype == "image":
        src = props.get("src", "")
        alt = _esc(props.get("alt", ""))
        try:
            width = int(props.get("width", CONTAINER_WIDTH - 48))
        except (TypeError, ValueError):
            width = CONTAINER_WIDTH - 48
        link = props.get("link", "")
        if not src:
            return (
                f'<tr><td align="{align}" style="padding:16px 24px;'
                f'font-family:Arial,Helvetica,sans-serif;color:#9ca3af;'
                f'font-size:14px;font-style:italic;">[Bild: keine URL gesetzt]</td></tr>'
            )
        img_html = (
            f'<img src="{_attr(src)}" alt="{alt}" width="{width}" '
            f'style="display:block;border:0;outline:none;text-decoration:none;'
            f'max-width:100%;height:auto;" />'
        )
        if link:
            img_html = f'<a href="{_attr(link)}" target="_blank" rel="noopener">{img_html}</a>'
        return f'<tr><td align="{align}" style="padding:16px 24px;">{img_html}</td></tr>'

    if btype == "button":
        text = _esc(props.get("text", "Mehr erfahren"))
        url = _attr(props.get("url", "#"))
        bg = props.get("bg_color", "#2563eb")
        fg = props.get("text_color", "#ffffff")
        return (
            f'<tr><td align="{align}" style="padding:16px 24px;">'
            f'<table role="presentation" cellspacing="0" cellpadding="0" border="0">'
            f'<tr><td bgcolor="{bg}" style="border-radius:6px;">'
            f'<a href="{url}" target="_blank" rel="noopener" '
            f'style="display:inline-block;padding:12px 24px;'
            f'font-family:Arial,Helvetica,sans-serif;font-size:16px;'
            f'font-weight:bold;color:{fg};text-decoration:none;border-radius:6px;">{text}</a>'
            f'</td></tr></table></td></tr>'
        )

    if btype == "divider":
        color = props.get("color", "#e5e7eb")
        return (
            f'<tr><td style="padding:12px 24px;">'
            f'<div style="height:1px;background-color:{color};'
            f'line-height:1px;font-size:0;">&nbsp;</div></td></tr>'
        )

    if btype == "spacer":
        try:
            height = int(props.get("height", 24))
        except (TypeError, ValueError):
            height = 24
        return (
            f'<tr><td style="line-height:1px;font-size:1px;'
            f'height:{height}px;">&nbsp;</td></tr>'
        )

    return ""


def render_newsletter_html(blocks: Iterable[dict], subject: str = "", preheader: str = "") -> str:
    body = "".join(_render_block(b) for b in (blocks or []))
    pre_hidden = ""
    if preheader:
        pre_hidden = (
            f'<div style="display:none;font-size:1px;color:{EMAIL_BG};'
            f'line-height:1px;max-height:0;max-width:0;opacity:0;overflow:hidden;">'
            f'{_esc(preheader)}</div>'
        )
    return (
        '<!DOCTYPE html>\n'
        '<html lang="de">\n'
        '<head>\n'
        '<meta charset="UTF-8" />\n'
        '<meta name="viewport" content="width=device-width,initial-scale=1" />\n'
        '<meta http-equiv="X-UA-Compatible" content="IE=edge" />\n'
        f'<title>{_esc(subject)}</title>\n'
        '</head>\n'
        f'<body style="margin:0;padding:0;background-color:{EMAIL_BG};'
        'font-family:Arial,Helvetica,sans-serif;">\n'
        f'{pre_hidden}\n'
        '<table role="presentation" width="100%" cellspacing="0" cellpadding="0" '
        f'border="0" style="background-color:{EMAIL_BG};">\n'
        '  <tr><td align="center" style="padding:24px 12px;">\n'
        f'    <table role="presentation" width="{CONTAINER_WIDTH}" cellspacing="0" '
        'cellpadding="0" border="0" '
        f'style="background-color:{CONTAINER_BG};max-width:{CONTAINER_WIDTH}px;'
        'border-radius:8px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,0.04);">\n'
        f'      {body}\n'
        '    </table>\n'
        '  </td></tr>\n'
        '</table>\n'
        '</body>\n'
        '</html>\n'
    )


def personalize(blocks: list, ctx: dict) -> list:
    """Replace {{placeholder}} tokens inside block text/html props."""
    result = deepcopy(blocks or [])
    for block in result:
        props = block.get("props") or {}
        for key in ("text", "html", "alt"):
            val = props.get(key)
            if isinstance(val, str):
                for k, v in (ctx or {}).items():
                    val = val.replace("{{" + k + "}}", "" if v is None else str(v))
                props[key] = val
        block["props"] = props
    return result
