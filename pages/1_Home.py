"""Home — intent-first front door layered over the full navigator.

Order: masthead (Venezuela Resiliente + what it offers), GL 60 countdown
(shared urgency signal), two intent cards (donate -> Directory filtered to
giving flows, send money -> the GL 57 plain-language page), then the existing
expert Home content (hero, metrics, feature cards) below a #full-navigator
anchor so nothing is hidden from anyone who already knows what they want.
Org/lawyer users and volunteer-adjacent inquiries reach everything through
the "explore the full navigator" link below the cards. Old deep links
(?source= / ?pathway=) still redirect to the sub-page that now owns them.
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

# --- Live data for metrics + teasers (cached reads — see data_cache.py) ---
licenses = data_cache.licenses()
pathways = data_cache.verified_pathways()
funds = data_cache.public_funds()
sources = data_cache.funding_sources()

tracked_usd = sum(f.get("amount_usd") or 0 for f in funds)
active_licenses = sum(1 for lic in licenses if (lic.get("status") or "").lower() == "active")
gl60_exp = date.fromisoformat(config.GL60_EXPIRES)
gl60_days = max((gl60_exp - date.today()).days, 0)


def _welcome() -> str:
    """Masthead: names the initiative, then its two offerings side by side.

    The two items reuse the accent colors of the intent cards below (red =
    donate, blue = send money) so the masthead foreshadows the selector.
    """
    def item(head_key: str, body_key: str, accent: str) -> str:
        return (
            '<div style="flex:1 1 300px;max-width:460px;">'
            f'<div style="width:34px;height:4px;border-radius:2px;'
            f'background:{accent};margin-bottom:10px;"></div>'
            '<div style="font-size:12px;font-weight:700;letter-spacing:0.07em;'
            f'text-transform:uppercase;color:{L.INK};margin-bottom:6px;">'
            f'{escape(c.t(head_key))}</div>'
            f'<div style="font-size:14px;color:{L.MUTE};line-height:1.6;">'
            f'{escape(c.t(body_key))}</div></div>'
        )

    lead = c.t("home_welcome_lead", date=config.EARTHQUAKE_DATE_DISPLAY[c.lang])
    return (
        '<section style="padding:52px 48px 46px;">'
        '<div style="font-size:12px;font-weight:700;letter-spacing:0.08em;'
        f'text-transform:uppercase;color:{L.BLUE};">'
        f'{escape(c.t("home_welcome_eyebrow"))}</div>'
        '<h1 style="margin:10px 0 0;font-size:46px;font-weight:800;'
        f'letter-spacing:-0.02em;line-height:1.1;color:{L.INK};">'
        "Venezuela Resiliente</h1>"
        '<div style="width:72px;height:5px;border-radius:3px;margin:18px 0 20px;'
        f'background:linear-gradient(90deg,{L.YELLOW} 0 33%,{L.BLUE} 33% 66%,'
        f'{L.RED} 66% 100%);"></div>'
        f'<p style="margin:0 0 28px;font-size:16.5px;color:{L.MUTE};'
        f'max-width:700px;line-height:1.65;">{escape(lead)}</p>'
        '<div style="display:flex;gap:36px;flex-wrap:wrap;">'
        + item("home_welcome_a_h", "home_welcome_a", L.RED)
        + item("home_welcome_b_h", "home_welcome_b", L.BLUE)
        + "</div></section>"
    )


def _countdown_band() -> str:
    """GL 60 countdown — the shared urgency signal for every audience."""
    return (
        f'<section style="background:{L.INK};padding:26px 48px;display:flex;'
        'gap:24px;align-items:center;flex-wrap:wrap;">'
        f'<div style="font-size:44px;font-weight:800;color:{L.YELLOW};'
        f'line-height:1;">{gl60_days}</div>'
        '<div style="flex:1 1 320px;">'
        '<div style="font-size:13px;font-weight:700;letter-spacing:0.05em;'
        'text-transform:uppercase;color:rgba(255,255,255,0.85);">'
        f'{escape(c.t("m_gl60_days"))}</div>'
        '<div style="font-size:12.5px;color:rgba(255,255,255,0.6);margin-top:4px;'
        'max-width:560px;line-height:1.5;">'
        f'{escape(c.t("gl60_countdown_note", date=config.GL60_EXPIRES))}</div>'
        "</div></section>"
    )


def _intent_card(href: str, title: str, desc: str, accent: str) -> str:
    return (
        f'<a href="{href}" class="intent-card" style="text-decoration:none;'
        'flex:1 1 420px;max-width:520px;border:1px solid #E1DFD8;border-radius:10px;'
        'padding:26px 26px 22px;display:flex;flex-direction:column;gap:10px;'
        'background:#FFF;">'
        f'<div style="width:38px;height:5px;border-radius:3px;background:{accent};"></div>'
        f'<div style="font-size:21px;font-weight:800;color:{L.INK};line-height:1.25;">'
        f'{escape(title)}</div>'
        f'<div style="font-size:14px;color:{L.MUTE};line-height:1.55;flex:1;">'
        f'{escape(desc)}</div>'
        f'<div style="font-size:14px;font-weight:700;color:{L.BLUE};">→</div></a>'
    )


def _ngo_band() -> str:
    """NGO funding-seeking entry point — a slim banner, distinct from the two
    personal intent cards, landing on the Directory's confirmed-open view
    (fd=seek). That view stays empty until entries carry the human-set
    accepts_applications tag (see EDITING_GUIDE.md)."""
    return (
        f'<a href="{c.page_url("directory", fd="seek")}" class="intent-card" '
        'style="text-decoration:none;display:flex;align-items:center;gap:8px 18px;'
        'margin-top:20px;max-width:1060px;border:1px solid #E1DFD8;'
        'border-radius:10px;padding:18px 26px;background:#FBFAF7;flex-wrap:wrap;">'
        f'<div style="font-size:16px;font-weight:800;color:{L.INK};">'
        f'{escape(c.t("intent_ngo_t"))}</div>'
        f'<div style="font-size:13.5px;color:{L.MUTE};line-height:1.5;flex:1 1 320px;">'
        f'{escape(c.t("intent_ngo_d"))}</div>'
        f'<div style="font-size:14px;font-weight:700;color:{L.BLUE};">→</div></a>'
    )


def _intent_section() -> str:
    cards = (
        # Donate intent lands on the Directory pre-filtered to giving flows —
        # the Directory is the developed donation view; there is no separate
        # simplified donate page.
        _intent_card(c.page_url("directory", fd="give"), c.t("intent_donate_t"),
                     c.t("intent_donate_d"), L.RED)
        + _intent_card(c.page_url("remit"), c.t("intent_remit_t"),
                       c.t("intent_remit_d"), L.BLUE)
    )
    return (
        '<section style="padding:52px 48px 20px;">'
        '<h2 style="margin:0;font-size:34px;font-weight:800;letter-spacing:-0.01em;'
        f'color:{L.INK};">{escape(c.t("intent_heading"))}</h2>'
        f'<p style="margin:12px 0 28px;font-size:15.5px;color:{L.MUTE};max-width:620px;'
        f'line-height:1.6;">{escape(c.t("intent_sub"))}</p>'
        f'<div style="display:flex;gap:20px;flex-wrap:wrap;">{cards}</div>'
        + _ngo_band()
        + '<p style="margin:26px 0 0;font-size:13.5px;">'
        f'<a href="#full-navigator" style="color:{L.MUTE};font-weight:600;">'
        f'{escape(c.t("intent_full_link"))}</a></p></section>'
    )


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
    def stat(value: str, label: str, accent: str) -> str:
        return (
            '<div style="flex:1 1 200px;">'
            f'<div style="font-size:30px;font-weight:800;color:{accent};">{escape(value)}</div>'
            f'<div style="font-size:12px;font-weight:600;letter-spacing:0.04em;'
            f'text-transform:uppercase;color:rgba(255,255,255,0.6);margin-top:4px;">'
            f'{escape(label)}</div></div>'
        )
    return (
        f'<section style="background:{L.INK};padding:30px 48px;display:flex;gap:32px;'
        'flex-wrap:wrap;align-items:flex-start;">'
        + stat("≈" + L._fmt_usd(tracked_usd), c.t("m_tracked"), "#FFF")
        + stat(str(active_licenses), c.t("m_licenses"), "#FFF")
        + stat(str(len(pathways)), c.t("m_pathways"), "#FFF")
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


body = (
    _welcome()
    + _countdown_band()
    + _intent_section()
    # Full navigator (expert view) — everything the simple layer sits in
    # front of, reachable via the anchor link above.
    + '<div id="full-navigator" style="scroll-margin-top:70px;">'
    + _hero()
    + _metrics()
    + _feature_cards()
    + "</div>"
)
L.render_page(c, "home", body)
