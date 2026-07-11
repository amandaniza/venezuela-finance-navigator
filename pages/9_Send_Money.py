"""Send money — simple path: GL 57 in plain language.

Not a directory view: this is the Licenses content (GL 57, financial services
involving Venezuelan banks) answered in the order a person actually asks —
can I, how, until when, what to avoid — with a deep link to the license card
and an explicit "not legal advice" close. Copy lives in layout.STRINGS; the
expiry line is driven by the GL 57 row in the DB when one exists.
"""

from __future__ import annotations

from html import escape

import data_cache
import layout as L

c = L.Ctx("remit")
licenses = data_cache.licenses()
gl57 = L.find_license(licenses, "GL 57")

GL57 = L.gloss(c, "GL", "GL 57")


def _block(heading: str, inner_html: str, lead: str = "") -> str:
    lead_html = (
        f'<div style="font-size:16px;font-weight:800;color:#146C43;'
        f'margin-bottom:6px;">{escape(lead)}</div>' if lead else ""
    )
    return (
        '<div style="margin-top:34px;max-width:680px;">'
        f'<h2 style="margin:0 0 10px;font-size:21px;font-weight:800;color:{L.INK};'
        f'letter-spacing:-0.01em;">{escape(heading)}</h2>'
        f"{lead_html}{inner_html}</div>"
    )


def _bullets(keys: list[str]) -> str:
    items = "".join(
        f'<li style="margin-bottom:8px;">{escape(c.t(k))}</li>' for k in keys
    )
    return (
        f'<ul style="margin:0;padding-left:20px;font-size:14.5px;color:{L.INK};'
        f'line-height:1.6;">{items}</ul>'
    )


def _para(html: str) -> str:
    return (
        f'<p style="margin:0;font-size:14.5px;color:{L.INK};line-height:1.65;">'
        f"{html}</p>"
    )


# (3) Expiration / risk window — driven by the GL 57 row when the DB has one.
gl57_exp = (gl57 or {}).get("expiration_date")
if gl57_exp:
    q3 = escape(c.t("rem_q3_exp")).format(gl=GL57, date=escape(L.fmt_date(gl57_exp, c.lang)))
else:
    q3 = escape(c.t("rem_q3_noexp")).format(gl=GL57)

license_link = (
    f'<p style="margin:30px 0 0;font-size:13.5px;">'
    f'<a href="{c.page_url("licenses", gl="GL 57", anchor="gl-57")}" '
    f'style="color:{L.BLUE};font-weight:700;text-decoration:none;">'
    f'{escape(c.t("rem_license_link"))}</a></p>'
)

body = (
    '<section style="padding:36px var(--pad-x) 64px;">'
    '<h1 style="margin:0;font-size:clamp(25px,6.5vw,32px);font-weight:800;letter-spacing:-0.01em;'
    f'color:{L.INK};">{escape(c.t("rem_title"))}</h1>'
    f'<p style="margin:12px 0 0;font-size:15px;color:{L.MUTE};max-width:640px;'
    f'line-height:1.6;">{escape(c.t("rem_intro"))}</p>'
    + _block(
        c.t("rem_q1_h"),
        _para(escape(c.t("rem_q1_body")).format(gl=GL57)),
        lead=c.t("rem_q1_a"),
    )
    + _block(
        c.t("rem_q2_h"),
        _bullets(["rem_q2_b1", "rem_q2_b2"])
        # Not-covered warning: most families bank privately, and GL 57 only
        # reaches the four named banks — this is the load-bearing caveat.
        + '<div style="margin-top:12px;background:#FBF3D9;border:1px solid '
        '#F0DFA8;border-radius:6px;padding:10px 14px;font-size:13.5px;'
        f'color:#8A6100;line-height:1.55;">{escape(c.t("rem_q2_note"))}</div>',
    )
    + _block(c.t("rem_q3_h"), _para(q3))
    + _block(c.t("rem_q4_h"), _bullets(["rem_q4_b1", "rem_q4_b2", "rem_q4_b3"]))
    + license_link
    + L.simple_disclaimer_html(c)
    + "</section>"
)

L.render_page(c, "remit", body)
