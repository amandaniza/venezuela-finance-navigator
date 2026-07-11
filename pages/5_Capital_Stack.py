"""Capital Stack — live FTS flows with an instant capital-type filter."""

from __future__ import annotations

from html import escape

import streamlit as st

import data_cache
import layout as L

c = L.Ctx("capital")
funds = data_cache.public_funds()
# Known directory source_keys so flows can cross-link where a match exists.
known = {s["source_key"] for s in data_cache.funding_sources()}

heading = (
    '<div style="font-size:clamp(24px,6vw,30px);font-weight:800;letter-spacing:-0.01em;">'
    f'<span style="color:{L.RED};">{escape(c.t("stack_kicker"))}</span> '
    f'{escape(c.t("stack_heading"))}</div>'
    f'<p style="margin:12px 0 0;font-size:15px;color:{L.MUTE};max-width:660px;'
    f'line-height:1.6;">{escape(c.t("cap_intro"))}</p>'
)

L.render_shell(c, "capital")
L.render_body(f'<section style="padding:24px var(--pad-x) 6px;">{heading}</section>')
with st.container(key="capfilters"):
    c.cap = L.pills_filter(
        c, "cap", "explore_capital", L.capital_filter_options(c, funds)
    )
L.render_body(L._capital_stack(c, funds, known))
L.render_footer(c)
