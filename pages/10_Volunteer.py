"""Volunteer — simple path: filtered Directory view of orgs that take people.

The thinnest path by design: organizations working on the response (INGOs,
diaspora orgs, community funds) with a "reach out" action per entry and no
compliance framing. Skill needs aren't in the dataset yet — entries link to
each org's own site/contact, and diaspora volunteer platforms (e.g.
SismoAyuda VE) slot in here once added to the seed data.
"""

from __future__ import annotations

from html import escape

import data_cache
import layout as L

c = L.Ctx("volunteer")
sources = data_cache.funding_sources()

shown = L.volunteer_entries(sources)
if shown:
    cards = "".join(L.simple_source_card(c, s, "vol_reach") for s in shown)
    grid = f'<div style="display:flex;flex-wrap:wrap;gap:18px;">{cards}</div>'
else:
    grid = f'<p style="font-size:14px;color:{L.MUTE};">{escape(c.t("vol_none"))}</p>'

body = (
    '<section style="padding:36px 48px 64px;">'
    '<h1 style="margin:0;font-size:32px;font-weight:800;letter-spacing:-0.01em;'
    f'color:{L.INK};">{escape(c.t("vol_title"))}</h1>'
    f'<p style="margin:12px 0 26px;font-size:15px;color:{L.MUTE};max-width:640px;'
    f'line-height:1.6;">{escape(c.t("vol_intro"))}</p>'
    + grid
    + f'<p style="margin:18px 0 0;font-size:12.5px;color:#9CA3AF;">'
    f'{escape(c.t("vol_count", count=len(shown)))}</p>'
    + L.simple_disclaimer_html(c)
    + "</section>"
)

L.render_page(c, "volunteer", body, simple=True)
