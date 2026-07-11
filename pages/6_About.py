"""About — methodology, what "verified" means, disclaimer, sources, cadence."""

from __future__ import annotations

from html import escape

import config
import layout as L
from database import init_db

init_db()
c = L.Ctx("about")


def _disclaimer_block() -> str:
    """Site-level disclaimer — same credibility-protection treatment as the
    yellow "under review" labeling on directory entries, at site level."""
    return (
        '<div style="max-width:720px;margin-top:36px;background:#FBF3D9;'
        'border:1px solid #F0DFA8;border-radius:8px;padding:20px 24px;">'
        '<div style="font-size:15px;font-weight:800;color:#8A6100;'
        f'margin-bottom:8px;">{escape(c.t("about_disclaimer_h"))}</div>'
        '<div style="font-size:13.5px;color:#8A6100;line-height:1.65;">'
        f'{escape(c.t("about_disclaimer_body"))}</div></div>'
    )


def _block(title: str, body_html: str, accent: str = L.BLUE) -> str:
    return (
        '<div style="margin-bottom:28px;max-width:720px;">'
        f'<div style="width:34px;height:4px;border-radius:2px;background:{accent};'
        'margin-bottom:12px;"></div>'
        f'<div style="font-size:19px;font-weight:800;color:{L.INK};margin-bottom:8px;">'
        f'{escape(title)}</div>'
        f'<div style="font-size:14.5px;color:{L.MUTE};line-height:1.65;">{body_html}</div></div>'
    )


ofac_link = (
    f'<a href="{escape(L.OFAC_URL)}" {L.EXT} '
    f'style="color:{L.BLUE};font-weight:600;">OFAC Recent Actions ↗</a>'
)
fts_link = (
    f'<a href="{escape(L.FTS_URL)}" {L.EXT} '
    f'style="color:{L.BLUE};font-weight:600;">UNOCHA FTS ↗</a>'
)
mail_link = (
    f'<a href="{L._mailto("report")}" style="color:{L.BLUE};font-weight:700;">'
    f'{escape(config.CONTACT_EMAIL)}</a>'
)

blocks = (
    _block(c.t("about_verified_h"), escape(c.t("about_verified_body")), "#146C43")
    + _block(c.t("about_notverified_h"), escape(c.t("about_notverified_body")), L.RED)
    + _block(
        c.t("about_sources_h"),
        escape(c.t("about_sources_body")) + f'<br><br>{ofac_link} · {fts_link}',
        L.YELLOW,
    )
    + _block(
        c.t("about_cadence_h"),
        escape(c.t("about_cadence_body", date=L.fmt_date(config.FUNDING_LAST_CHECKED, c.lang),
                   ocha=L.fmt_date(config.OCHA_REVISED_PLAN_DATE, c.lang))),
    )
    + _block(c.t("about_contact_h"), escape(c.t("about_contact_body")) + " " + mail_link)
    + _disclaimer_block()
)

body = (
    '<section style="padding:24px var(--pad-x) 64px;">'
    '<div style="font-size:clamp(24px,6vw,30px);font-weight:800;letter-spacing:-0.01em;margin-bottom:12px;">'
    f'{escape(c.t("nav_about"))}</div>'
    f'<p style="margin:0 0 32px;font-size:16px;color:{L.MUTE};max-width:720px;'
    f'line-height:1.6;">{escape(c.t("about_intro"))}</p>'
    f'{blocks}</section>'
)
L.render_page(c, "about", body)
