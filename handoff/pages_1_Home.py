"""Home — redesigned landing page (2026-07 redesign).

Diaspora-first: hero with one clear promise + CTA, GL 60 countdown,
three equal intent cards (donate / send money / NGO funding), then a
compact expert navigator. Removes the old blue title banner and the
duplicated Donaciones/Transferencias blurbs in the welcome section.

Requires the new STRINGS keys listed in HANDOFF.md (add to layout.py).
"""

from __future__ import annotations

from datetime import date
from html import escape

import streamlit as st

import config
import data_cache
import layout as L

c = L.Ctx("home")

# --- Redirect legacy deep links to their new home ---
if c.source:
    st.query_params["source"] = c.source
    st.switch_page("pages/4_Directory.py")
if c.pathway:
    st.query_params["pathway"] = c.pathway
    st.switch_page("pages/3_Pathways.py")

# --- Live data ---
licenses = data_cache.licenses()
pathways = data_cache.verified_pathways()
funds = data_cache.public_funds()
sources = data_cache.funding_sources()

tracked_usd = sum(f.get("amount_usd") or 0 for f in funds)
active_licenses = sum(1 for lic in licenses if (lic.get("status") or "").lower() == "active")
gl60_exp = date.fromisoformat(config.GL60_EXPIRES)
gl60_days = max((gl60_exp - date.today()).days, 0)

GREEN = "#146C43"


def _hero() -> str:
    """Hero: eyebrow, one-promise headline, short lead, two CTAs, photo."""
    text_col = (
        '<div style="flex:1.3 1 440px;min-width:280px;">'
        '<div style="font-size:12px;font-weight:700;letter-spacing:0.08em;'
        f'text-transform:uppercase;color:{L.BLUE};">'
        f'{escape(c.t("home_welcome_eyebrow"))}</div>'
        '<h1 style="margin:10px 0 0;font-size:clamp(34px,6vw,50px);font-weight:800;'
        f'letter-spacing:-0.02em;line-height:1.08;color:{L.INK};">'
        f'{escape(c.t("home_hero_title"))}</h1>'
        '<div style="width:72px;height:5px;border-radius:3px;margin:20px 0 22px;'
        f'background:linear-gradient(90deg,{L.YELLOW} 0 33%,{L.BLUE} 33% 66%,'
        f'{L.RED} 66% 100%);"></div>'
        f'<p style="margin:0;font-size:17px;color:{L.MUTE};max-width:560px;'
        'line-height:1.65;">'
        f'{escape(c.t("home_hero_lead", date=config.EARTHQUAKE_DATE_DISPLAY[c.lang]))}</p>'
        '<div class="home-hero-ctas" style="display:flex;gap:12px;margin-top:28px;flex-wrap:wrap;">'
        f'<a href="#donar" style="text-decoration:none;background:{L.BLUE};color:#FFF;'
        'font-size:15px;font-weight:700;padding:13px 26px;border-radius:8px;">'
        f'{escape(c.t("home_cta_help"))}</a>'
        f'<a href="#full-navigator" style="text-decoration:none;border:1.5px solid #D8D5CC;'
        f'color:{L.INK};font-size:15px;font-weight:700;padding:13px 26px;border-radius:8px;">'
        f'{escape(c.t("home_cta_explore"))}</a></div></div>'
    )
    photo = (
        f'<img src="{L.photo_data_uri("welcome")}" '
        f'alt="{escape(c.t("photo_welcome_alt"))}" '
        'style="flex:1 1 340px;min-width:260px;max-width:520px;width:100%;'
        'max-height:400px;object-fit:cover;border-radius:10px;"/>'
    )
    return (
        '<section style="padding:56px var(--pad-x) 48px;display:flex;gap:44px;'
        f'flex-wrap:wrap;align-items:center;">{text_col}{photo}</section>'
    )


def _countdown_band() -> str:
    """GL 60 countdown, with a link through to the Licenses page."""
    return (
        f'<section style="background:{L.DARK_BLUE};padding:20px var(--pad-x);display:flex;'
        'gap:10px 26px;align-items:center;flex-wrap:wrap;">'
        f'<div style="font-size:40px;font-weight:800;color:{L.YELLOW};line-height:1;">'
        f'{gl60_days}</div>'
        '<div style="flex:1 1 320px;">'
        '<div style="font-size:13px;font-weight:700;letter-spacing:0.05em;'
        'text-transform:uppercase;color:#FFF;">'
        f'{escape(c.t("m_gl60_days"))}</div>'
        '<div style="font-size:12.5px;color:rgba(255,255,255,0.65);margin-top:3px;'
        'max-width:640px;line-height:1.5;">'
        f'{escape(c.t("gl60_countdown_short", date=L.fmt_date(config.GL60_EXPIRES, c.lang)))}</div>'
        "</div>"
        f'<a href="{c.page_url("licenses")}" style="text-decoration:none;font-size:13px;'
        f'font-weight:700;color:{L.YELLOW};white-space:nowrap;">'
        f'{escape(c.t("gl60_see_license"))}</a></section>'
    )


