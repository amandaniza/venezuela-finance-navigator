"""
English / Spanish UI strings with session-state-based lookup.

Usage:
    from i18n.strings import t, set_lang, get_lang
    st.write(t("app_title"))   # resolves via st.session_state.lang
"""

from __future__ import annotations

import streamlit as st

DEFAULT_LANG = "es"
SUPPORTED_LANGS = ("es", "en")

STRINGS: dict[str, dict[str, str]] = {
    "en": {
        "header_kicker": "PHASE 1 MVP | OPERATIONAL INTELLIGENCE",
        "app_title": "Reconstruction Finance Navigator",
        "app_subtitle": (
            "Mapping relief capital to active U.S. OFAC General Licenses"
        ),
        "lang_label": "Language",
        "lang_en": "EN",
        "lang_es": "ES",
        "metrics_heading": "Key Metrics",
        "metric_active_funds": "Active Relief Funds",
        "metric_expiring_licenses": "Expiring Licenses",
        "metric_pathways": "Verified Pathways",
        "navigator_help": (
            "Human-verified pathways only. Operational aid, not legal advice."
        ),
        "col_fund": "Fund Name",
        "col_capital": "Capital Type",
        "col_sectors": "Target Sectors",
        "col_license": "Governing License",
        "col_status": "License Status",
        "col_expiry": "Expiration Date",
        "col_verdict": "Compliance Verdict",
        "verdict_green": "Green",
        "verdict_yellow": "Yellow",
        "verdict_red": "Red",
        "empty_seed": (
            "No verified pathways yet. Run python scripts/seed_demo.py, "
            "then mark pathways Human_Verified in Admin."
        ),
        "expiry_banner": (
            "Expiring license warning: {licenses} expire within {days} days."
        ),
        "expiry_none": (
            "No licenses on displayed pathways expire within {days} days."
        ),
        "rows_shown": "{count} pathway(s) shown",
        "persona_hint": (
            "Capital providers: verify tranches against GL coverage. "
            "Relief operators: filter funding pools by eligible activity."
        ),
        "table_heading": "Verified Pathways",
        "disclaimer": (
            "Confidential operational report. Does not constitute legal advice "
            "or an OFAC determination."
        ),
        "admin_title": "Compliance Administration",
        "admin_kicker": "RESTRICTED | COMPLIANCE OFFICERS",
        "admin_help": (
            "Edit Compliance Verdict and Human Verified, then save. "
            "Only verified pathways appear on the public Navigator."
        ),
        "admin_empty": (
            "No pathways in the database yet. Seed data or run the pipeline, "
            "then verify pathways here."
        ),
        "admin_save": "Save changes",
        "admin_saved": "Saved {count} pathway(s).",
        "admin_col_fund": "Fund",
        "admin_col_license": "License",
        "exec_heading": "Executive Context",
        "exec_col1_title": "The Regulatory Environment",
        "exec_ofac_term": "OFAC",
        "exec_ofac_def": (
            "Office of Foreign Assets Control, the U.S. Treasury agency that "
            "enforces economic and trade sanctions."
        ),
        "exec_gl_term": "GL (General License)",
        "exec_gl_def": (
            "A blanket authorization issued by OFAC that allows specific types "
            "of transactions (like earthquake relief or agricultural exports) "
            "that would otherwise be prohibited under the sanctions regime."
        ),
        "exec_col2_title": "The Capital Stack",
        "exec_blended_term": "Blended Finance",
        "exec_blended_def": (
            "The strategic use of philanthropic or public development capital "
            "to de-risk projects, encouraging private investment to follow."
        ),
        "exec_concessional_term": "Concessional Capital",
        "exec_concessional_def": (
            "Loans extended on terms substantially more generous than market "
            "rates, typically by development banks."
        ),
        # Humanitarian capital stack (funds_tb view)
        "stack_heading": "Humanitarian Capital Stack",
        "stack_help": (
            "Live funding flows and pools for the 2026 Venezuela earthquake "
            "response, from UNOCHA FTS and development-bank announcements. "
            "Filter to see what is open for applications versus already "
            "allocated to primary partners."
        ),
        "stack_filter_label": "Show",
        "stack_filter_all": "All capital",
        "stack_filter_open": "Open for applications",
        "stack_filter_allocated": "Allocated to partners",
        "stack_status_label": "Status",
        "stack_status_all": "All statuses",
        "status_pledged": "Pledged",
        "status_committed": "Committed",
        "status_disbursed": "Disbursed",
        "stack_metric_total": "Total Tracked Capital",
        "stack_metric_open": "Open Funds",
        "stack_metric_allocated": "Allocated Flows",
        "stack_col_fund": "Fund / Commitment",
        "stack_col_donor": "Donor",
        "stack_col_recipient": "Recipient / Access",
        "stack_col_amount": "Amount (USD)",
        "stack_col_status": "Status",
        "stack_col_source": "Source",
        "stack_open_badge": "Open for applications",
        "stack_empty": (
            "No capital matches this filter. Run the pipeline "
            "(python run_pipeline.py) to ingest FTS flows and announcements."
        ),
        "stack_rows_shown": "{count} entr(y/ies) shown · {total} tracked",
    },
    "es": {
        "header_kicker": "FASE 1 MVP | INTELIGENCIA OPERATIVA",
        "app_title": "Navegador de Financiamiento para la Reconstrucción",
        "app_subtitle": (
            "Vincula capital de alivio con Licencias Generales OFAC activas"
        ),
        "lang_label": "Idioma",
        "lang_en": "EN",
        "lang_es": "ES",
        "metrics_heading": "Indicadores clave",
        "metric_active_funds": "Fondos de alivio activos",
        "metric_expiring_licenses": "Licencias por vencer",
        "metric_pathways": "Rutas verificadas",
        "navigator_help": (
            "Solo rutas con verificación humana. Herramienta operativa, "
            "no asesoría legal."
        ),
        "col_fund": "Nombre del fondo",
        "col_capital": "Tipo de capital",
        "col_sectors": "Sectores objetivo",
        "col_license": "Licencia aplicable",
        "col_status": "Estado de la licencia",
        "col_expiry": "Fecha de vencimiento",
        "col_verdict": "Dictamen de cumplimiento",
        "verdict_green": "Verde",
        "verdict_yellow": "Amarillo",
        "verdict_red": "Rojo",
        "empty_seed": (
            "Aún no hay rutas verificadas. Ejecute python scripts/seed_demo.py "
            "y marque Human_Verified en Admin."
        ),
        "expiry_banner": (
            "Alerta de vencimiento: {licenses} vencen en {days} días."
        ),
        "expiry_none": (
            "Ninguna licencia mostrada vence en los próximos {days} días."
        ),
        "rows_shown": "{count} ruta(s) mostrada(s)",
        "persona_hint": (
            "Proveedores de capital: verifique tramos frente a la cobertura de GL. "
            "Operadores de alivio: filtre fondos por actividad elegible."
        ),
        "table_heading": "Rutas verificadas",
        "disclaimer": (
            "Informe operativo confidencial. No constituye asesoría legal ni una "
            "determinación de OFAC."
        ),
        "admin_title": "Administración de cumplimiento",
        "admin_kicker": "RESTRINGIDO | OFICIALES DE CUMPLIMIENTO",
        "admin_help": (
            "Edite el dictamen de cumplimiento y Human Verified, luego guarde. "
            "Solo las rutas verificadas aparecen en el Navegador público."
        ),
        "admin_empty": (
            "Aún no hay rutas en la base de datos. Cargue datos o ejecute el "
            "pipeline, luego verifique las rutas aquí."
        ),
        "admin_save": "Guardar cambios",
        "admin_saved": "Se guardaron {count} ruta(s).",
        "admin_col_fund": "Fondo",
        "admin_col_license": "Licencia",
        "exec_heading": "Contexto ejecutivo",
        "exec_col1_title": "El entorno regulatorio",
        "exec_ofac_term": "OFAC",
        "exec_ofac_def": (
            "Office of Foreign Assets Control, la agencia del Tesoro de EE. UU. "
            "que aplica sanciones económicas y comerciales."
        ),
        "exec_gl_term": "GL (Licencia General)",
        "exec_gl_def": (
            "Una autorización general emitida por OFAC que permite tipos "
            "específicos de transacciones (como alivio por terremoto o "
            "exportaciones agrícolas) que de otro modo estarían prohibidas "
            "bajo el régimen de sanciones."
        ),
        "exec_col2_title": "La estructura de capital",
        "exec_blended_term": "Financiamiento combinado",
        "exec_blended_def": (
            "El uso estratégico de capital filantrópico o de desarrollo público "
            "para reducir el riesgo de proyectos e incentivar la inversión privada."
        ),
        "exec_concessional_term": "Capital concesional",
        "exec_concessional_def": (
            "Préstamos otorgados en condiciones sustancialmente más favorables "
            "que las del mercado, generalmente por bancos de desarrollo."
        ),
        # Estructura de capital humanitario (vista de funds_tb)
        "stack_heading": "Estructura de Capital Humanitario",
        "stack_help": (
            "Flujos y fondos de financiamiento en vivo para la respuesta al "
            "terremoto de Venezuela 2026, desde UNOCHA FTS y anuncios de bancos "
            "de desarrollo. Filtre para ver qué está abierto a solicitudes "
            "frente a lo ya asignado a socios principales."
        ),
        "stack_filter_label": "Mostrar",
        "stack_filter_all": "Todo el capital",
        "stack_filter_open": "Abierto a solicitudes",
        "stack_filter_allocated": "Asignado a socios",
        "stack_status_label": "Estado",
        "stack_status_all": "Todos los estados",
        "status_pledged": "Prometido",
        "status_committed": "Comprometido",
        "status_disbursed": "Desembolsado",
        "stack_metric_total": "Capital total rastreado",
        "stack_metric_open": "Fondos abiertos",
        "stack_metric_allocated": "Flujos asignados",
        "stack_col_fund": "Fondo / Compromiso",
        "stack_col_donor": "Donante",
        "stack_col_recipient": "Receptor / Acceso",
        "stack_col_amount": "Monto (USD)",
        "stack_col_status": "Estado",
        "stack_col_source": "Fuente",
        "stack_open_badge": "Abierto a solicitudes",
        "stack_empty": (
            "Ningún capital coincide con este filtro. Ejecute el pipeline "
            "(python run_pipeline.py) para ingerir flujos FTS y anuncios."
        ),
        "stack_rows_shown": "{count} entrada(s) mostrada(s) · {total} rastreado",
    },
}


def get_lang() -> str:
    """Return the current language from session state (default Spanish)."""
    lang = st.session_state.get("lang", DEFAULT_LANG)
    return lang if lang in SUPPORTED_LANGS else DEFAULT_LANG


def set_lang(lang: str) -> None:
    st.session_state.lang = lang if lang in SUPPORTED_LANGS else DEFAULT_LANG


def t(key: str, **kwargs: object) -> str:
    """Look up a string for the active language, with optional formatting."""
    lang = get_lang()
    bundle = STRINGS.get(lang, STRINGS[DEFAULT_LANG])
    template = bundle.get(key) or STRINGS["en"].get(key, key)
    if kwargs:
        return template.format(**kwargs)
    return template
