"""Licenses — OFAC General License cards from licenses_tb (full activity text)."""

from __future__ import annotations

from html import escape

import layout as L
from database import fetch_licenses, init_db

init_db()
c = L.Ctx("licenses")
licenses = fetch_licenses()


def _license_card(lic: dict) -> str:
    license_id = lic.get("license_id") or ""
    anchor = "gl-" + license_id.lower().replace(" ", "").replace("gl", "")
    status = (lic.get("status") or "").lower()
    expired = status in ("expired", "revoked")
    expiring = status == "expiring soon" or L._is_expiring_soon(lic.get("expiration_date"))
    if expired:
        tag, tag_col, swatch = c.t("lic_tag_expired"), "#9B1C1C", L.DARK_RED
    elif expiring:
        tag, tag_col, swatch = c.t("lic_tag_expiring"), "#8A6100", "#0a3a8f"
    else:
        tag, tag_col, swatch = c.t("lic_tag_active"), "#146C43", L.BLUE

    exp = L._parse_date(lic.get("expiration_date"))
    exp_line = (
        f'{c.t("lic_expires")} {exp.isoformat()}' if exp else c.t("lic_no_expiry")
    )
    activities = lic.get("activities") or []
    act_html = "".join(
        f'<li style="margin-bottom:4px;">{escape(a)}</li>' for a in activities
    ) or "<li>—</li>"

    # Highlight the card a cross-link targeted via ?gl=.
    highlighted = (c.gl or "").upper().replace(" ", "") == license_id.upper().replace(" ", "")
    border = f"2px solid {L.YELLOW}" if highlighted else "1px solid #E1DFD8"

    pathways_link = (
        f'<a href="{c.page_url("pathways", gl=license_id)}" '
        f'style="text-decoration:none;font-size:13px;font-weight:700;color:{L.BLUE};">'
        f'{escape(c.t("xl_license_pathways"))}</a>'
    )
    ofac_link = (
        f'<a href="{escape(L.OFAC_URL)}" '
        f'style="text-decoration:none;font-size:13px;font-weight:700;color:{L.INK};">'
        f'{escape(c.t("lic_official_source"))}</a>'
    )
    return (
        f'<div id="{anchor}" style="flex:1 1 380px;max-width:560px;border:{border};'
        'border-radius:8px;padding:24px;display:flex;gap:18px;scroll-margin-top:80px;">'
        f'<div style="width:88px;height:64px;flex:none;border-radius:6px;background:{swatch};'
        'display:flex;align-items:center;justify-content:center;font:800 20px/1 '
        f'\'Open Sans\';color:rgba(255,255,255,0.95);">{escape(license_id)}</div>'
        '<div style="flex:1;">'
        f'<div style="display:flex;gap:10px;align-items:center;">'
        f'<span style="font-size:11px;font-weight:700;letter-spacing:0.06em;color:{tag_col};">'
        f'{escape(tag)}</span>'
        f'<span style="font-size:12px;color:{L.MUTE};">· {escape(exp_line)}</span></div>'
        f'<div style="font-size:11px;font-weight:700;letter-spacing:0.06em;'
        f'text-transform:uppercase;color:#9CA3AF;margin:14px 0 6px;">'
        f'{escape(c.t("lic_activities"))}</div>'
        f'<ul style="margin:0;padding-left:18px;font-size:13.5px;color:{L.INK};'
        f'line-height:1.5;">{act_html}</ul>'
        '<div style="display:flex;gap:18px;flex-wrap:wrap;margin-top:16px;'
        'padding-top:14px;border-top:1px solid #F0EEE9;">'
        f'{pathways_link}{ofac_link}</div></div></div>'
    )


if licenses:
    cards = "".join(_license_card(lic) for lic in licenses)
    grid = f'<div style="display:flex;gap:20px;flex-wrap:wrap;">{cards}</div>'
else:
    grid = f'<p style="font-size:14px;color:{L.MUTE};">{escape(c.t("lic_none"))}</p>'

body = (
    L.breadcrumb(c)
    + '<section style="padding:24px 48px 64px;">'
    '<div style="font-size:30px;font-weight:800;letter-spacing:-0.01em;">'
    f'<span style="color:{L.RED};">OFAC</span> {escape(c.t("nav_licenses"))}</div>'
    f'<p style="margin:12px 0 28px;font-size:15px;color:{L.MUTE};max-width:640px;'
    f'line-height:1.6;">{escape(c.t("lic_page_intro"))}</p>'
    f'{grid}</section>'
)
L.render_page(c, "licenses", body)
