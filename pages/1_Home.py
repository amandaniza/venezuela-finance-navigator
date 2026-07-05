"""Home — short intro: hero, live metrics strip, four feature cards, footer.

No data tables here. Each feature card links to its own sub-page and shows one
live teaser pulled from the DB. Old deep links (?source= / ?pathway=) are
redirected to the sub-page that now owns them.
"""

from __future__ import annotations

from datetime import date
from html import escape

import streamlit as st

import config
import layout as L
from database import (
    fetch_funding_sources,
    fetch_licenses,
    fetch_public_funds,
    fetch_verified_pathways,
    init_db,
)

init_db()
c = L.Ctx("home")

# --- Redirect legacy deep links to their new home ---
if c.source:
    st.query_params["source"] = c.source
    st.switch_page("pages/4_Directory.py")
if c.pathway:
    st.query_params["pathway"] = c.pathway
    st.switch_page("pages/3_Pathways.py")

# --- Live data for metrics + teasers ---
licenses = fetch_licenses()
pathways = fetch_verified_pathways()
funds = fetch_public_funds()
sources = fetch_funding_sources()

tracked_usd = sum(f.get("amount_usd") or 0 for f in funds)
active_licenses = sum(1 for lic in licenses if (lic.get("status") or "").lower() == "active")
gl60_exp = date.fromisoformat(config.GL60_EXPIRES)
gl60_days = max((gl60_exp - date.today()).days, 0)


def _hero() -> str:
    return (
        '<section style="position:relative;min-height:300px;display:flex;'
        'flex-direction:column;justify-content:center;background:linear-gradient('
        f'160deg,{L.DARK_BLUE} 0%,{L.BLUE} 45%,#0a3a8f 75%,{L.DARK_RED} 100%);'
        'overflow:hidden;padding:56px 48px;">'
        '<div style="position:absolute;inset:0;background-image:repeating-linear-gradient('
        '115deg,rgba(255,255,255,0.05) 0px,rgba(255,255,255,0.05) 2px,transparent 2px,'
        'transparent 26px);opacity:0.6;"></div>'
        '<div style="position:relative;max-width:820px;">'
        '<h1 style="margin:0;font-size:40px;font-weight:800;line-height:1.14;'
        'letter-spacing:-0.01em;color:#FFF;">'
        f'{escape(c.t("app_title"))}</h1>'
        '<p style="margin:18px 0 26px;max-width:640px;font-size:18px;line-height:1.55;'
        f'color:rgba(255,255,255,0.9);">{escape(c.t("home_value_prop"))}</p>'
        f'<a href="{c.page_url("pathways")}" style="text-decoration:none;background:'
        f'{L.YELLOW};color:{L.INK};padding:14px 28px;border-radius:999px;font-size:15px;'
        f'font-weight:700;display:inline-block;">{escape(c.t("home_cta"))}</a>'
        "</div></section>"
    )


def _metrics() -> str:
    def stat(value: str, label: str, accent: str, note: str = "") -> str:
        note_html = (
            f'<div style="font-size:11px;color:rgba(255,255,255,0.55);margin-top:6px;'
            f'max-width:230px;line-height:1.4;">{escape(note)}</div>' if note else ""
        )
        return (
            '<div style="flex:1 1 200px;">'
            f'<div style="font-size:30px;font-weight:800;color:{accent};">{escape(value)}</div>'
            f'<div style="font-size:12px;font-weight:600;letter-spacing:0.04em;'
            f'text-transform:uppercase;color:rgba(255,255,255,0.6);margin-top:4px;">'
            f'{escape(label)}</div>{note_html}</div>'
        )
    return (
        f'<section style="background:{L.INK};padding:30px 48px;display:flex;gap:32px;'
        'flex-wrap:wrap;align-items:flex-start;">'
        + stat("≈" + L._fmt_usd(tracked_usd), c.t("m_tracked"), "#FFF")
        + stat(str(active_licenses), c.t("m_licenses"), "#FFF")
        + stat(str(len(pathways)), c.t("m_pathways"), "#FFF")
        + stat(str(gl60_days), c.t("m_gl60_days"), L.YELLOW,
               c.t("gl60_countdown_note", date=config.GL60_EXPIRES))
        + "</section>"
    )


def _feature_card(slug: str, title: str, desc: str, teaser: str, accent: str) -> str:
    return (
        f'<a href="{c.page_url(slug)}" style="text-decoration:none;flex:1 1 240px;'
        'max-width:280px;border:1px solid #E1DFD8;border-radius:8px;padding:24px;'
        'display:flex;flex-direction:column;gap:10px;background:#FFF;">'
        f'<div style="width:34px;height:4px;border-radius:2px;background:{accent};"></div>'
        f'<div style="font-size:19px;font-weight:800;color:{L.BLUE};">{escape(title)}</div>'
        f'<div style="font-size:13.5px;color:{L.MUTE};line-height:1.5;flex:1;">{escape(desc)}</div>'
        f'<div style="font-size:12.5px;font-weight:700;color:{L.INK};border-top:1px solid '
        f'#F0EEE9;padding-top:10px;">{escape(teaser)}</div></a>'
    )


def _feature_cards() -> str:
    cards = (
        _feature_card(
            "licenses", c.t("nav_licenses"), c.t("fc_licenses_desc"),
            c.t("fc_licenses_teaser", n=active_licenses, date=config.GL60_EXPIRES),
            L.BLUE,
        )
        + _feature_card(
            "pathways", c.t("nav_pathways"), c.t("fc_pathways_desc"),
            c.t("fc_pathways_teaser", n=len(pathways)), "#146C43",
        )
        + _feature_card(
            "directory", c.t("nav_directory"), c.t("fc_directory_desc"),
            c.t("fc_directory_teaser", n=len(sources)), L.RED,
        )
        + _feature_card(
            "capital", c.t("nav_capital"), c.t("fc_capital_desc"),
            c.t("fc_capital_teaser", amount=L._fmt_usd(tracked_usd), n=len(funds)),
            L.YELLOW,
        )
    )
    return (
        '<section style="padding:48px;display:flex;gap:20px;flex-wrap:wrap;">'
        f"{cards}</section>"
    )


body = _hero() + _metrics() + _feature_cards()
L.render_page(c, "home", body)
