"""Directory — the 25 seeded funding sources with filters + source detail view."""

from __future__ import annotations

import streamlit as st

import layout as L
from database import fetch_funding_source, fetch_funding_sources, fetch_licenses, init_db

init_db()
c = L.Ctx("directory")
licenses = fetch_licenses()

# --- Source detail view ---
if c.source:
    src = fetch_funding_source(c.source)
    if src:
        L.render_page(c, "directory", L.breadcrumb(c) + L._source_detail(c, src, licenses))
        st.stop()

sources = fetch_funding_sources()
body = L.breadcrumb(c) + L._directory_section(c, sources)
L.render_page(c, "directory", body)
