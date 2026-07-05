"""Pathways — verified compliance verdicts + fund/pathway detail view.

Verified pathways ONLY (the credibility gate). Optional ?gl= filter narrows to
one license; ?pathway= opens a single verified pathway's detail.
"""

from __future__ import annotations

from html import escape

import streamlit as st

import layout as L
from database import fetch_licenses, fetch_pathway, fetch_verified_pathways, init_db

init_db()
c = L.Ctx("pathways")
licenses = fetch_licenses()

# --- Detail view (verified pathways only — never leak an unverified verdict) ---
if c.pathway:
    try:
        pw = fetch_pathway(int(c.pathway))
    except (TypeError, ValueError):
        pw = None
    if pw and pw.get("human_verified"):
        L.render_page(c, "pathways", L.breadcrumb(c) + L._pathway_detail(c, pw, licenses))
        st.stop()

pathways = fetch_verified_pathways()

# --- Optional license filter ---
filter_note = ""
if c.gl:
    pathways = [p for p in pathways if (p.get("license_id") or "") == c.gl]
    filter_note = (
        f'<p style="margin:0 0 18px;font-size:13px;color:{L.INK};">'
        f'<b>{escape(c.t("pw_filtered_to", gl=c.gl))}</b> · '
        f'<a href="{c.href(gl=None)}" style="color:{L.BLUE};font-weight:700;'
        f'text-decoration:none;">{escape(c.t("pw_clear_filter"))}</a></p>'
    )

heading = (
    '<div style="font-size:30px;font-weight:800;letter-spacing:-0.01em;">'
    f'<span style="color:{L.RED};">{escape(c.t("pathways_kicker"))}</span> '
    f'{escape(c.t("pathways_heading"))}</div>'
    f'<p style="margin:12px 0 24px;font-size:15px;color:{L.MUTE};max-width:660px;'
    f'line-height:1.6;">{escape(c.t("pw_intro"))}</p>'
)

if pathways:
    inner = (
        L._feature_cards(c, pathways)
        + filter_note
        + f'<p style="margin:0 0 18px;font-size:13px;color:{L.MUTE};max-width:640px;'
        f'line-height:1.5;">{escape(c.t("pathways_note"))}</p>'
        + L._pathways_table(c, pathways)
        + f'<p style="margin:14px 0 0;font-size:12.5px;color:#9CA3AF;">'
        f'{escape(c.t("rows_shown", count=len(pathways)))}</p>'
    )
else:
    inner = (
        filter_note
        + f'<p style="font-size:14px;color:{L.MUTE};">{escape(c.t("pathways_empty"))}</p>'
    )

body = (
    L.breadcrumb(c)
    + f'<section id="pathways" style="padding:24px 48px 64px;">{heading}{inner}</section>'
)
L.render_page(c, "pathways", body)
