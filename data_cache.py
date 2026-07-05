"""
Cached read layer between the Streamlit UI and sqlite.

Every page rerun used to hit sqlite directly (and re-run the schema DDL via
init_db). These wrappers memoize the hot queries with st.cache_data so reruns
triggered by widgets/navigation render from memory. TTL keeps pipeline updates
flowing through within a few minutes; the Admin page calls clear() after
saving verdicts so its edits show up immediately.

UI code (layout.py, pages/) imports from here; pipeline/CLI code keeps using
database.py directly, so nothing outside Streamlit touches st.cache_data.
"""

from __future__ import annotations

from typing import Any

import streamlit as st

import database as db

_TTL = 300  # seconds


@st.cache_data(ttl=_TTL, show_spinner=False)
def licenses() -> list[dict[str, Any]]:
    return db.fetch_licenses()


@st.cache_data(ttl=_TTL, show_spinner=False)
def verified_pathways() -> list[dict[str, Any]]:
    return db.fetch_verified_pathways()


@st.cache_data(ttl=_TTL, show_spinner=False)
def pathway(map_id: int) -> dict[str, Any] | None:
    return db.fetch_pathway(map_id)


@st.cache_data(ttl=_TTL, show_spinner=False)
def public_funds() -> list[dict[str, Any]]:
    return db.fetch_public_funds()


@st.cache_data(ttl=_TTL, show_spinner=False)
def funding_sources() -> list[dict[str, Any]]:
    return db.fetch_funding_sources()


@st.cache_data(ttl=_TTL, show_spinner=False)
def funding_source(source_key: str) -> dict[str, Any] | None:
    return db.fetch_funding_source(source_key)


def clear() -> None:
    """Drop all cached reads (call after any admin write)."""
    st.cache_data.clear()
