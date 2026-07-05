"""Capital Stack — live FTS flows with capital-type filter pills."""

from __future__ import annotations

from html import escape

import layout as L
from database import fetch_funding_sources, fetch_public_funds, init_db

init_db()
c = L.Ctx("capital")
funds = fetch_public_funds()
# Known directory source_keys so flows can cross-link where a match exists.
known = {s["source_key"] for s in fetch_funding_sources()}

heading = (
    '<div style="font-size:30px;font-weight:800;letter-spacing:-0.01em;">'
    f'<span style="color:{L.RED};">{escape(c.t("stack_kicker"))}</span> '
    f'{escape(c.t("stack_heading"))}</div>'
    f'<p style="margin:12px 0 0;font-size:15px;color:{L.MUTE};max-width:660px;'
    f'line-height:1.6;">{escape(c.t("cap_intro"))}</p>'
)

body = (
    L.breadcrumb(c)
    + f'<section style="padding:24px 48px 0;">{heading}</section>'
    + L._capital_stack(c, funds, known)
)
L.render_page(c, "capital", body)
