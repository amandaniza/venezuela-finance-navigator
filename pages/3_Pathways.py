"""Pathways — verified compliance verdicts + fund/pathway detail view.

Verified pathways ONLY (the credibility gate). Optional ?gl= filter narrows to
one license (cleared by a widget button — no page reload); ?pathway= opens a
single verified pathway's detail.
"""

from __future__ import annotations

from html import escape

import streamlit as st

import data_cache
import layout as L

c = L.Ctx("pathways")
licenses = data_cache.licenses()

# --- Detail view (verified pathways only — never leak an unverified verdict) ---
if c.pathway:
    try:
        pw = data_cache.pathway(int(c.pathway))
    except (TypeError, ValueError):
        pw = None
    if pw and pw.get("human_verified"):
        L.render_page(c, "pathways", L._pathway_detail(c, pw, licenses))
        st.stop()

pathways = data_cache.verified_pathways()

heading = (
    '<div style="font-size:clamp(24px,6vw,30px);font-weight:800;letter-spacing:-0.01em;">'
    f'<span style="color:{L.RED};">{escape(c.t("pathways_kicker"))}</span> '
    f'{escape(c.t("pathways_heading"))}</div>'
    f'<p style="margin:12px 0 12px;font-size:15px;color:{L.MUTE};max-width:660px;'
    f'line-height:1.6;">{escape(c.t("pw_intro"))}</p>'
)

L.render_shell(c, "pathways")
L.render_body(f'<section id="pathways" style="padding:24px var(--pad-x) 0;">{heading}</section>')

# --- Optional license filter (clear via widget — websocket rerun, no reload) ---
if c.gl:
    with st.container(key="pwfilter"):
        label = f'{c.t("pw_filtered_to", gl=c.gl)} · {c.t("pw_clear_filter")} ✕'
        if st.button(label, key="pw_clear"):
            st.query_params.pop("gl", None)
            c.gl = None
            st.rerun()
if c.gl:
    pathways = [p for p in pathways if (p.get("license_id") or "") == c.gl]

if pathways:
    inner = (
        L._feature_cards(c, pathways)
        + f'<p style="margin:0 0 18px;font-size:13px;color:{L.MUTE};max-width:640px;'
        f'line-height:1.5;">{escape(c.t("pathways_note"))}</p>'
        + L._pathways_table(c, pathways)
        + f'<p style="margin:14px 0 0;font-size:12.5px;color:#9CA3AF;">'
        f'{escape(c.t("rows_shown", count=len(pathways)))}</p>'
    )
else:
    inner = f'<p style="font-size:14px;color:{L.MUTE};">{escape(c.t("pathways_empty"))}</p>'

L.render_body(f'<section style="padding:8px var(--pad-x) 64px;">{inner}</section>')
L.render_footer(c)
