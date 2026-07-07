"""Donate — simple path: plain-language, pre-filtered view of the Directory.

One question up front (individual vs organization donor), then a filtered
card list. Compliance is stated as plain-English consequence, never a license
number, with a deep link into the Licenses page for anyone who wants the
detail. Data source: the same funding_sources rows the Directory renders.
"""

from __future__ import annotations

from html import escape

import streamlit as st

import data_cache
import layout as L

c = L.Ctx("donate")
licenses = data_cache.licenses()
sources = data_cache.funding_sources()

L.render_shell(c, "donate", simple=True)


def _intro() -> str:
    # GL 60 consequence in plain English, with the acronym glossed and a deep
    # link to the license card for the full detail.
    gl60_link = (
        f'<a href="{c.page_url("licenses", gl="GL 60", anchor="gl-60")}" '
        f'style="color:{L.BLUE};font-weight:700;text-decoration:none;">'
        f'{L.gloss(c, "GL", "GL 60")}</a>'
    )
    note = escape(c.t("don_gl60_note")).format(
        gl=gl60_link, date=escape(str(L.gl60_expiry(licenses)))
    )
    return (
        '<section style="padding:36px 48px 8px;">'
        '<h1 style="margin:0;font-size:32px;font-weight:800;letter-spacing:-0.01em;'
        f'color:{L.INK};">{escape(c.t("don_title"))}</h1>'
        f'<p style="margin:12px 0 14px;font-size:15px;color:{L.MUTE};max-width:640px;'
        f'line-height:1.6;">{escape(c.t("don_intro"))}</p>'
        '<div style="max-width:680px;background:#E7F4EC;border:1px solid #B7E0C6;'
        'border-radius:8px;padding:14px 18px;font-size:13.5px;color:#146C43;'
        f'line-height:1.6;">{note}</div></section>'
    )


def _entry_note(s: dict) -> str:
    """Compliance consequence line — only where the data raises one."""
    notes = []
    if "Government of Venezuela" in (s.get("funds_go_to") or ""):
        notes.append(
            '<div style="font-size:12.5px;color:#8A6100;background:#FBF3D9;'
            'border-radius:6px;padding:8px 12px;line-height:1.5;">'
            f'{escape(c.t("don_gov_note"))}</div>'
        )
    if "GL 60" in (s.get("suggested_license") or ""):
        notes.append(
            f'<div style="font-size:12.5px;"><a href="'
            f'{c.page_url("licenses", gl="GL 60", anchor="gl-60")}" '
            f'style="color:{L.BLUE};font-weight:700;text-decoration:none;">'
            f'{escape(c.t("don_license_link"))}</a></div>'
        )
    return "".join(notes)


L.render_body(_intro())

# The one up-front question: who is giving? (None = individual, "org" = org)
with st.container(key="simplefilters"):
    c.who = L.pills_filter(c, "who", "don_who_q", [
        (c.t("don_who_ind"), None),
        (c.t("don_who_org"), "org"),
    ])

shown = L.donate_entries(sources, c.who)
if shown:
    cards = "".join(L.simple_source_card(c, s, "don_how", _entry_note(s)) for s in shown)
    grid = f'<div style="display:flex;flex-wrap:wrap;gap:18px;">{cards}</div>'
else:
    grid = f'<p style="font-size:14px;color:{L.MUTE};">{escape(c.t("don_none"))}</p>'

L.render_body(
    '<section style="padding:10px 48px 64px;">'
    + grid
    + f'<p style="margin:18px 0 0;font-size:12.5px;color:#9CA3AF;">'
    f'{escape(c.t("don_count", count=len(shown)))}</p>'
    + L.simple_disclaimer_html(c)
    + "</section>"
)
L.render_footer(c)