def _intent_card(href: str, title: str, desc: str, cta: str, accent: str) -> str:
    return (
        f'<a href="{href}" class="intent-card" style="text-decoration:none;background:#FFF;'
        'border:1px solid #E1DFD8;border-radius:10px;padding:28px 26px 24px;display:flex;'
        'flex-direction:column;gap:12px;">'
        f'<div style="width:38px;height:5px;border-radius:3px;background:{accent};"></div>'
        f'<div style="font-size:21px;font-weight:800;color:{L.INK};line-height:1.25;">'
        f'{escape(title)}</div>'
        f'<div style="font-size:14px;color:{L.MUTE};line-height:1.55;flex:1;">'
        f'{escape(desc)}</div>'
        f'<div style="font-size:14px;font-weight:700;color:{accent};">{escape(cta)}</div></a>'
    )


def _intent_section() -> str:
    """Three equal intent cards on a warm band — the page's main event."""
    cards = (
        _intent_card(c.page_url("directory", fd="give"), c.t("intent_donate_t"),
                     c.t("intent_donate_d"), c.t("intent_donate_cta"), L.RED)
        + _intent_card(c.page_url("remit"), c.t("intent_remit_t"),
                       c.t("intent_remit_d"), c.t("intent_remit_cta"), L.BLUE)
        + _intent_card(c.page_url("directory", fd="seek"), c.t("intent_ngo_t"),
                       c.t("intent_ngo_d"), c.t("intent_ngo_cta"), GREEN)
    )
    return (
        '<section id="donar" style="padding:56px var(--pad-x);background:#FBFAF7;'
        'scroll-margin-top:70px;">'
        '<h2 style="margin:0;font-size:clamp(26px,5vw,34px);font-weight:800;'
        f'letter-spacing:-0.01em;color:{L.INK};">{escape(c.t("intent_heading"))}</h2>'
        f'<p style="margin:10px 0 30px;font-size:15.5px;color:{L.MUTE};max-width:560px;'
        f'line-height:1.6;">{escape(c.t("intent_sub"))}</p>'
        '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));'
        f'gap:20px;max-width:1200px;">{cards}</div></section>'
    )


def _feature_card(slug: str, title: str, desc: str, teaser: str) -> str:
    return (
        f'<a href="{c.page_url(slug)}" style="text-decoration:none;border:1px solid #E1DFD8;'
        'border-radius:8px;padding:20px 22px;display:flex;flex-direction:column;gap:8px;'
        'background:#FFF;">'
        f'<div style="font-size:17px;font-weight:800;color:{L.BLUE};">{escape(title)}</div>'
        f'<div style="font-size:13px;color:{L.MUTE};line-height:1.5;flex:1;">{escape(desc)}</div>'
        f'<div style="font-size:12px;font-weight:700;color:{L.INK};border-top:1px solid '
        f'#F0EEE9;padding-top:9px;">{escape(teaser)}</div></a>'
    )


def _full_navigator() -> str:
    cards = (
        _feature_card("licenses", c.t("nav_licenses"), c.t("fc_licenses_desc"),
                      c.t("fc_licenses_teaser", n=active_licenses,
                          date=L.fmt_date(config.GL60_EXPIRES, c.lang)))
        + _feature_card("pathways", c.t("nav_pathways"), c.t("fc_pathways_desc"),
                        c.t("fc_pathways_teaser", n=len(pathways)))
        + _feature_card("directory", c.t("nav_directory"), c.t("fc_directory_desc"),
                        c.t("fc_directory_teaser", n=len(sources)))
        + _feature_card("capital", c.t("nav_capital"), c.t("fc_capital_desc"),
                        c.t("fc_capital_teaser", amount=L._fmt_usd(tracked_usd),
                            n=len(funds)))
    )
    return (
        '<section id="full-navigator" style="padding:56px var(--pad-x);'
        'scroll-margin-top:70px;">'
        '<div style="display:flex;align-items:baseline;gap:16px;flex-wrap:wrap;">'
        f'<h2 style="margin:0;font-size:22px;font-weight:800;letter-spacing:-0.01em;'
        f'color:{L.INK};">{escape(c.t("fullnav_heading"))}</h2>'
        f'<span style="font-size:13.5px;color:#9CA3AF;">{escape(c.t("fullnav_sub"))}</span>'
        "</div>"
        '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));'
        f'gap:16px;margin-top:24px;max-width:1200px;">{cards}</div></section>'
    )


body = _hero() + _countdown_band() + _intent_section() + _full_navigator()
L.render_page(c, "home", body)
