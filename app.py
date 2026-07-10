"""
Venezuela Reconstruction Finance Navigator — multipage entrypoint.

Home is a short intro; each feature lives on its own sub-page. Navigation is
custom (the flag-themed header in layout.py), so Streamlit's sidebar nav is
hidden. Language is a ?lang= query param carried through every internal link.
Admin is secret-gated behind ?auth=admin.

Usage:
    streamlit run app.py
    # Admin: append ?auth=admin to any URL
"""

from __future__ import annotations

import streamlit as st

from database import init_db
from layout import DEFAULT_LANG, SUPPORTED_LANGS

ADMIN_TOKEN = "admin"

st.set_page_config(
    page_title="Venezuela Resiliente",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="collapsed",
)

init_db()


@st.cache_resource
def _bootstrap_data() -> None:
    """First-boot seeding for fresh deploys.

    data/navigator.db is not committed to git, so a brand-new host (e.g.
    Streamlit Community Cloud) starts empty. Populate the directory from
    navigator_funding_seed.json, the demo licenses/pathways, and (best-effort)
    live FTS flows. All upserts — a no-op on an already-populated database.
    """
    from database import get_connection

    with get_connection() as conn:
        n_dir = conn.execute("SELECT COUNT(*) FROM funding_sources").fetchone()[0]
        n_lic = conn.execute("SELECT COUNT(*) FROM licenses_tb").fetchone()[0]
        n_funds = conn.execute("SELECT COUNT(*) FROM funds_tb").fetchone()[0]
    if not n_dir:
        from scripts.import_funding_seed import import_seed

        import_seed()
    if not n_lic:
        from scripts.seed_demo import seed

        seed()
    if n_funds < 5:  # only demo rows present — try the public FTS API
        try:
            from pipeline.ingest_fts import ingest_fts

            ingest_fts()
        except Exception:
            pass  # capital stack fills on the next pipeline run


_bootstrap_data()


def _query_value(key: str) -> str | None:
    value = st.query_params.get(key)
    if isinstance(value, list):
        value = value[0] if value else None
    return value


# Language is driven by ?lang= so the header ES/EN toggle works everywhere.
_lang = _query_value("lang")
if _lang in SUPPORTED_LANGS:
    st.session_state.lang = _lang
elif "lang" not in st.session_state:
    st.session_state.lang = DEFAULT_LANG


# Persist the admin session like the language: st.page_link navigation is
# client-side and drops query params, so ?auth=admin must survive in state.
_auth = _query_value("auth")
if _auth:
    st.session_state.auth = _auth


def _is_admin() -> bool:
    return ADMIN_TOKEN in (_query_value("auth"), st.session_state.get("auth"))


home = st.Page("pages/1_Home.py", title="Home", icon="🏠", default=True)
licenses = st.Page("pages/2_Licenses.py", title="Licenses", icon="📜", url_path="licenses")
pathways = st.Page("pages/3_Pathways.py", title="Pathways", icon="🗺️", url_path="pathways")
directory = st.Page("pages/4_Directory.py", title="Directory", icon="📇", url_path="directory")
capital = st.Page(
    "pages/5_Capital_Stack.py", title="Capital Stack", icon="📊", url_path="capital-stack"
)
about = st.Page("pages/6_About.py", title="About", icon="ℹ️", url_path="about")
admin = st.Page("pages/7_Admin.py", title="Admin", icon="🛡️", url_path="admin")
# Simple path — plain-language send-money explainer (Donate intent lands on
# the Directory pre-filtered to giving flows; see pages/1_Home.py).
remit = st.Page("pages/9_Send_Money.py", title="Send Money", icon="💸", url_path="send-money")

public_pages = [home, licenses, pathways, directory, capital, about, remit]
pages = public_pages + [admin] if _is_admin() else public_pages

# position="hidden": pages route by URL (custom header nav), no sidebar chrome.
pg = st.navigation(pages, position="hidden")
pg.run()
