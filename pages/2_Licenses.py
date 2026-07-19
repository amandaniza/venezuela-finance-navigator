"""Licenses — OFAC General License cards from licenses_tb (full activity text)."""

from __future__ import annotations

from html import escape

import data_cache
import layout as L

c = L.Ctx("licenses")
licenses = data_cache.licenses()


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
        f'{c.t("lic_expires")} {L.fmt_date(exp, c.lang)}' if exp else c.t("lic_no_expiry")
    )
    activities = lic.get("activities") or []
    act_html = "".join(
        f'<li style="margin-bottom:4px;">{escape(L._localize_activity(a, c.lang))}</li>'
        for a in activities
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
        f'<a href="{escape(L.OFAC_URL)}" {L.EXT} '
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


def _nonus_note() -> str:
    """Plain-language callout: what these U.S. licenses mean for donors who
    are reading from outside the United States (item 1 of the 2026-07 edits)."""
    return (
        '<div style="margin:0 0 30px;max-width:720px;border:1px solid #D8E3F5;'
        f'border-left:4px solid {L.BLUE};border-radius:8px;background:#F5F8FE;'
        'padding:18px 22px;">'
        f'<div style="font-size:14px;font-weight:800;color:{L.BLUE};'
        f'margin-bottom:8px;">🌍 {escape(c.t("lic_nonus_h"))}</div>'
        f'<div style="font-size:13.5px;color:{L.INK};line-height:1.65;">'
        f'{escape(c.t("lic_nonus_body"))}</div></div>'
    )


if licenses:
    cards = "".join(_license_card(lic) for lic in licenses)
    grid = f'<div style="display:flex;gap:20px;flex-wrap:wrap;">{cards}</div>'
else:
    grid = f'<p style="font-size:14px;color:{L.MUTE};">{escape(c.t("lic_none"))}</p>'

body = (
    '<section style="padding:24px var(--pad-x) 64px;">'
    '<div style="font-size:clamp(24px,6vw,30px);font-weight:800;letter-spacing:-0.01em;">'
    f'<span style="color:{L.RED};">OFAC</span> {escape(c.t("nav_licenses"))}</div>'
    f'<p style="margin:12px 0 22px;font-size:15px;color:{L.MUTE};max-width:640px;'
    f'line-height:1.6;">{escape(c.t("lic_page_intro"))}</p>'
    f'{_nonus_note()}'
    f'{grid}</section>'
)
L.render_page(c, "licenses", body)
