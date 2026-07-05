"""Directory — researched funding sources with instant filters + detail view.

Filters are st.pills widgets synced to query params: clicking reruns over the
websocket (no browser reload) while the URL stays shareable.
"""

from __future__ import annotations

import streamlit as st

import data_cache
import layout as L

c = L.Ctx("directory")
licenses = data_cache.licenses()

# --- Source detail view ---
if c.source:
    src = data_cache.funding_source(c.source)
    if src:
        L.render_page(c, "directory", L._source_detail(c, src, licenses))
        st.stop()

sources = data_cache.funding_sources()

L.render_shell(c, "directory")
L.render_body(L._directory_intro(c, len(sources)))
with st.container(key="dirfilters"):
    for param, (label_key, options) in L.directory_filter_defs(c).items():
        setattr(c, param, L.pills_filter(c, param, label_key, options))
shown = L.apply_directory_filters(c, sources)
L.render_body(L._directory_grid(c, sources, shown))
L.render_footer(c)
