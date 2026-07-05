"""Admin — compliance officers edit pathway verdicts and verification flags."""

from __future__ import annotations

from html import escape

import pandas as pd
import streamlit as st

from database import fetch_pathways_for_admin, init_db, update_pathways_batch
from i18n.strings import t

init_db()

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    header[data-testid="stHeader"] {display: none;}
    footer {visibility: hidden;}
    #MainMenu {visibility: hidden;}
    .stApp, [data-testid="stAppViewContainer"], .block-container {background-color: #FFFFFF !important;}
    html, body, [class*="css"], .stApp, p, span, label, div, h1 {
        font-family: 'Inter', 'Helvetica Neue', Helvetica, Arial, sans-serif !important;
    }
    .block-container {padding-top: 1.75rem !important; max-width: 1120px;}
    .admin-kicker {
        margin: 0 0 0.7rem 0; font-size: 0.72rem; font-weight: 600;
        letter-spacing: 0.16em; text-transform: uppercase; color: #9A3412;
    }
    .admin-title {
        margin: 0 0 0.5rem 0; font-size: 2rem; font-weight: 800;
        letter-spacing: -0.02em; color: #0A1F44;
    }
    .admin-note {margin: 0 0 1.5rem 0; font-size: 0.9rem; color: #4B5563; line-height: 1.5;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    f"""
    <div>
        <p class="admin-kicker">{escape(t("admin_kicker"))}</p>
        <h1 class="admin-title">{escape(t("admin_title"))}</h1>
        <p class="admin-note">{escape(t("admin_help"))}</p>
    </div>
    """,
    unsafe_allow_html=True,
)

rows = fetch_pathways_for_admin()

if not rows:
    st.warning(t("admin_empty"))
    st.stop()

editor_df = pd.DataFrame(
    [
        {
            "Map_ID": r["map_id"],
            t("admin_col_fund"): r["fund_name"],
            t("admin_col_license"): r["license_id"],
            "Compliance_Verdict": r["compliance_verdict"] or "Yellow",
            "Human_Verified": bool(r["human_verified"]),
        }
        for r in rows
    ]
)

edited = st.data_editor(
    editor_df,
    use_container_width=True,
    hide_index=True,
    num_rows="fixed",
    column_config={
        "Map_ID": st.column_config.NumberColumn("Map_ID", disabled=True),
        t("admin_col_fund"): st.column_config.TextColumn(
            t("admin_col_fund"), disabled=True
        ),
        t("admin_col_license"): st.column_config.TextColumn(
            t("admin_col_license"), disabled=True
        ),
        "Compliance_Verdict": st.column_config.SelectboxColumn(
            "Compliance_Verdict",
            options=["Green", "Yellow", "Red"],
            required=True,
        ),
        "Human_Verified": st.column_config.CheckboxColumn("Human_Verified"),
    },
    key="pathways_admin_editor",
)

if st.button(t("admin_save"), type="primary"):
    payload = [
        {
            "map_id": int(row["Map_ID"]),
            "compliance_verdict": str(row["Compliance_Verdict"]),
            "human_verified": bool(row["Human_Verified"]),
        }
        for _, row in edited.iterrows()
    ]
    updated = update_pathways_batch(payload)
    st.success(t("admin_saved", count=updated))
    st.rerun()
