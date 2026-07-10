"""
Shared chrome + component library for the multipage Navigator.

Every page (Home, Licenses, Pathways, Directory, Capital Stack, About) imports
from here so the flag-themed header, footer, CSS, i18n strings, and the
language/nav helpers live in ONE place — no copy-pasted header HTML.

Key pieces:
  * STRINGS          — all EN/ES copy.
  * Ctx(active)      — language + query-param context bound to the active page.
                       Use c.page_url()/c.nav_link() for cross-page links and
                       c.href()/c.filter_href() for same-page filter/detail
                       links so ?lang= and ?auth= never silently drop.
  * render_page(c, active, body) — wraps a page body in the shared shell.
  * Section builders — reusable HTML blocks (license cards, pathways table,
                       directory, capital stack, detail views) the pages call.

This module renders nothing on import; pages drive the rendering.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from html import escape
from urllib.parse import quote

import streamlit as st

import config
from database import (
    fetch_funding_source,
    fetch_funding_sources,
    fetch_licenses,
    fetch_pathway,
    fetch_public_funds,
    fetch_verified_pathways,
    init_db,
)

EXPIRY_WARNING_DAYS = 30
SUPPORTED_LANGS = ("es", "en")
DEFAULT_LANG = "es"
CONTACT_EMAIL = config.CONTACT_EMAIL

# Venezuelan flag palette
YELLOW = "#FCD116"
BLUE = "#00247D"
RED = "#CF142B"
DARK_BLUE = "#001845"
DARK_RED = "#7a1420"
INK = "#12172B"
MUTE = "#5B6472"
SWATCHES = [BLUE, RED, DARK_RED, "#0a3a8f"]

# ---------------------------------------------------------------------------
# Copy (ported from the design, both languages)
# ---------------------------------------------------------------------------

STRINGS: dict[str, dict[str, str]] = {
    "en": {
        "nav_navigator": "Navigator",
        "nav_methodology": "Methodology",
        "nav_admin": "Admin",
        "hero_title_l1": "When Capital Moves,",
        "hero_title_l2": "Relief Follows",
        "app_subtitle": (
            "Mapping earthquake relief and reconstruction capital to active "
            "U.S. OFAC General Licenses, so funds move fast and stay "
            "compliant."
        ),
        "hero_cta": "View Verified Pathways",
        "hero_photo": "PHOTO PLACEHOLDER: reconstruction site, La Guaira / Caracas",
        "stories_label": "ACTIVE LICENSES",
        "lic_authorized": "authorized",
        "lic_expired_suffix": "(expired)",
        "lic_tag_active": "ACTIVE",
        "lic_tag_expired": "EXPIRED",
        "lic_tag_expiring": "EXPIRING SOON",
        "lic_none": "No licenses ingested yet. Run the pipeline to populate OFAC actions.",
        "data_kicker": "DATA FOR",
        "data_heading": "COMPLIANCE",
        "data_body": (
            "Every pathway maps a funding vehicle to the OFAC license that "
            "authorizes it. Filter by focus area to see what's eligible."
        ),
        "data_cta": "See Full Navigator",
        "explore_focus": "Explore by focus area",
        "gl_source_ofac": "SOURCE: OFAC GUIDANCE",
        "gl_source_glossary": "SOURCE: GLOSSARY",
        "gl_ofac_term": "OFAC",
        "gl_ofac_def": (
            "Office of Foreign Assets Control, the U.S. Treasury agency "
            "that enforces economic and trade sanctions."
        ),
        "gl_gl_term": "GL (General License)",
        "gl_gl_def": (
            "A blanket authorization issued by OFAC. It allows specific "
            "transactions, such as earthquake relief, that sanctions "
            "would otherwise prohibit."
        ),
        "signup_l1": "Stay current with",
        "signup_bold": "expiring license alerts",
        "signup_email": "* Your email",
        "signup_org": "Your organization",
        "signup_consent": (
            "I agree to receive operational updates on OFAC license status and "
            "reconstruction funding pathways."
        ),
        "signup_button": "Sign Up",
        "pathways_kicker": "VERIFIED",
        "pathways_heading": "PATHWAYS",
        "pathways_more": "View All Pathways",
        "verdict_green": "Green",
        "verdict_yellow": "Yellow",
        "verdict_red": "Red",
        "feature_green_tmpl": "{fund} clears {license}. Authorized for relief.",
        "feature_red_tmpl": "{fund} is blocked. Governing license {license} is {status}.",
        "feature_green_fallback": (
            "Verified pathways clear their governing OFAC license. Relief "
            "capital is authorized to move."
        ),
        "feature_red_fallback": (
            "Watch for pathways whose governing license has expired or been "
            "revoked. Capital is blocked until re-licensed."
        ),
        "pathways_note": "Human-verified pathways only. Operational aid, not legal advice.",
        "pathways_empty": (
            "No verified pathways yet. Verify pathways in Admin to publish them here."
        ),
        "rows_shown": "{count} pathway(s) shown",
        "power_kicker": "THE POWER OF",
        "power_heading": "COMPLIANCE",
        "power_body": (
            "Sanctions compliance is the bottleneck between capital and relief. "
            "Verified pathways let providers and operators move faster, together."
        ),
        "power_photo": "PHOTO PLACEHOLDER: relief worker / field team",
        "metric_active_funds": "Active Relief Funds",
        "metric_expiring": "Expiring Licenses",
        "metric_pathways": "Verified Pathways",
        "banner_l1": "Mapping Capital.",
        "banner_l2": "Enabling Relief.",
        "banner_body": (
            "Trusted, human-verified data helps capital providers and relief "
            "operators deploy funds without regulatory delay."
        ),
        "banner_link1_title": "Compliance Methodology",
        "banner_link2_title": "Data Pipeline",
        "learn_more": "Learn More",
        "stack_kicker": "TRACKING",
        "stack_heading": "FUNDS TO IMPACT",
        "stack_seeall": "See all Funds",
        "stack_photo": "PHOTO PLACEHOLDER: hospital reconstruction site",
        "explore_capital": "Filter by capital type",
        "cap_all": "All capital",
        "stack_open_badge": "Open for applications",
        "stack_total": "{total} tracked across {count} flows",
        "stack_empty": "No tracked capital yet. Run the pipeline to ingest FTS flows.",
        "sources_kicker": "DATA",
        "sources_heading": "SOURCES",
        "sources_body": (
            "We monitor public regulatory and funding announcements daily so "
            "pathways stay current."
        ),
        "source_ofac": "OFAC Recent Actions",
        "source_fts": "UNOCHA FTS & Development Bank Announcements",
        # Context bar
        "context_estimate": "UN reconstruction estimate",
        "context_tracked": "Tracked so far",
        "context_in_need": "People in need (earthquake)",
        "context_gap_note": (
            "≈{tracked} identified against a ~{estimate} reconstruction bill. "
            "This directory exists to close that gap."
        ),
        # Funding Directory
        "dir_heading": "FUNDING DIRECTORY",
        "dir_kicker": "RESEARCHED LEADS",
        "dir_intro": (
            "{count} researched funding sources: where money can be given and where "
            "NGOs can apply. Every entry links to its authoritative source."
        ),
        "dir_review_badge": "Compliance pathway under review",
        "dir_review_note": (
            "None of these are verified compliance verdicts. They are researched "
            "leads; a human assigns a Green/Red verdict only after reviewing the "
            "license text. Verified pathways appear in the Pathways section above."
        ),
        "dir_filter_flow": "Money direction",
        "dir_flow_all": "All",
        "dir_flow_give": "Where you can give",
        "dir_flow_apply": "Where NGOs can apply",
        "dir_filter_phase": "Phase",
        "dir_phase_all": "All phases",
        "phase_relief": "Relief",
        "phase_recovery": "Recovery",
        "phase_reconstruction": "Reconstruction",
        "dir_filter_layer": "Your layer",
        "layer_all": "Everyone",
        "layer_institutional": "Institutional funder",
        "layer_ngo": "NGO / operator",
        "layer_diaspora": "Diaspora / public",
        "layer_community": "Community-organized",
        "layer_platform": "Platform / directory",
        "flow_give_badge": "Give here",
        "flow_apply_badge": "NGOs can apply",
        "flow_both_badge": "Give or apply",
        "flow_direct_badge": "Direct to families",
        "flow_gov_badge": "Government resource",
        "flow_directory_badge": "Verified directory",
        "flow_pipeline_badge": "Upcoming",
        "dir_target": "Target",
        "dir_committed": "Committed / raised",
        "dir_visit": "Visit source ↗",
        "dir_details": "Details →",
        "dir_last_checked": "Last checked {date}",
        "dir_none": "No sources match these filters.",
        "dir_count": "{count} of {total} sources shown",
        "dir_suggest": "Suggest a source or report an issue →",
        "ocha_slot_title": "OCHA Revised Response Plan",
        "ocha_slot_body": (
            "A consolidated funding requirement lands the week of {date}. This "
            "slot updates automatically from the FTS API once the appeal is live."
        ),
        "ocha_slot_badge": "Expected week of {date}",
        # Detail view
        "detail_back": "← Back to Navigator",
        "detail_source_link": "Go to official source ↗",
        "detail_amounts": "Amounts",
        "detail_target": "Target",
        "detail_committed": "Committed / raised",
        "detail_accepts": "Accepts from",
        "detail_goes_to": "Funds go to",
        "detail_compliance": "Compliance notes",
        "detail_suggested": "Suggested license pathway",
        "detail_license_ctx": "License context",
        "detail_gl60_ctx": "GL 60: earthquake relief authorization, expires {date}.",
        "detail_status": "Status",
        "detail_phase": "Phase",
        "detail_org_type": "Organization type",
        "detail_verification": "Verification",
        "detail_notes": "Notes",
        "detail_how_title": "How to contribute",
        "detail_pathway_kicker": "VERIFIED PATHWAY",
        "detail_pw_fund": "Fund",
        "detail_pw_license": "Governing license",
        "detail_pw_verdict": "Compliance verdict",
        "detail_pw_expiry": "License expiration",
        "detail_pw_sectors": "Target sectors",
        "detail_pw_capital": "Capital type",
        "verif_unverified": "Unverified, pathway under review",
        "verif_reported_unconfirmed": "Reported, unconfirmed",
        "verif_platform_vetted": "Platform-vetted",
        "verif_pipeline": "Pipeline, not yet launched",
        # Navigation + chrome
        "app_title": "Reconstruction Finance Navigator",
        "nav_licenses": "Licenses",
        "nav_pathways": "Pathways",
        "nav_directory": "Directory",
        "nav_capital": "Capital Stack",
        "nav_about": "About",
        "crumb_home": "← Home",
        "footer_report": "Report an issue",
        "footer_updated": "Updated {date}",
        "footer_learn_about": "What “verified” means →",
        "disclaimer_short": (
            "Informational resource. Not legal advice or an OFAC determination."
        ),
        # Home
        "home_value_prop": (
            "A living map of relief and reconstruction financing for Venezuela, "
            "tagged by sanctions pathway."
        ),
        "home_cta": "Explore verified pathways",
        "m_tracked": "Tracked across flows",
        "m_licenses": "Active licenses",
        "m_pathways": "Verified pathways",
        "m_gl60_days": "Days until GL 60 expires",
        "gl60_countdown_note": (
            "GL 60 authorizes earthquake-relief transfers into Venezuela. It "
            "expires {date}. The window to move funds under it is closing."
        ),
        "fc_licenses_desc": (
            "The OFAC General Licenses that authorize relief and reconstruction "
            "transactions."
        ),
        "fc_pathways_desc": "Human-verified funds mapped to the license that clears them.",
        "fc_directory_desc": "Researched sources: where to give and where NGOs can apply.",
        "fc_capital_desc": "Live donor→recipient flows tracked from UNOCHA FTS.",
        "fc_licenses_teaser": "{n} active · GL 60 expires {date}",
        "fc_pathways_teaser": "{n} verified pathway(s)",
        "fc_directory_teaser": "{n} sources · relief → reconstruction",
        "fc_capital_teaser": "≈{amount} across {n} flows",
        # Cross-links
        "xl_license_pathways": "See pathways cleared by this license →",
        "xl_pathway_license": "View governing license →",
        "xl_source_license": "See suggested license →",
        "xl_flow_directory": "See in Directory →",
        # Licenses page
        "lic_page_intro": (
            "The U.S. OFAC General Licenses that authorize relief and "
            "reconstruction transactions with Venezuela."
        ),
        "lic_expires": "Expires",
        "lic_no_expiry": "No stated expiry",
        "lic_official_source": "Official OFAC source ↗",
        "lic_activities": "Authorized activities",
        # Pathways page
        "pw_intro": (
            "Funds mapped to the OFAC license that governs them, with a "
            "human-assigned compliance verdict. Verified entries only."
        ),
        "pw_filtered_to": "Filtered to {gl}",
        "pw_clear_filter": "Clear filter",
        # Capital page
        "cap_intro": (
            "Live funding flows into Venezuela reported to UNOCHA FTS: who "
            "gave, who received, how much, and where it sits in the pipeline."
        ),
        # About page
        "about_intro": (
            "The Reconstruction Finance Navigator maps where relief and "
            "reconstruction money for Venezuela comes from, and whether a U.S. "
            "sanctions pathway exists to move it."
        ),
        "about_verified_h": "What “verified” means",
        "about_verified_body": (
            "A pathway is marked verified only after a human reviews the license "
            "text and the fund's own compliance posture and assigns a Green, "
            "Yellow, or Red verdict. Only verified pathways appear on the "
            "Pathways page."
        ),
        "about_notverified_h": "What it does not mean",
        "about_notverified_body": (
            "Everything in the Funding Directory is a researched lead marked "
            "“Compliance pathway under review.” It is not a verdict, not legal "
            "advice, and not an OFAC determination. This is an informational "
            "resource; confirm your own compliance before moving funds."
        ),
        "about_sources_h": "Data sources",
        "about_sources_body": (
            "OFAC Recent Actions (licenses), UNOCHA FTS (funding flows), and a "
            "curated directory of researched funding sources, including "
            "accredited community-organized funds. Each links to its "
            "authoritative public page."
        ),
        "about_cadence_h": "Update cadence",
        "about_cadence_body": (
            "Licenses and flows refresh from their source APIs; the directory "
            "was last checked {date}. OCHA's revised response plan is expected "
            "the week of {ocha} and will update the tracked totals."
        ),
        "about_contact_h": "Contact",
        "about_contact_body": "Report an issue or suggest a source:",
        "about_disclaimer_h": "Disclaimer",
        "about_disclaimer_body": (
            "This site is a volunteer effort to compile information and links "
            "about cooperation, humanitarian assistance, and financing "
            "initiatives that support reconstruction after the earthquakes in "
            "Venezuela, under the economic sanctions regime currently in "
            "force. Compilation is done with an AI engine, followed by "
            "verification of each initiative. The people responsible for this "
            "site have no affiliation with the institutions and organizations "
            "listed, do not participate in the listed projects, and do not "
            "benefit in any way from contributions made through the linked "
            "platforms. Source verification and reliability classification "
            "are approximate and do not imply any responsibility on our part "
            "for the administration of donated funds or the management of "
            "aid projects."
        ),
        # Footer contacts
        "footer_contacts_h": "CONTACTS",
        "contact_maintainer": "Site maintainer: questions, corrections, new sources",
        "contact_ofac": "OFAC sanctions & license questions (U.S. Treasury)",
        "contact_caf": "CAF Reconstruction Fund contributions",
        "contact_fts": "UNOCHA FTS funding-flow data",
        # Glossary (hover/tap definitions for acronyms, both modes)
        "gl_mdb_term": "MDB (Multilateral Development Bank)",
        "gl_mdb_def": (
            "A bank owned by many member governments, such as CAF or the "
            "IDB. It finances development and reconstruction projects."
        ),
        "gl_ingo_term": "INGO (International NGO)",
        "gl_ingo_def": (
            "A non-governmental organization that works in many countries, "
            "for example the International Rescue Committee or Save the "
            "Children."
        ),
        # Simple paths — intent-first front door
        "home_welcome_eyebrow": "Welcome",
        "home_welcome_lead": (
            "The purpose of this independent initiative is to share "
            "information about the resources available to support rescue and "
            "recovery efforts in Venezuela after the devastating earthquake "
            "of {date}. Here you will find current information on:"
        ),
        "home_welcome_a_h": "Donations",
        "home_welcome_a": (
            "Ways to make effective donations to multilateral institutions, "
            "national organizations, and NGOs that work on the ground or "
            "offer channels for monetary aid."
        ),
        "home_welcome_b_h": "Money transfers",
        "home_welcome_b": (
            "Authorized mechanisms for sending money to individuals and "
            "families (distinct from donations, and not intended for "
            "commercial transactions)."
        ),
        "intent_heading": "How do you want to help?",
        "intent_sub": (
            "Pick the option that fits you. We show only what you need, in "
            "plain language."
        ),
        "intent_donate_t": "I want to donate",
        "intent_donate_d": "Trusted places to give money for earthquake relief.",
        "intent_remit_t": "I want to send money to family",
        "intent_remit_d": (
            "What is allowed right now, which channels work, and what to avoid."
        ),
        "intent_full_link": "Or explore the full navigator ↓",
        "simple_disclaimer": (
            "General information, not legal advice. For your specific "
            "situation, consult a licensed professional."
        ),
        # Send-money path
        "rem_title": "Sending money to family in Venezuela",
        "rem_intro": (
            "What is allowed right now, in plain language. This page is about "
            "personal transfers to family, not business payments or "
            "donations."
        ),
        "rem_q1_h": "Can I send money right now?",
        "rem_q1_a": "Yes, in most cases.",
        "rem_q1_body": (
            "Personal, non-commercial transfers to family in Venezuela are "
            "generally allowed. A U.S. authorization ({gl}) permits the "
            "financial services these transfers rely on, including "
            "transactions involving certain Venezuelan banks."
        ),
        "rem_q2_h": "What channels can I use?",
        "rem_q2_b1": (
            "Bank transfers to accounts at the four banks GL 57 covers: "
            "Banco Central de Venezuela, Banco de Venezuela, Banco Digital "
            "de los Trabajadores, and Banco del Tesoro, plus entities they "
            "own 50% or more of."
        ),
        "rem_q2_b2": (
            "Licensed money-transfer services that serve Venezuela. Check "
            "that the service is licensed where you live before sending."
        ),
        "rem_q2_note": (
            "Transfers to accounts at other Venezuelan banks, including "
            "private banks like Banesco, Mercantil, or BOD, are not covered "
            "by GL 57. If you are not sure which bank your family uses, "
            "check with a professional before sending."
        ),
        "rem_q3_h": "Is there a deadline?",
        "rem_q3_noexp": (
            "{gl} has no stated end date, but U.S. authorizations can change "
            "or be withdrawn with little notice. If you plan a large "
            "transfer, do not assume today's rules will hold indefinitely."
        ),
        "rem_q3_exp": (
            "{gl} is currently set to expire on {date}. After that date the "
            "rules may change. Check back before sending."
        ),
        "rem_q4_h": "What should I avoid?",
        "rem_q4_b1": (
            "Sending money to anyone on a U.S. sanctions list, or to "
            "Venezuelan government entities."
        ),
        "rem_q4_b2": (
            "Disguising business or commercial payments as family support. "
            "Only personal, non-commercial transfers are covered."
        ),
        "rem_q4_b3": (
            "Unlicensed, informal transfer networks. You have no protection "
            "if the money disappears."
        ),
        "rem_license_link": "Full license details →",
    },
    "es": {
        "nav_navigator": "Navegador",
        "nav_methodology": "Metodología",
        "nav_admin": "Admin",
        "hero_title_l1": "Cuando el Capital se Mueve,",
        "hero_title_l2": "el Alivio Sigue",
        "app_subtitle": (
            "Vincula el capital de alivio y reconstrucción por terremoto con "
            "las Licencias Generales OFAC activas, para que los fondos se "
            "muevan rápido y con cumplimiento."
        ),
        "hero_cta": "Ver Rutas Verificadas",
        "hero_photo": "IMAGEN: sitio de reconstrucción, La Guaira / Caracas",
        "stories_label": "LICENCIAS ACTIVAS",
        "lic_authorized": "autorizado",
        "lic_expired_suffix": "(vencida)",
        "lic_tag_active": "ACTIVA",
        "lic_tag_expired": "VENCIDA",
        "lic_tag_expiring": "POR VENCER",
        "lic_none": "Aún no hay licencias. Ejecute el pipeline para cargar acciones de OFAC.",
        "data_kicker": "DATOS PARA EL",
        "data_heading": "CUMPLIMIENTO",
        "data_body": (
            "Cada ruta vincula un vehículo de financiamiento con la licencia "
            "OFAC que lo autoriza. Filtre por área para ver qué es elegible."
        ),
        "data_cta": "Ver Navegador Completo",
        "explore_focus": "Explorar por área",
        "gl_source_ofac": "FUENTE: GUÍA OFAC",
        "gl_source_glossary": "FUENTE: GLOSARIO",
        "gl_ofac_term": "OFAC",
        "gl_ofac_def": (
            "Office of Foreign Assets Control, la agencia del Tesoro de "
            "EE. UU. que aplica sanciones económicas y comerciales."
        ),
        "gl_gl_term": "GL (Licencia General)",
        "gl_gl_def": (
            "Autorización general emitida por OFAC que permite transacciones "
            "específicas, como el alivio por terremoto, que de otro modo "
            "estarían prohibidas."
        ),
        "signup_l1": "Manténgase al día con",
        "signup_bold": "alertas de vencimiento",
        "signup_email": "* Su correo",
        "signup_org": "Su organización",
        "signup_consent": (
            "Acepto recibir actualizaciones operativas sobre el estado de "
            "licencias OFAC y rutas de financiamiento."
        ),
        "signup_button": "Suscribirse",
        "pathways_kicker": "RUTAS",
        "pathways_heading": "VERIFICADAS",
        "pathways_more": "Ver Todas las Rutas",
        "verdict_green": "Verde",
        "verdict_yellow": "Amarillo",
        "verdict_red": "Rojo",
        "feature_green_tmpl": "{fund} cumple con {license}. Autorizado para el alivio.",
        "feature_red_tmpl": "{fund} está bloqueado. La licencia {license} está {status}.",
        "feature_green_fallback": (
            "Las rutas verificadas cumplen con su licencia OFAC. El capital "
            "de alivio está autorizado para moverse."
        ),
        "feature_red_fallback": (
            "Vigile las rutas cuya licencia haya vencido o sido revocada. "
            "El capital queda bloqueado hasta obtener una nueva licencia."
        ),
        "pathways_note": "Solo rutas con verificación humana. Herramienta operativa, no asesoría legal.",
        "pathways_empty": (
            "Aún no hay rutas verificadas. Verifíquelas en Admin para publicarlas aquí."
        ),
        "rows_shown": "{count} ruta(s) mostrada(s)",
        "power_kicker": "EL PODER DEL",
        "power_heading": "CUMPLIMIENTO",
        "power_body": (
            "El cumplimiento de sanciones es el cuello de botella entre el "
            "capital y el alivio. Las rutas verificadas permiten avanzar más "
            "rápido, juntos."
        ),
        "power_photo": "IMAGEN: personal de alivio / equipo de campo",
        "metric_active_funds": "Fondos de Alivio Activos",
        "metric_expiring": "Licencias por Vencer",
        "metric_pathways": "Rutas Verificadas",
        "banner_l1": "Vinculando Capital.",
        "banner_l2": "Habilitando el Alivio.",
        "banner_body": (
            "Datos confiables con verificación humana ayudan a las "
            "organizaciones que proveen capital y operan la ayuda a "
            "desplegar fondos sin demora regulatoria."
        ),
        "banner_link1_title": "Metodología de Cumplimiento",
        "banner_link2_title": "Pipeline de Datos",
        "learn_more": "Saber Más",
        "stack_kicker": "RASTREANDO",
        "stack_heading": "FONDOS HASTA EL IMPACTO",
        "stack_seeall": "Ver todos los Fondos",
        "stack_photo": "IMAGEN: sitio de reconstrucción hospitalaria",
        "explore_capital": "Filtrar por tipo de capital",
        "cap_all": "Todo el capital",
        "stack_open_badge": "Abierto a solicitudes",
        "stack_total": "{total} rastreado en {count} flujos",
        "stack_empty": "Aún no hay capital rastreado. Ejecute el pipeline para ingerir flujos FTS.",
        "sources_kicker": "FUENTES DE",
        "sources_heading": "DATOS",
        "sources_body": (
            "Monitoreamos anuncios regulatorios y de financiamiento públicos a "
            "diario para mantener las rutas actualizadas."
        ),
        "source_ofac": "Acciones Recientes de OFAC",
        "source_fts": "UNOCHA FTS y Anuncios de Bancos de Desarrollo",
        # Context bar
        "context_estimate": "Estimación de reconstrucción ONU",
        "context_tracked": "Rastreado hasta ahora",
        "context_in_need": "Personas necesitadas (terremoto)",
        "context_gap_note": (
            "≈{tracked} identificados frente a una factura de reconstrucción de "
            "~{estimate}. Este directorio busca cerrar esa brecha."
        ),
        # Directorio de Financiamiento
        "dir_heading": "DIRECTORIO DE FINANCIAMIENTO",
        "dir_kicker": "FUENTES INVESTIGADAS",
        "dir_intro": (
            "{count} fuentes de financiamiento investigadas: dónde se puede donar y "
            "dónde las ONG pueden postular. Cada entrada enlaza a su fuente oficial."
        ),
        "dir_review_badge": "Ruta de cumplimiento en revisión",
        "dir_review_note": (
            "Ninguna de estas es un dictamen de cumplimiento verificado. Son "
            "fuentes investigadas; el dictamen Verde/Rojo se asigna solo tras "
            "una revisión humana del texto de la licencia. Las rutas "
            "verificadas aparecen en la sección Rutas más arriba."
        ),
        "dir_filter_flow": "Dirección del dinero",
        "dir_flow_all": "Todo",
        "dir_flow_give": "Dónde puede donar",
        "dir_flow_apply": "Dónde postulan las ONG",
        "dir_filter_phase": "Fase",
        "dir_phase_all": "Todas las fases",
        "phase_relief": "Alivio",
        "phase_recovery": "Recuperación",
        "phase_reconstruction": "Reconstrucción",
        "dir_filter_layer": "Su perfil",
        "layer_all": "Cualquier perfil",
        "layer_institutional": "Institución financiadora",
        "layer_ngo": "ONG / entidad operadora",
        "layer_diaspora": "Diáspora / público",
        "layer_community": "Fondos comunitarios",
        "layer_platform": "Plataforma / directorio",
        "flow_give_badge": "Done aquí",
        "flow_apply_badge": "ONG pueden postular",
        "flow_both_badge": "Donar o postular",
        "flow_direct_badge": "Directo a familias",
        "flow_gov_badge": "Recurso del gobierno",
        "flow_directory_badge": "Directorio verificado",
        "flow_pipeline_badge": "Próximamente",
        "dir_target": "Meta",
        "dir_committed": "Comprometido / recaudado",
        "dir_visit": "Ir a la fuente ↗",
        "dir_details": "Detalles →",
        "dir_last_checked": "Verificado {date}",
        "dir_none": "Ninguna fuente coincide con estos filtros.",
        "dir_count": "{count} de {total} fuentes mostradas",
        "dir_suggest": "Sugerir una fuente o reportar un problema →",
        "ocha_slot_title": "Plan de Respuesta Revisado de OCHA",
        "ocha_slot_body": (
            "Un requerimiento de financiamiento consolidado llega la semana del "
            "{date}. Este espacio se actualiza automáticamente desde la API de FTS "
            "cuando el llamamiento esté activo."
        ),
        "ocha_slot_badge": "Esperado la semana del {date}",
        # Vista de detalle
        "detail_back": "← Volver al Navegador",
        "detail_source_link": "Ir a la fuente oficial ↗",
        "detail_amounts": "Montos",
        "detail_target": "Meta",
        "detail_committed": "Comprometido / recaudado",
        "detail_accepts": "Acepta de",
        "detail_goes_to": "Los fondos van a",
        "detail_compliance": "Notas de cumplimiento",
        "detail_suggested": "Ruta de licencia sugerida",
        "detail_license_ctx": "Contexto de licencia",
        "detail_gl60_ctx": "GL 60: autorización de alivio por terremoto, vence {date}.",
        "detail_status": "Estado",
        "detail_phase": "Fase",
        "detail_org_type": "Tipo de organización",
        "detail_verification": "Verificación",
        "detail_notes": "Notas",
        "detail_how_title": "Cómo contribuir",
        "detail_pathway_kicker": "RUTA VERIFICADA",
        "detail_pw_fund": "Fondo",
        "detail_pw_license": "Licencia aplicable",
        "detail_pw_verdict": "Dictamen de cumplimiento",
        "detail_pw_expiry": "Vencimiento de licencia",
        "detail_pw_sectors": "Sectores objetivo",
        "detail_pw_capital": "Tipo de capital",
        "verif_unverified": "Sin verificar, ruta en revisión",
        "verif_reported_unconfirmed": "Reportado, sin confirmar",
        "verif_platform_vetted": "Verificado por la plataforma",
        "verif_pipeline": "En preparación, aún sin lanzar",
        # Navegación + chrome
        "app_title": "Navegador de Financiamiento para la Reconstrucción",
        "nav_licenses": "Licencias",
        "nav_pathways": "Rutas",
        "nav_directory": "Directorio",
        "nav_capital": "Capital",
        "nav_about": "Acerca de",
        "crumb_home": "← Inicio",
        "footer_report": "Reportar un problema",
        "footer_updated": "Actualizado {date}",
        "footer_learn_about": "Qué significa “verificado” →",
        "disclaimer_short": (
            "Recurso informativo. No constituye asesoría legal ni una "
            "determinación de OFAC."
        ),
        # Inicio
        "home_value_prop": (
            "Un mapa vivo del financiamiento de ayuda y reconstrucción para "
            "Venezuela, clasificado por ruta de cumplimiento."
        ),
        "home_cta": "Explorar rutas verificadas",
        "m_tracked": "Rastreado en flujos",
        "m_licenses": "Licencias activas",
        "m_pathways": "Rutas verificadas",
        "m_gl60_days": "Días para que venza la GL 60",
        "gl60_countdown_note": (
            "La GL 60 autoriza transferencias de ayuda por terremoto hacia "
            "Venezuela. Vence el {date}. La ventana para mover fondos se está cerrando."
        ),
        "fc_licenses_desc": (
            "Las Licencias Generales de OFAC que autorizan transacciones de "
            "ayuda y reconstrucción."
        ),
        "fc_pathways_desc": "Fondos verificados vinculados a la licencia que los habilita.",
        "fc_directory_desc": "Fuentes investigadas: dónde donar y dónde postulan las ONG.",
        "fc_capital_desc": "Flujos donante→receptor en vivo, desde UNOCHA FTS.",
        "fc_licenses_teaser": "{n} activas · GL 60 vence {date}",
        "fc_pathways_teaser": "{n} ruta(s) verificada(s)",
        "fc_directory_teaser": "{n} fuentes · alivio → reconstrucción",
        "fc_capital_teaser": "≈{amount} en {n} flujos",
        # Enlaces cruzados
        "xl_license_pathways": "Ver rutas habilitadas por esta licencia →",
        "xl_pathway_license": "Ver licencia aplicable →",
        "xl_source_license": "Ver licencia sugerida →",
        "xl_flow_directory": "Ver en el Directorio →",
        # Página de Licencias
        "lic_page_intro": (
            "Las Licencias Generales de OFAC que autorizan transacciones de "
            "ayuda y reconstrucción con Venezuela."
        ),
        "lic_expires": "Vence",
        "lic_no_expiry": "Sin fecha de vencimiento",
        "lic_official_source": "Fuente oficial de OFAC ↗",
        "lic_activities": "Actividades autorizadas",
        # Página de Rutas
        "pw_intro": (
            "Fondos vinculados a la licencia OFAC que los rige, con un dictamen "
            "de cumplimiento asignado tras revisión humana. Solo entradas verificadas."
        ),
        "pw_filtered_to": "Filtrado a {gl}",
        "pw_clear_filter": "Quitar filtro",
        # Página de Capital
        "cap_intro": (
            "Flujos de financiamiento hacia Venezuela reportados a UNOCHA "
            "FTS: quién dio, quién recibió, cuánto y dónde está en el proceso."
        ),
        # Página Acerca de
        "about_intro": (
            "El Navegador de Financiamiento para la Reconstrucción mapea de "
            "dónde viene el dinero de ayuda y reconstrucción para Venezuela, y "
            "si existe una ruta de cumplimiento de sanciones de EE. UU. para "
            "moverlo."
        ),
        "about_verified_h": "Qué significa “verificado”",
        "about_verified_body": (
            "Una ruta se marca como verificada solo tras una revisión humana "
            "del texto de la licencia y de la postura de cumplimiento del "
            "fondo, con un dictamen Verde, Amarillo o Rojo. Solo las rutas "
            "verificadas aparecen en la página de Rutas."
        ),
        "about_notverified_h": "Qué NO significa",
        "about_notverified_body": (
            "Todo en el Directorio de Financiamiento es una fuente investigada "
            "marcada “Ruta de cumplimiento en revisión”. No es un dictamen, ni "
            "asesoría legal, ni una determinación de OFAC. Es un recurso "
            "informativo; confirme su propio cumplimiento antes de mover fondos."
        ),
        "about_sources_h": "Fuentes de datos",
        "about_sources_body": (
            "Acciones Recientes de OFAC (licencias), UNOCHA FTS (flujos de "
            "financiamiento) y un directorio curado de fuentes investigadas, "
            "que incluye fondos comunitarios acreditados. Cada una enlaza a "
            "su página pública oficial."
        ),
        "about_cadence_h": "Frecuencia de actualización",
        "about_cadence_body": (
            "Las licencias y los flujos se actualizan desde sus APIs de origen; "
            "el directorio se verificó por última vez el {date}. El plan de "
            "respuesta revisado de OCHA se espera la semana del {ocha} y "
            "actualizará los totales rastreados."
        ),
        "about_contact_h": "Contacto",
        "about_contact_body": "Reporte un problema o sugiera una fuente:",
        "about_disclaimer_h": "Descargo de responsabilidad",
        "about_disclaimer_body": (
            "Este sitio constituye un esfuerzo voluntario de compilar "
            "información y enlaces sobre iniciativas de cooperación, "
            "asistencia humanitaria y financiamiento orientadas a la "
            "reconstrucción tras los terremotos en Venezuela, bajo el régimen "
            "de sanciones económicas vigente. La compilación se realiza "
            "mediante un motor de IA, seguida de una labor de verificación de "
            "cada iniciativa. Los responsables de este sitio no tienen "
            "vínculo alguno con las instituciones y organizaciones listadas, "
            "no participan en los proyectos indicados, y no se benefician en "
            "modo alguno de las contribuciones realizadas a través de las "
            "plataformas enlazadas. La verificación de fuentes y la "
            "clasificación de confiabilidad son aproximadas y no implican "
            "responsabilidad alguna de nuestra parte respecto a la "
            "administración de fondos donados ni a la gestión de los "
            "proyectos de ayuda."
        ),
        # Contactos del pie de página
        "footer_contacts_h": "CONTACTOS",
        "contact_maintainer": "Responsable del sitio: preguntas, correcciones, nuevas fuentes",
        "contact_ofac": "Consultas de sanciones y licencias OFAC (Tesoro de EE. UU.)",
        "contact_caf": "Contribuciones al Fondo de Reconstrucción CAF",
        "contact_fts": "Datos de flujos de financiamiento UNOCHA FTS",
        # Glosario (definiciones al pasar el cursor / tocar, ambos modos)
        "gl_mdb_term": "MDB (Banco Multilateral de Desarrollo)",
        "gl_mdb_def": (
            "Un banco propiedad de varios gobiernos, como CAF o el BID. "
            "Financia proyectos de desarrollo y reconstrucción."
        ),
        "gl_ingo_term": "INGO (ONG internacional)",
        "gl_ingo_def": (
            "Una organización no gubernamental que trabaja en muchos países, "
            "por ejemplo el International Rescue Committee o Save the "
            "Children."
        ),
        # Rutas simples — portada por intención
        "home_welcome_eyebrow": "Le damos la bienvenida",
        "home_welcome_lead": (
            "El propósito de esta iniciativa independiente es poner a su "
            "disposición información sobre los recursos disponibles para "
            "contribuir a las labores de rescate y recuperación de Venezuela "
            "luego del devastador terremoto del {date}. Aquí podrá encontrar "
            "información actualizada sobre:"
        ),
        "home_welcome_a_h": "Donaciones",
        "home_welcome_a": (
            "Formas de realizar donaciones efectivas a instituciones "
            "multilaterales, organizaciones nacionales y ONG que trabajan "
            "sobre el terreno u ofrecen vías para canalizar su ayuda "
            "monetaria."
        ),
        "home_welcome_b_h": "Transferencias de dinero",
        "home_welcome_b": (
            "Mecanismos habilitados para realizar transferencias de dinero a "
            "personas y familias particulares (distinto de donaciones, y no "
            "apto para transacciones comerciales)."
        ),
        "intent_heading": "¿Cómo quiere ayudar?",
        "intent_sub": (
            "Elija la opción que corresponda a su caso. Le mostramos solo lo "
            "necesario, en lenguaje claro."
        ),
        "intent_donate_t": "Quiero donar",
        "intent_donate_d": (
            "Opciones confiables para donar dinero al alivio del terremoto."
        ),
        "intent_remit_t": "Quiero enviar dinero a mi familia",
        "intent_remit_d": (
            "Qué está permitido ahora, qué canales funcionan y qué evitar."
        ),
        "intent_full_link": "O explore el navegador completo ↓",
        "simple_disclaimer": (
            "Información general, no asesoría legal. Para su situación "
            "específica, busque asesoría profesional autorizada."
        ),
        # Ruta de envío de dinero
        "rem_title": "Enviar dinero a su familia en Venezuela",
        "rem_intro": (
            "Qué está permitido ahora mismo, en lenguaje claro. Esta página "
            "trata de transferencias personales a familiares, no de pagos "
            "comerciales ni donaciones."
        ),
        "rem_q1_h": "¿Puedo enviar dinero ahora?",
        "rem_q1_a": "Sí, en la mayoría de los casos.",
        "rem_q1_body": (
            "Las transferencias personales, no comerciales, a familiares en "
            "Venezuela están generalmente permitidas. Una autorización de "
            "EE. UU. ({gl}) permite los servicios financieros de los que "
            "dependen estas transferencias, incluidas las operaciones con "
            "ciertos bancos venezolanos."
        ),
        "rem_q2_h": "¿Qué canales puedo usar?",
        "rem_q2_b1": (
            "Transferencias bancarias a cuentas en los cuatro bancos que "
            "cubre la GL 57: Banco Central de Venezuela, Banco de Venezuela, "
            "Banco Digital de los Trabajadores y Banco del Tesoro, más las "
            "entidades con 50 % o más de propiedad de esos bancos."
        ),
        "rem_q2_b2": (
            "Servicios de envío de dinero con licencia que operan hacia "
            "Venezuela. Verifique que el servicio tenga licencia donde usted "
            "vive antes de enviar."
        ),
        "rem_q2_note": (
            "Las transferencias a cuentas en otros bancos venezolanos, "
            "incluidos bancos privados como Banesco, Mercantil o BOD, no "
            "están cubiertas por la GL 57. Si no sabe con seguridad qué banco "
            "usa su familia, busque asesoría profesional antes de enviar."
        ),
        "rem_q3_h": "¿Hay una fecha límite?",
        "rem_q3_noexp": (
            "{gl} no tiene fecha de vencimiento declarada, pero las "
            "autorizaciones de EE. UU. pueden cambiar o retirarse con poco "
            "aviso. Si planea una transferencia grande, no asuma que las "
            "reglas de hoy se mantendrán indefinidamente."
        ),
        "rem_q3_exp": (
            "{gl} vence actualmente el {date}. Después de esa fecha las "
            "reglas pueden cambiar. Verifique antes de enviar."
        ),
        "rem_q4_h": "¿Qué debo evitar?",
        "rem_q4_b1": (
            "Enviar dinero a cualquier persona en una lista de sanciones de "
            "EE. UU., o a entidades del gobierno venezolano."
        ),
        "rem_q4_b2": (
            "Disfrazar pagos comerciales como apoyo familiar. Solo las "
            "transferencias personales, no comerciales, están cubiertas."
        ),
        "rem_q4_b3": (
            "Redes informales de envío sin licencia. No tiene ninguna "
            "protección si el dinero desaparece."
        ),
        "rem_license_link": "Detalles completos de la licencia →",
    },
}

SECTOR_ES = {
    "Healthcare": "Salud",
    "Infrastructure": "Infraestructura",
    "WASH": "WASH",
    "Housing": "Vivienda",
    "Energy": "Energía",
    "Education": "Educación",
}
CAPITAL_ES = {
    "Grant": "Subvención",
    "Concessional Loan": "Préstamo Concesional",
    "Commercial Debt": "Deuda Comercial",
    "Blended Finance": "Financiamiento Combinado",
}
VERDICT_STYLE = {
    "green": ("#E7F4EC", "#146C43", "#B7E0C6"),
    "yellow": ("#FBF3D9", "#8A6100", "#F0DFA8"),
    "red": ("#FBE7E7", "#9B1C1C", "#F1C3C3"),
}
STATUS_ES = {
    "Pledged": "Prometido",
    "Committed": "Comprometido",
    "Disbursed": "Desembolsado",
}

# Focus-area (sector) pills and capital-type list for the design pill rows.
SECTORS = ["Healthcare", "Infrastructure", "Housing", "WASH", "Energy"]
CAPITAL_TYPES = ["Grant", "Blended Finance", "Concessional Loan", "Commercial Debt"]

# Audience layer derived from org_type (so a diaspora user, an NGO and an
# institutional funder each get their own filter). Not in the JSON — a curated
# grouping of the raw org_type tags.
ORG_LAYER = {
    "multilateral_development_bank": "institutional",
    "un_pooled_fund": "institutional",
    "un_agency": "institutional",
    "un_coordination": "institutional",
    "government_donor": "institutional",
    "sovereign_multilateral": "institutional",
    "grantmaker": "institutional",
    "ingo": "ngo",
    "faith_based_ingo": "ngo",
    "ingo_coalition": "ngo",
    "logistics_ngo": "ngo",
    "local_venezuelan_ngo": "ngo",
    "red_cross_movement": "ngo",
    "diaspora_ngo": "diaspora",
    "community_fund": "community",
    "regranting_platform": "platform",
    "crowdfunding_platform": "platform",
}

# flow_direction → (badge string key, whether it counts as GIVE / APPLY)
FLOW_BADGE = {
    "accepts_contributions": "flow_give_badge",
    "grants_to_ngos": "flow_apply_badge",
    "both": "flow_both_badge",
    "direct_to_beneficiaries": "flow_direct_badge",
    "government_resource": "flow_gov_badge",
    "sovereign_financing": "flow_gov_badge",
    "directory": "flow_directory_badge",
    "pipeline": "flow_pipeline_badge",
}
FLOW_GIVE = {"accepts_contributions", "both", "direct_to_beneficiaries"}
FLOW_APPLY = {"grants_to_ngos", "both"}

# ---------------------------------------------------------------------------
# Simple paths (Donate / Send money / Volunteer) — plain-language views of the
# same directory + license data the advanced pages use. No new content lives
# here except the plain-language phrasing.
# ---------------------------------------------------------------------------

# Glossary: acronym → (term string key, definition string key). Rendered by
# gloss() as a hover/tap tooltip. Shared across simple AND advanced modes.
GLOSSARY = {
    "OFAC": ("gl_ofac_term", "gl_ofac_def"),
    "GL": ("gl_gl_term", "gl_gl_def"),
    "MDB": ("gl_mdb_term", "gl_mdb_def"),
    "INGO": ("gl_ingo_term", "gl_ingo_def"),
}

CURRENCY_SYMBOLS = config.CURRENCY_SYMBOLS


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------

def _get_lang() -> str:
    value = st.query_params.get("lang")
    if isinstance(value, list):
        value = value[0] if value else None
    if value not in SUPPORTED_LANGS:
        value = st.session_state.get("lang", DEFAULT_LANG)
    return value if value in SUPPORTED_LANGS else DEFAULT_LANG


def _localize_sector(name: str, lang: str) -> str:
    return SECTOR_ES.get(name, name) if lang == "es" else name


def _localize_capital(name: str, lang: str) -> str:
    return CAPITAL_ES.get(name, name) if lang == "es" else name


def _localize_status(name: str, lang: str) -> str:
    return STATUS_ES.get(name, name) if lang == "es" else name


def _parse_date(value: object) -> date | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _is_expiring_soon(value: object, *, days: int = EXPIRY_WARNING_DAYS) -> bool:
    exp = _parse_date(value)
    if exp is None:
        return False
    today = date.today()
    return today <= exp <= today + timedelta(days=days)


def _fmt_usd(amount: object) -> str:
    try:
        value = float(amount)
    except (TypeError, ValueError):
        return "—"
    if value <= 0:
        return "—"
    if value >= 1_000_000:
        return f"${value / 1_000_000:,.1f}M"
    if value >= 1_000:
        return f"${value / 1_000:,.0f}K"
    return f"${value:,.0f}"


def _fmt_scaled(value: float, symbol: str) -> str:
    if value >= 1_000_000_000:
        return f"{symbol}{value / 1_000_000_000:,.1f}B"
    if value >= 1_000_000:
        return f"{symbol}{value / 1_000_000:,.1f}M"
    if value >= 1_000:
        return f"{symbol}{value / 1_000:,.0f}K"
    return f"{symbol}{value:,.0f}"


def _fmt_amount(currency: str, original: object, usd: object) -> str:
    """Display a funding amount.

    Non-USD entries show the source figure (e.g. £7.0M) followed by the
    converted USD labelled with ≈. USD entries just show the dollar figure.
    """
    symbol = CURRENCY_SYMBOLS.get(currency, "")
    try:
        orig_val = float(original) if original not in (None, "") else None
    except (TypeError, ValueError):
        orig_val = None
    usd_str = _fmt_usd(usd)
    if currency and currency != "USD" and orig_val:
        native = _fmt_scaled(orig_val, symbol)
        if usd_str != "—":
            return f"{native} (≈{usd_str})"
        return native
    return usd_str


# Authoritative external destinations for otherwise-dead links.
OFAC_URL = config.OFAC_RECENT_ACTIONS_URL
FTS_URL = "https://fts.unocha.org/countries/242/summary/2026"

# Every OUTBOUND link must carry this. Internal links stay same-tab, but when
# the app itself is viewed inside an iframe (e.g. Streamlit Cloud's embedded
# viewer), a target-less external link navigates the iframe — and most org
# sites send X-Frame-Options: DENY, which renders as "refused to connect".
EXT = 'target="_blank" rel="noopener noreferrer"'


def _mailto(kind: str) -> str:
    subjects = {
        "subscribe": "Subscribe: OFAC license & funding alerts",
        "report": "Reconstruction Finance Navigator: report an issue or suggest a source",
    }
    subject = quote(subjects.get(kind, subjects["report"]))
    return f"mailto:{CONTACT_EMAIL}?subject={subject}"


def gloss(c: "Ctx", term: str, label: str | None = None) -> str:
    """An acronym with a hover/tap definition (shared glossary component).

    `term` is a GLOSSARY key (OFAC, GL, MDB, INGO); `label` is the visible
    text (e.g. "GL 60" glossed under the GL definition). Returns an inline
    HTML span — inject it into already-escaped copy, never escape() it again.
    Tooltip styling lives in _BASE_CSS (.gl-term).
    """
    term_key, def_key = GLOSSARY[term]
    tip = f"{c.t(term_key)}: {c.t(def_key)}"
    return (
        f'<span class="gl-term" tabindex="0" data-tip="{escape(tip)}">'
        f"{escape(label or term)}</span>"
    )


# URL path for each page (Home is served at root). Keep in sync with app.py.
PAGE_SLUGS = {
    "home": "",
    "licenses": "licenses",
    "pathways": "pathways",
    "directory": "directory",
    "capital": "capital-stack",
    "about": "about",
    "admin": "admin",
    "remit": "send-money",
}

# Top-level header nav (five is the ceiling). Home reached via the logo,
# About lives in the footer.
HEADER_NAV = [
    ("licenses", "nav_licenses"),
    ("pathways", "nav_pathways"),
    ("directory", "nav_directory"),
    ("capital", "nav_capital"),
]

class Ctx:
    """Language + query-param aware render context, bound to the active page."""

    # Query params carried across links (per-page filters + detail routing).
    _NAV_PARAMS = (
        "lang", "auth", "cap", "fd", "ph", "ot", "gl", "source", "pathway",
    )

    def __init__(self, active: str = "home") -> None:
        self.active = active
        self.lang = _get_lang()
        self.bundle = STRINGS[self.lang]
        # SPA page_link navigation drops query params — fall back to the
        # session copy (set in app.py) so the admin session survives.
        self.auth = self._q("auth") or st.session_state.get("auth")
        self.cap = self._q("cap")           # capital-stack type filter
        self.fd = self._q("fd")             # directory money direction
        self.ph = self._q("ph")             # directory phase
        self.ot = self._q("ot")             # directory audience layer
        self.gl = self._q("gl")             # pathways license filter
        self.source = self._q("source")     # directory detail
        self.pathway = self._q("pathway")   # pathways detail

    @staticmethod
    def _q(key: str) -> str | None:
        value = st.query_params.get(key)
        if isinstance(value, list):
            value = value[0] if value else None
        return value

    def t(self, key: str, **kw: object) -> str:
        template = self.bundle.get(key) or STRINGS["en"].get(key, key)
        return template.format(**kw) if kw else template

    def _base_params(self) -> dict[str, object]:
        """Params that must persist across ALL links so state never resets."""
        params = {"lang": self.lang}
        if self.auth:
            params["auth"] = self.auth
        return params

    def page_url(self, slug: str, *, anchor: str | None = None, **extra: object) -> str:
        """Cross-page link to `slug`, carrying lang + auth + any extras.

        This is the single link builder every internal link must use so the
        language and admin session never silently drop.
        """
        params = self._base_params()
        for k, v in extra.items():
            if v is not None:
                params[k] = v
        path = "/" + PAGE_SLUGS.get(slug, "")
        query = "&".join(f"{k}={quote(str(v), safe='')}" for k, v in params.items())
        url = f"{path}?{query}" if query else path
        return f"{url}#{anchor}" if anchor else url

    def nav_link(self, slug: str, label: str, active: bool = False, **extra: object) -> str:
        color = INK if active else MUTE
        weight = "700" if active else "600"
        border = f"border-bottom:2px solid {RED};" if active else ""
        return (
            f'<a href="{self.page_url(slug, **extra)}" style="text-decoration:none;'
            f'font-size:13px;font-weight:{weight};color:{color};{border}'
            f'padding-bottom:2px;">{escape(label)}</a>'
        )

    def href(self, **overrides: object) -> str:
        """Self-link to the CURRENT page, preserving its params, with overrides."""
        current = {p: getattr(self, p, None) for p in self._NAV_PARAMS}
        current.update(overrides)
        params = {k: v for k, v in current.items() if v}
        path = "/" + PAGE_SLUGS.get(self.active, "")
        query = "&".join(f"{k}={quote(str(v), safe='')}" for k, v in params.items())
        return f"{path}?{query}" if query else path

    def filter_href(self, **overrides: object) -> str:
        """Directory/stack filter link on the current page (clears any detail)."""
        overrides.setdefault("source", None)
        overrides.setdefault("pathway", None)
        return self.href(**overrides)

    def detail_href(self, *, source: str | None = None, pathway: object = None) -> str:
        return self.href(source=source, pathway=pathway)


# ---------------------------------------------------------------------------
# Section builders (return HTML strings)
# ---------------------------------------------------------------------------

def _flag_stripe(height: int = 5, radius: int = 0) -> str:
    r = f"border-radius:{radius}px;overflow:hidden;" if radius else ""
    return (
        f'<div style="display:flex;height:{height}px;width:100%;{r}">'
        f'<div style="flex:1;background:{YELLOW};"></div>'
        f'<div style="flex:1;background:{BLUE};"></div>'
        f'<div style="flex:1;background:{RED};"></div></div>'
    )


# (The old HTML _header was replaced by _render_header — widget-based nav with
# client-side page transitions. See the "Page" section near the bottom.)


def _hero(c: Ctx) -> str:
    return (
        '<section style="position:relative;min-height:460px;display:flex;'
        'flex-direction:column;justify-content:flex-end;background:linear-gradient('
        f'160deg,{DARK_BLUE} 0%,{BLUE} 45%,#0a3a8f 75%,{DARK_RED} 100%);'
        'overflow:hidden;">'
        '<div style="position:absolute;inset:0;background-image:repeating-linear-gradient('
        '115deg,rgba(255,255,255,0.05) 0px,rgba(255,255,255,0.05) 2px,transparent 2px,'
        'transparent 26px);opacity:0.6;"></div>'
        '<div style="position:absolute;top:22px;right:48px;font:600 10px/1.4 '
        'ui-monospace,monospace;color:rgba(255,255,255,0.55);letter-spacing:0.06em;'
        f'text-align:right;max-width:240px;">{escape(c.t("hero_photo"))}</div>'
        '<div style="position:relative;padding:64px 48px 40px;max-width:900px;">'
        '<h1 style="margin:0;font-size:46px;font-weight:800;line-height:1.12;'
        'letter-spacing:-0.01em;color:#FFFFFF;">'
        f'{escape(c.t("hero_title_l1"))}<br/>{escape(c.t("hero_title_l2"))}</h1>'
        '<p style="margin:20px 0 0;max-width:620px;font-size:18px;line-height:1.55;'
        f'color:rgba(255,255,255,0.88);">{escape(c.t("app_subtitle"))}</p></div>'
        '<div style="position:relative;display:flex;justify-content:flex-end;'
        'padding:0 48px 36px;">'
        f'<a href="{c.href()}#pathways" style="text-decoration:none;background:{YELLOW};'
        f'color:{INK};padding:16px 30px;border-radius:999px;font-size:15px;'
        f'font-weight:700;">{escape(c.t("hero_cta"))}</a></div></section>'
    )


def _context_bar(c: Ctx, tracked_usd: float) -> str:
    """UN reconstruction estimate vs tracked — the credibility framing."""
    est = _fmt_scaled(config.UN_RECONSTRUCTION_ESTIMATE_USD, "$")
    tracked = f"≈{_fmt_usd(tracked_usd)}" if tracked_usd else "—"
    pin = f"{config.PEOPLE_IN_NEED_EARTHQUAKE / 1_000_000:.1f}M"

    def stat(value: str, label: str, accent: str) -> str:
        return (
            '<div style="flex:1 1 200px;">'
            f'<div style="font-size:24px;font-weight:800;color:{accent};">{escape(value)}</div>'
            f'<div style="font-size:12px;font-weight:600;letter-spacing:0.04em;'
            f'text-transform:uppercase;color:rgba(255,255,255,0.6);margin-top:4px;">'
            f'{escape(label)}</div></div>'
        )
    return (
        f'<section style="background:{INK};padding:26px 48px;display:flex;gap:32px;'
        'flex-wrap:wrap;align-items:center;">'
        + stat(est, c.t("context_estimate"), "#FFF")
        + stat(tracked, c.t("context_tracked"), YELLOW)
        + stat(pin, c.t("context_in_need"), "#FFF")
        + '<div style="flex:2 1 300px;font-size:13px;line-height:1.5;'
        'color:rgba(255,255,255,0.72);">'
        + escape(c.t("context_gap_note", tracked=tracked, estimate=est))
        + "</div></section>"
    )


def _license_cards(c: Ctx, licenses: list[dict]) -> str:
    label = (
        '<div style="display:flex;align-items:center;gap:18px;margin-bottom:26px;">'
        '<span style="font-size:12px;font-weight:700;letter-spacing:0.1em;'
        f'color:{INK};white-space:nowrap;">{escape(c.t("stories_label"))}</span>'
        '<div style="height:1px;background:#D8D5CC;flex:1;"></div></div>'
    )
    if not licenses:
        body = f'<p style="font-size:14px;color:{MUTE};">{escape(c.t("lic_none"))}</p>'
        return f'<section style="padding:44px 48px 8px;">{label}{body}</section>'

    cards = []
    for lic in licenses[:3]:
        status = (lic.get("status") or "").lower()
        expired = status in ("expired", "revoked")
        expiring = status == "expiring soon" or _is_expiring_soon(lic.get("expiration_date"))
        acts = lic.get("activities") or []
        activities = ", ".join(acts)
        if len(activities) > 60:  # keep card headlines tight
            activities = activities[:57].rstrip(", ") + "…"
        activities = activities or "—"
        if expired:
            tag, tag_color, swatch = c.t("lic_tag_expired"), "#9B1C1C", DARK_RED
            suffix = c.t("lic_expired_suffix")
        elif expiring:
            tag, tag_color, swatch = c.t("lic_tag_expiring"), "#8A6100", "#0a3a8f"
            suffix = c.t("lic_authorized")
        else:
            tag, tag_color, swatch = c.t("lic_tag_active"), "#146C43", BLUE
            suffix = c.t("lic_authorized")
        headline = f"{activities} {suffix}"
        cards.append(
            '<div style="display:flex;gap:16px;flex:1 1 260px;max-width:320px;">'
            f'<div style="width:96px;height:72px;flex:none;border-radius:4px;'
            f'background:{swatch};display:flex;align-items:center;justify-content:center;'
            f'font:700 20px/1 \'Open Sans\';color:rgba(255,255,255,0.9);">'
            f'{escape(lic.get("license_id") or "")}</div>'
            '<div>'
            f'<div style="font-size:17px;font-weight:700;line-height:1.3;color:{BLUE};">'
            f'{escape(headline)}</div>'
            f'<div style="margin-top:8px;font-size:11px;font-weight:700;'
            f'letter-spacing:0.06em;color:{tag_color};">{escape(tag)}</div></div></div>'
        )
    grid = (
        '<div style="display:flex;gap:32px;flex-wrap:wrap;">' + "".join(cards) + "</div>"
    )
    return f'<section style="padding:44px 48px 8px;">{label}{grid}</section>'


def _pill_row(items: list[str]) -> str:
    pills = "".join(
        '<span style="border:1px solid #D8D5CC;border-radius:999px;padding:7px 14px;'
        f'font-size:12.5px;font-weight:600;color:{INK};">{escape(x)}</span>'
        for x in items
    )
    return f'<div style="display:flex;flex-wrap:wrap;gap:8px;">{pills}</div>'


def _data_compliance(c: Ctx) -> str:
    left = (
        '<div style="flex:0 0 340px;">'
        '<div style="font-size:30px;font-weight:800;letter-spacing:-0.01em;line-height:1.15;">'
        f'<span style="color:{RED};">{escape(c.t("data_kicker"))}</span> '
        f'{escape(c.t("data_heading"))}</div>'
        f'<p style="margin:16px 0 24px;font-size:15px;line-height:1.6;color:{MUTE};'
        f'max-width:320px;">{escape(c.t("data_body"))}</p>'
        f'<a href="{c.href()}#pathways" style="text-decoration:none;display:inline-block;'
        f'background:{BLUE};color:#FFF;padding:13px 24px;border-radius:999px;'
        f'font-size:14px;font-weight:700;margin-bottom:28px;">{escape(c.t("data_cta"))}</a>'
        f'<div style="font-size:13px;font-weight:600;color:{INK};margin-bottom:10px;">'
        f'{escape(c.t("explore_focus"))}</div>'
        + _pill_row([_localize_sector(s, c.lang) for s in SECTORS])
        + "</div>"
    )
    glossary_items = [
        (c.t("gl_source_ofac"), c.t("gl_ofac_term"), c.t("gl_ofac_def")),
        (c.t("gl_source_glossary"), c.t("gl_gl_term"), c.t("gl_gl_def")),
    ]
    cards = "".join(
        '<div style="flex:1 1 220px;border:1px solid #E1DFD8;border-radius:4px;'
        'padding:20px;min-width:220px;background:#FBFAF7;">'
        f'<div style="font-size:11px;font-weight:700;color:#9CA3AF;letter-spacing:0.04em;">'
        f'{escape(src)}</div>'
        f'<div style="margin-top:40px;font-size:15px;font-weight:700;color:{BLUE};">'
        f'{escape(term)}</div>'
        f'<p style="margin:8px 0 0;font-size:13px;line-height:1.55;color:{MUTE};">'
        f'{escape(defn)}</p></div>'
        for src, term, defn in glossary_items
    )
    right = f'<div style="flex:1;display:flex;gap:20px;flex-wrap:wrap;">{cards}</div>'
    return (
        '<section style="display:flex;gap:40px;padding:64px 48px;align-items:flex-start;'
        f'flex-wrap:wrap;">{left}{right}</section>'
    )


def _signup(c: Ctx) -> str:
    return (
        f'<section style="background:#F2EFEA;padding:44px 48px;display:flex;gap:40px;'
        'align-items:center;flex-wrap:wrap;">'
        '<div style="flex:1 1 320px;font-size:22px;font-weight:800;line-height:1.3;'
        'text-transform:uppercase;">'
        f'{escape(c.t("signup_l1"))} <span style="color:{RED};">'
        f'{escape(c.t("signup_bold"))}</span></div>'
        '<div style="flex:2 1 420px;">'
        '<div style="display:flex;border:1px solid #B9B6AC;border-radius:4px;'
        'overflow:hidden;background:#FFF;">'
        f'<input placeholder="{escape(c.t("signup_email"))}" style="flex:1;border:none;'
        'padding:14px 16px;font-size:14px;font-family:inherit;outline:none;"/>'
        f'<input placeholder="{escape(c.t("signup_org"))}" style="flex:1;border:none;'
        'border-left:1px solid #E1DFD8;padding:14px 16px;font-size:14px;'
        'font-family:inherit;outline:none;"/></div>'
        '<label style="display:flex;align-items:flex-start;gap:8px;margin-top:10px;'
        f'font-size:11.5px;color:{MUTE};line-height:1.4;">'
        '<input type="checkbox" style="margin-top:2px;"/> '
        f'{escape(c.t("signup_consent"))}</label>'
        f'<a href="{_mailto("subscribe")}" style="text-decoration:none;display:inline-block;'
        f'margin-top:14px;background:{BLUE};color:#FFF;'
        'padding:12px 26px;border-radius:999px;font-size:14px;font-weight:700;">'
        f'{escape(c.t("signup_button"))}</a></div></section>'
    )


def _feature_cards(c: Ctx, pathways: list[dict]) -> str:
    green = next(
        (p for p in pathways if (p.get("compliance_verdict") or "").lower() == "green"),
        None,
    )
    red = next(
        (p for p in pathways if (p.get("compliance_verdict") or "").lower() == "red"),
        None,
    )
    if green:
        green_text = c.t(
            "feature_green_tmpl",
            fund=green.get("fund_name") or "",
            license=green.get("license_id") or "",
        )
    else:
        green_text = c.t("feature_green_fallback")
    if red:
        status = (red.get("license_status") or "").lower() or "expired"
        red_text = c.t(
            "feature_red_tmpl",
            fund=red.get("fund_name") or "",
            license=red.get("license_id") or "",
            status=status,
        )
    else:
        red_text = c.t("feature_red_fallback")

    def card(bg: str, pill_bg: str, pill_col: str, label: str, text: str,
             pathway: dict | None) -> str:
        tag = "a" if pathway else "div"
        href = (
            f' href="{c.detail_href(pathway=pathway.get("map_id"))}"'
            if pathway else ""
        )
        return (
            f'<{tag}{href} style="text-decoration:none;flex:1 1 320px;background:{bg};'
            'border-radius:4px;padding:28px;min-height:150px;display:flex;'
            'flex-direction:column;justify-content:space-between;">'
            f'<span style="display:inline-block;align-self:flex-start;background:{pill_bg};'
            f'color:{pill_col};border-radius:999px;padding:4px 12px;font-size:11px;'
            f'font-weight:700;">{escape(label)}</span>'
            f'<div style="color:#FFF;font-size:17px;font-weight:700;line-height:1.4;'
            f'margin-top:16px;">{escape(text)}</div></{tag}>'
        )

    return (
        '<div style="display:flex;gap:24px;margin-bottom:40px;flex-wrap:wrap;">'
        + card(DARK_BLUE, "#E7F4EC", "#146C43", c.t("verdict_green"), green_text, green)
        + card(DARK_RED, "#FBE7E7", "#9B1C1C", c.t("verdict_red"), red_text, red)
        + "</div>"
    )


def _pathways_table(c: Ctx, pathways: list[dict]) -> str:
    cols = "1.6fr 1fr 1.3fr 0.8fr 1fr 0.8fr"
    headers = [
        c.t("nav_navigator") if False else ("Fondo" if c.lang == "es" else "Fund Name"),
        "Tipo de Capital" if c.lang == "es" else "Capital Type",
        "Sectores" if c.lang == "es" else "Sectors",
        "Licencia" if c.lang == "es" else "License",
        "Vencimiento" if c.lang == "es" else "Expiration",
        "Dictamen" if c.lang == "es" else "Verdict",
    ]
    head = (
        f'<div style="display:grid;grid-template-columns:{cols};gap:0 18px;'
        'border-bottom:1px solid #E1DFD8;padding-bottom:10px;">'
        + "".join(
            '<div style="font-size:11px;font-weight:700;letter-spacing:0.08em;'
            'text-transform:uppercase;color:#9CA3AF;white-space:nowrap;">'
            f'{escape(h)}</div>'
            for h in headers
        )
        + "</div>"
    )
    rows_html = []
    for p in pathways:
        exp = _parse_date(p.get("expiration_date"))
        exp_str = exp.isoformat() if exp else "—"
        soon = _is_expiring_soon(exp)
        exp_color = "#9A3412" if soon else MUTE
        exp_weight = "700" if soon else "400"
        verdict = (p.get("compliance_verdict") or "").strip()
        vkey = verdict.lower()
        vbg, vcol, vborder = VERDICT_STYLE.get(vkey, ("#F1F3F5", MUTE, "#E2E5E9"))
        vlabel = c.t(f"verdict_{vkey}") if vkey in ("green", "yellow", "red") else (verdict or "—")
        sectors = ", ".join(
            _localize_sector(s, c.lang) for s in (p.get("target_sectors") or [])
        ) or "—"
        row_href = c.detail_href(pathway=p.get("map_id"))
        rows_html.append(
            f'<a href="{row_href}" class="row-link" '
            f'style="text-decoration:none;display:grid;grid-template-columns:{cols};'
            'gap:0 18px;align-items:center;border-bottom:1px solid #EFEDE8;padding:16px 0;">'
            f'<div style="font-weight:700;color:{BLUE};">{escape(p.get("fund_name") or "—")}</div>'
            f'<div style="color:{MUTE};">{escape(_localize_capital(p.get("capital_type") or "", c.lang)) or "—"}</div>'
            f'<div style="color:{MUTE};">{escape(sectors)}</div>'
            f'<div style="color:{INK};">{escape(p.get("license_id") or "—")}</div>'
            f'<div style="color:{exp_color};font-weight:{exp_weight};">{escape(exp_str)}</div>'
            f'<div><span style="background:{vbg};color:{vcol};border:1px solid {vborder};'
            f'border-radius:999px;padding:3px 12px;font-size:12px;font-weight:700;'
            f'white-space:nowrap;">{escape(vlabel)}</span></div></a>'
        )
    table = (
        '<div style="overflow-x:auto;"><div style="min-width:760px;">'
        + head + "".join(rows_html) + "</div></div>"
    )
    return table


def _pathways_section(c: Ctx, pathways: list[dict]) -> str:
    header = (
        '<div style="display:flex;justify-content:space-between;align-items:baseline;'
        'margin-bottom:28px;">'
        '<div style="font-size:28px;font-weight:800;letter-spacing:-0.01em;">'
        f'<span style="color:{RED};">{escape(c.t("pathways_kicker"))}</span> '
        f'{escape(c.t("pathways_heading"))}</div>'
        f'<a href="{c.href()}#pathways" style="text-decoration:none;background:{BLUE};'
        'color:#FFF;padding:11px 22px;border-radius:999px;font-size:13px;font-weight:700;'
        f'white-space:nowrap;">{escape(c.t("pathways_more"))}</a></div>'
    )
    if not pathways:
        body = (
            _feature_cards(c, pathways)
            + f'<p style="margin:0;font-size:14px;color:{MUTE};">'
            f'{escape(c.t("pathways_empty"))}</p>'
        )
        return (
            '<section id="pathways" style="padding:64px 48px 20px;">'
            f"{header}{body}</section>"
        )
    note = (
        f'<p style="margin:0 0 18px;font-size:13px;color:{MUTE};max-width:640px;'
        f'line-height:1.5;">{escape(c.t("pathways_note"))}</p>'
    )
    footer = (
        f'<p style="margin:14px 0 0;font-size:12.5px;color:#9CA3AF;">'
        f'{escape(c.t("rows_shown", count=len(pathways)))}</p>'
    )
    return (
        '<section id="pathways" style="padding:64px 48px 20px;">'
        f"{header}{_feature_cards(c, pathways)}{note}"
        f"{_pathways_table(c, pathways)}{footer}</section>"
    )


def _metrics_section(c: Ctx, pathways: list[dict]) -> str:
    active_funds = len({p["fund_name"] for p in pathways if p.get("fund_name")})
    expiring = len(
        {
            p["license_id"]
            for p in pathways
            if p.get("license_id") and _is_expiring_soon(p.get("expiration_date"))
        }
    )
    metrics = [
        (str(active_funds), c.t("metric_active_funds")),
        (str(expiring), c.t("metric_expiring")),
        (str(len(pathways)), c.t("metric_pathways")),
    ]
    metric_html = "".join(
        f'<div style="border-left:3px solid {BLUE};padding-left:16px;">'
        f'<div style="font-size:30px;font-weight:800;color:{INK};">{escape(v)}</div>'
        f'<div style="font-size:13.5px;color:{MUTE};margin-top:2px;">{escape(lbl)}</div></div>'
        for v, lbl in metrics
    )
    photo = (
        '<div style="flex:1 1 340px;height:300px;border-radius:4px;background:'
        'repeating-linear-gradient(135deg,#F2EFEA 0px,#F2EFEA 14px,#E7E4DC 14px,'
        '#E7E4DC 28px);display:flex;align-items:center;justify-content:center;'
        'font:600 12px ui-monospace,monospace;color:#9CA3AF;text-align:center;'
        f'padding:20px;">{escape(c.t("power_photo"))}</div>'
    )
    right = (
        '<div style="flex:1 1 380px;">'
        '<div style="font-size:26px;font-weight:800;letter-spacing:-0.01em;">'
        f'<span style="color:{RED};">{escape(c.t("power_kicker"))}</span> '
        f'{escape(c.t("power_heading"))}</div>'
        f'<p style="margin:16px 0 28px;font-size:15px;line-height:1.65;color:{MUTE};'
        f'max-width:460px;">{escape(c.t("power_body"))}</p>'
        '<div style="display:flex;flex-direction:column;gap:20px;">'
        f'{metric_html}</div></div>'
    )
    return (
        '<section style="display:flex;gap:48px;padding:64px 48px;align-items:center;'
        f'flex-wrap:wrap;">{photo}{right}</section>'
    )


def _dark_banner(c: Ctx) -> str:
    def link(title: str, url: str) -> str:
        return (
            f'<a href="{escape(url)}" {EXT} '
            'style="text-decoration:none;display:block;">'
            '<div style="color:#FFF;font-size:14px;font-weight:700;">'
            f'{escape(title)}</div>'
            f'<div style="color:{YELLOW};font-size:13px;font-weight:700;margin-top:6px;">'
            f'{escape(c.t("learn_more"))} ↗</div></a>'
        )
    return (
        f'<section style="position:relative;background:{DARK_BLUE};padding:56px 48px;'
        'display:flex;align-items:center;gap:40px;overflow:hidden;flex-wrap:wrap;">'
        '<div style="flex:1 1 380px;z-index:1;">'
        '<div style="color:#FFF;font-size:24px;font-weight:800;line-height:1.3;'
        'text-transform:uppercase;">'
        f'{escape(c.t("banner_l1"))}<br/><span style="color:{YELLOW};">'
        f'{escape(c.t("banner_l2"))}</span></div>'
        '<p style="margin:16px 0 24px;color:rgba(255,255,255,0.75);font-size:14.5px;'
        f'line-height:1.6;max-width:460px;">{escape(c.t("banner_body"))}</p>'
        '<div style="display:flex;gap:40px;flex-wrap:wrap;">'
        f'{link(c.t("banner_link1_title"), OFAC_URL)}'
        f'{link(c.t("banner_link2_title"), FTS_URL)}</div></div>'
        '<div style="width:220px;height:220px;border-radius:50%;flex:none;background:'
        'repeating-linear-gradient(115deg,rgba(255,255,255,0.08) 0px,'
        'rgba(255,255,255,0.08) 2px,transparent 2px,transparent 20px),'
        f'radial-gradient(circle,{DARK_RED},#3a1010);"></div></section>'
    )


def _is_open_fund(f: dict) -> bool:
    """Open for applications vs already allocated to a partner.

    Every UNOCHA FTS row is a directed donor→recipient flow — an
    allocation — even when the recipient is confidential/cluster-level.
    Announced pools (CAF/IDB/State/ECHO) with no named recipient are what
    NGOs can apply to.
    """
    if (f.get("source_name") or "") == "UNOCHA FTS":
        return False
    return not (f.get("recipient_org") or "").strip()


def _fund_snippet(c: Ctx, f: dict) -> str:
    if _is_open_fund(f):
        sectors = ", ".join(
            _localize_sector(s, c.lang) for s in (f.get("target_sectors") or [])
        )
        badge = c.t("stack_open_badge")
        return f"{sectors} · {badge}" if sectors else badge

    # Allocated flow — show amount, the donor→recipient route, and status.
    recipient = (f.get("recipient_org") or "").strip()
    donor = (f.get("donor") or "").strip()
    amount = _fmt_usd(f.get("amount_usd"))
    status = _localize_status(f.get("status") or "", c.lang)
    parts: list[str] = []
    if amount != "—":
        parts.append(amount)
    if donor and recipient:
        parts.append(f"{donor} → {recipient}")
    elif donor:
        parts.append(donor)
    elif recipient:
        parts.append(recipient)
    if status:
        parts.append(status)
    return " · ".join(parts)


# Best-effort match from an FTS flow to a curated directory source_key, so a
# tracked flow can cross-link to its home in the Directory where one exists.
FTS_TO_DIRECTORY = {
    "venezuela humanitarian fund": "un-venezuela-humanitarian-fund",
    "world food programme": "wfp-food",
    "unicef": "unicef-earthquake-appeal",
    "united nations children": "unicef-earthquake-appeal",
    "international federation of red cross": "ifrc-emergency-appeal",
    "red cross": "ifrc-emergency-appeal",
}


def _match_directory(fund: dict, known: set[str]) -> str | None:
    blob = f"{fund.get('fund_name', '')} {fund.get('recipient_org', '')}".lower()
    for kw, key in FTS_TO_DIRECTORY.items():
        if kw in blob and key in known:
            return key
    return None


def capital_filter_options(c: Ctx, funds: list[dict]) -> list[tuple[str, object]]:
    """Options for the capital-type pills widget (rendered by the page)."""
    present = [ct for ct in CAPITAL_TYPES if any(f.get("capital_type") == ct for f in funds)]
    return [(c.t("cap_all"), None)] + [
        (_localize_capital(ct, c.lang), ct) for ct in present
    ]


def _capital_stack(c: Ctx, funds: list[dict], known_sources: set[str] | None = None) -> str:
    known_sources = known_sources or set()
    # Filter + sort funds (the capital-type pills are a widget on the page).
    shown = [f for f in funds if not c.cap or f.get("capital_type") == c.cap]
    shown.sort(key=lambda f: (f.get("amount_usd") or 0), reverse=True)
    total = sum(f.get("amount_usd") or 0 for f in funds)

    left = (
        '<div style="flex:1 1 300px;">'
        '<div style="width:100%;height:220px;border-radius:4px;background:'
        'repeating-linear-gradient(135deg,#F2EFEA 0px,#F2EFEA 14px,#E7E4DC 14px,'
        '#E7E4DC 28px);display:flex;align-items:center;justify-content:center;'
        'font:600 12px ui-monospace,monospace;color:#9CA3AF;text-align:center;'
        f'margin-bottom:24px;padding:20px;">{escape(c.t("stack_photo"))}</div>'
        '<div style="font-size:24px;font-weight:800;letter-spacing:-0.01em;line-height:1.25;">'
        f'<span style="color:{RED};">{escape(c.t("stack_kicker"))}</span> '
        f'{escape(c.t("stack_heading"))}</div>'
        f'<a href="{c.page_url("directory")}" style="text-decoration:none;'
        f'display:inline-block;font-size:13px;font-weight:700;color:{BLUE};margin:18px 0 4px;">'
        f'{escape(c.t("stack_seeall"))} →</a>'
        f'<div style="font-size:12px;color:#9CA3AF;margin-bottom:4px;">'
        f'{escape(c.t("stack_total", total="≈" + _fmt_usd(total), count=len(funds)))}</div>'
        f'<div style="font-size:12px;color:#9CA3AF;margin-bottom:14px;">'
        f'{escape(c.t("context_estimate"))}: '
        f'~{_fmt_scaled(config.UN_RECONSTRUCTION_ESTIMATE_USD, "$")}</div></div>'
    )

    if not shown:
        articles = f'<p style="font-size:14px;color:{MUTE};">{escape(c.t("stack_empty"))}</p>'
    else:
        items = []
        for i, f in enumerate(shown[:12]):
            swatch = SWATCHES[i % len(SWATCHES)]
            url = (f.get("source_url") or "").strip()
            name = escape(f.get("fund_name") or "—")
            name_html = (
                f'<a href="{escape(url)}" {EXT} '
                f'style="text-decoration:none;color:{BLUE};">{name} ↗</a>'
                if url.startswith(("http://", "https://"))
                else name
            )
            dir_key = _match_directory(f, known_sources)
            dir_link = (
                f'<div style="margin-top:6px;"><a href="{c.page_url("directory", source=dir_key)}" '
                f'style="text-decoration:none;font-size:12px;font-weight:700;color:{BLUE};">'
                f'{escape(c.t("xl_flow_directory"))}</a></div>'
                if dir_key else ""
            )
            items.append(
                '<div style="display:flex;justify-content:space-between;gap:20px;'
                'padding:22px 0;border-bottom:1px solid #EFEDE8;"><div>'
                f'<div style="font-size:11px;font-weight:700;letter-spacing:0.06em;'
                f'color:{RED};text-transform:uppercase;">'
                f'{escape(_localize_capital(f.get("capital_type") or "", c.lang))}</div>'
                f'<div style="font-size:17px;font-weight:700;color:{BLUE};margin-top:6px;'
                f'line-height:1.35;">{name_html}</div>'
                f'<div style="font-size:13px;color:{MUTE};margin-top:6px;line-height:1.5;'
                f'max-width:480px;">{escape(_fund_snippet(c, f))}</div>{dir_link}</div>'
                f'<div style="width:100px;height:76px;flex:none;border-radius:4px;'
                f'background:{swatch};"></div></div>'
            )
        articles = "".join(items)
    right = (
        '<div style="flex:1.4 1 420px;display:flex;flex-direction:column;gap:0;">'
        f'{articles}</div>'
    )
    return (
        '<section style="display:flex;gap:48px;padding:64px 48px;flex-wrap:wrap;">'
        f"{left}{right}</section>"
    )


def _sources(c: Ctx) -> str:
    def card(bg: str, label: str, url: str) -> str:
        return (
            f'<a href="{escape(url)}" {EXT} '
            f'style="text-decoration:none;flex:1 1 320px;height:180px;border-radius:4px;'
            f'background:{bg};position:relative;padding:20px;display:flex;'
            'align-items:flex-end;">'
            f'<div style="color:#FFF;font-size:15px;font-weight:700;">{escape(label)} ↗</div>'
            '<div style="position:absolute;top:18px;right:18px;width:26px;height:26px;'
            'border:1px solid rgba(255,255,255,0.5);border-radius:50%;display:flex;'
            'align-items:center;justify-content:center;color:#FFF;font-size:15px;">+</div></a>'
        )
    return (
        '<section id="sources" style="padding:20px 48px 64px;scroll-margin-top:70px;">'
        '<div style="font-size:24px;font-weight:800;letter-spacing:-0.01em;">'
        f'<span style="color:{RED};">{escape(c.t("sources_kicker"))}</span> '
        f'{escape(c.t("sources_heading"))}</div>'
        f'<p style="margin:14px 0 28px;font-size:14.5px;color:{MUTE};max-width:640px;'
        f'line-height:1.6;">{escape(c.t("sources_body"))}</p>'
        '<div style="display:flex;gap:24px;flex-wrap:wrap;">'
        f'{card(DARK_BLUE, c.t("source_ofac"), OFAC_URL)}'
        f'{card(INK, c.t("source_fts"), FTS_URL)}</div></section>'
    )


def _contacts_block(c: Ctx) -> str:
    """Relevant contacts listed at the bottom of every page (config.FOOTER_CONTACTS)."""
    cards = []
    for label_key, display, href in config.FOOTER_CONTACTS:
        cards.append(
            '<div style="flex:1 1 240px;min-width:220px;">'
            f'<div style="font-size:11px;font-weight:700;letter-spacing:0.05em;'
            f'text-transform:uppercase;color:#9CA3AF;margin-bottom:4px;">'
            f'{escape(c.t(label_key))}</div>'
            f'<a href="{escape(href)}" style="text-decoration:none;font-size:13px;'
            f'font-weight:700;color:{BLUE};word-break:break-all;">{escape(display)}</a>'
            "</div>"
        )
    return (
        '<div style="margin-bottom:22px;">'
        f'<div style="font-size:12px;font-weight:800;letter-spacing:0.1em;color:{INK};'
        f'margin-bottom:12px;">{escape(c.t("footer_contacts_h"))}</div>'
        '<div style="display:flex;flex-wrap:wrap;gap:18px 28px;">'
        + "".join(cards) + "</div></div>"
    )


def _footer(c: Ctx) -> str:
    links = (
        f'<a href="{c.page_url("about")}" style="text-decoration:none;font-weight:700;'
        f'color:{BLUE};">{escape(c.t("nav_about"))}</a>'
        '<span style="color:#D8D5CC;">·</span>'
        f'<a href="{_mailto("report")}" style="text-decoration:none;font-weight:700;'
        f'color:{BLUE};">{escape(c.t("footer_report"))}</a>'
        '<span style="color:#D8D5CC;">·</span>'
        f'<span style="color:#9CA3AF;">{escape(c.t("footer_updated", date=config.FUNDING_LAST_CHECKED))}</span>'
    )
    return (
        '<footer style="border-top:1px solid #E7E5DF;padding:28px 48px;">'
        + _contacts_block(c)
        + '<div style="display:flex;gap:12px;flex-wrap:wrap;align-items:center;'
        f'font-size:13px;margin-bottom:14px;">{links}</div>'
        f'<p style="margin:0;font-size:12px;line-height:1.6;color:#9CA3AF;max-width:760px;">'
        f'{escape(c.t("disclaimer_short"))} '
        f'<a href="{c.page_url("about")}" style="color:#9CA3AF;font-weight:600;">'
        f'{escape(c.t("footer_learn_about"))}</a></p>'
        f'<div style="margin-top:24px;">{_flag_stripe(height=4, radius=2)}</div></footer>'
    )


# ---------------------------------------------------------------------------
# Funding Directory + detail views
# ---------------------------------------------------------------------------

PHASE_CANON = {
    "relief": "relief",
    "rehabilitation": "recovery",
    "recovery": "recovery",
    "reconstruction": "reconstruction",
}


def _norm_phases(phases: list[str]) -> list[str]:
    out: list[str] = []
    for p in phases:
        cp = PHASE_CANON.get(p, p)
        if cp not in out:
            out.append(cp)
    return out


def _org_layer(org_type: str) -> str:
    return ORG_LAYER.get(org_type, "other")


def _source_name(c: Ctx, s: dict) -> str:
    if c.lang == "es" and s.get("name_es"):
        return s["name_es"]
    return s.get("name_en") or s.get("source_key") or "—"


def _flow_meta(c: Ctx, flow: str) -> tuple[str, str, str]:
    label = c.t(FLOW_BADGE.get(flow, "flow_give_badge"))
    if flow in FLOW_APPLY and flow not in FLOW_GIVE:
        return label, "#E7EEF9", "#1E4E9C"
    if flow == "pipeline":
        return label, "#FBF3D9", "#8A6100"
    if flow == "directory":
        return label, "#EDE7F6", "#5B3B8C"
    if flow in ("government_resource", "sovereign_financing"):
        return label, "#F1F3F5", MUTE
    return label, "#E7F4EC", "#146C43"


def _committed_amount(s: dict) -> tuple[str, str]:
    """Return (formatted amount, label-key). Prefer committed, fall back to target."""
    amt = _fmt_amount(s["currency"], s.get("amount_committed_original"),
                      s.get("amount_committed_usd"))
    if amt != "—":
        return amt, "dir_committed"
    amt = _fmt_amount(s["currency"], s.get("amount_target_original"),
                      s.get("amount_target_usd"))
    return amt, "dir_target"


def _tag(label: str, bg: str, col: str, border: str = "") -> str:
    b = f"border:1px solid {border};" if border else ""
    return (
        f'<span style="display:inline-block;background:{bg};color:{col};{b}'
        'border-radius:999px;padding:3px 11px;font-size:11px;font-weight:700;'
        f'white-space:nowrap;">{escape(label)}</span>'
    )


def _directory_card(c: Ctx, s: dict) -> str:
    name = _source_name(c, s)
    flow_label, fbg, fcol = _flow_meta(c, s["flow_direction"])
    phases = " ".join(
        _tag(c.t(f"phase_{ph}"), "#F1F3F5", MUTE) for ph in _norm_phases(s["phase"])
    )
    amount, amt_key = _committed_amount(s)
    is_pipeline = s["verification_status"] == "pipeline"
    border = f"2px solid {YELLOW}" if is_pipeline else "1px solid #E1DFD8"
    detail = c.detail_href(source=s["source_key"])
    url = (s.get("url") or "").strip()
    review = _tag(c.t("dir_review_badge"), "#FBF3D9", "#8A6100", "#F0DFA8")

    visit = ""
    if url.startswith(("http://", "https://")):
        visit = (
            f'<a href="{escape(url)}" {EXT} '
            f'style="text-decoration:none;font-size:12.5px;font-weight:700;color:{BLUE};">'
            f'{escape(c.t("dir_visit"))}</a>'
        )
    return (
        f'<div style="flex:1 1 340px;max-width:520px;border:{border};border-radius:6px;'
        'padding:20px 22px;display:flex;flex-direction:column;gap:10px;background:#FFF;">'
        f'<div style="display:flex;flex-wrap:wrap;gap:6px;align-items:center;">'
        f'{_tag(flow_label, fbg, fcol)}{phases}</div>'
        f'<a href="{detail}" style="text-decoration:none;font-size:17px;font-weight:700;'
        f'color:{BLUE};line-height:1.3;">{escape(name)}</a>'
        f'<div style="font-size:12.5px;color:{MUTE};">{escape(s.get("org") or "")}</div>'
        + (
            f'<div style="font-size:13px;color:{INK};"><b>{escape(amount)}</b> '
            f'<span style="color:{MUTE};">{escape(c.t(amt_key))}</span></div>'
            if amount != "—" else ""
        )
        + f'<div>{review}</div>'
        '<div style="display:flex;justify-content:space-between;align-items:center;'
        'gap:12px;margin-top:4px;padding-top:10px;border-top:1px solid #F0EEE9;">'
        f'<a href="{detail}" style="text-decoration:none;font-size:12.5px;font-weight:700;'
        f'color:{INK};">{escape(c.t("dir_details"))}</a>{visit}</div>'
        f'<div style="font-size:11px;color:#9CA3AF;">'
        f'{escape(c.t("dir_last_checked", date=s.get("last_checked") or "—"))}</div>'
        "</div>"
    )


def directory_filter_defs(c: Ctx) -> dict[str, tuple[str, list[tuple[str, object]]]]:
    """Filter rows for the Directory: param -> (label key, [(label, value)])."""
    return {
        "fd": ("dir_filter_flow", [
            (c.t("dir_flow_all"), None),
            (c.t("dir_flow_give"), "give"),
            (c.t("dir_flow_apply"), "apply"),
        ]),
        "ph": ("dir_filter_phase", [
            (c.t("dir_phase_all"), None),
            (c.t("phase_relief"), "relief"),
            (c.t("phase_recovery"), "recovery"),
            (c.t("phase_reconstruction"), "reconstruction"),
        ]),
        "ot": ("dir_filter_layer", [
            (c.t("layer_all"), None),
            (c.t("layer_institutional"), "institutional"),
            (c.t("layer_ngo"), "ngo"),
            (c.t("layer_diaspora"), "diaspora"),
            (c.t("layer_community"), "community"),
            (c.t("layer_platform"), "platform"),
        ]),
    }


def apply_directory_filters(c: Ctx, sources: list[dict]) -> list[dict]:
    def flow_ok(s: dict) -> bool:
        if c.fd == "give":
            return s["flow_direction"] in FLOW_GIVE
        if c.fd == "apply":
            return s["flow_direction"] in FLOW_APPLY
        return True

    def phase_ok(s: dict) -> bool:
        if not c.ph:
            return True
        return c.ph in _norm_phases(s["phase"])

    def layer_ok(s: dict) -> bool:
        if not c.ot:
            return True
        return _org_layer(s["org_type"]) == c.ot

    shown = [s for s in sources if flow_ok(s) and phase_ok(s) and layer_ok(s)]
    # OCHA pipeline slot always first — the "obvious slot" for the July-6 plan.
    shown.sort(key=lambda s: (s["verification_status"] != "pipeline",))
    return shown


def _directory_intro(c: Ctx, total: int) -> str:
    header = (
        '<div style="font-size:28px;font-weight:800;letter-spacing:-0.01em;margin-bottom:6px;">'
        f'<span style="color:{RED};">{escape(c.t("dir_kicker"))}</span> '
        f'{escape(c.t("dir_heading"))}</div>'
        f'<p style="margin:0 0 6px;font-size:14.5px;color:{MUTE};max-width:680px;'
        f'line-height:1.55;">{escape(c.t("dir_intro", count=total))}</p>'
        f'<p style="margin:0 0 4px;font-size:12.5px;color:#9CA3AF;max-width:680px;'
        f'line-height:1.5;">{escape(c.t("dir_review_note"))}</p>'
    )
    return (
        '<section id="directory" style="padding:64px 48px 10px;background:#FBFAF7;'
        f'scroll-margin-top:70px;">{header}</section>'
    )


def _directory_grid(c: Ctx, sources: list[dict], shown: list[dict]) -> str:
    if shown:
        cards = "".join(_directory_card(c, s) for s in shown)
        grid = f'<div style="display:flex;flex-wrap:wrap;gap:18px;">{cards}</div>'
    else:
        grid = f'<p style="font-size:14px;color:{MUTE};">{escape(c.t("dir_none"))}</p>'
    footer = (
        f'<p style="margin:18px 0 0;font-size:12.5px;color:#9CA3AF;">'
        f'{escape(c.t("dir_count", count=len(shown), total=len(sources)))} · '
        f'<a href="{_mailto("report")}" style="color:{BLUE};font-weight:700;'
        f'text-decoration:none;">{escape(c.t("dir_suggest"))}</a></p>'
    )
    return (
        '<section style="padding:8px 48px 64px;background:#FBFAF7;">'
        f"{grid}{footer}</section>"
    )


# ---- Detail views ----

def _kv(label: str, value_html: str) -> str:
    if not value_html or value_html == "—":
        return ""
    return (
        '<div style="margin-bottom:16px;">'
        f'<div style="font-size:11px;font-weight:700;letter-spacing:0.06em;'
        f'text-transform:uppercase;color:#9CA3AF;margin-bottom:4px;">{escape(label)}</div>'
        f'<div style="font-size:14px;color:{INK};line-height:1.55;">{value_html}</div></div>'
    )


def find_license(licenses: list[dict], license_id: str) -> dict | None:
    want = license_id.upper().replace(" ", "")
    for lic in licenses:
        if (lic.get("license_id") or "").upper().replace(" ", "") == want:
            return lic
    return None


def gl60_expiry(licenses: list[dict]) -> str:
    lic = find_license(licenses, "GL 60")
    return (lic or {}).get("expiration_date") or config.GL60_EXPIRES


def _gl60_context(c: Ctx, licenses: list[dict]) -> str:
    return c.t("detail_gl60_ctx", date=gl60_expiry(licenses))


def _caf_contribute_block(c: Ctx) -> str:
    ref = "Fondo para la Recuperación y Reconstrucción de Venezuela – [contributor name]"
    emails = ["alianzas@caf.com", "trustfunds@caf.com"]
    mail_links = ", ".join(
        f'<a href="mailto:{e}" style="color:{BLUE};text-decoration:none;">{e}</a>'
        for e in emails
    )
    return (
        f'<div style="margin:24px 0;padding:20px 22px;border:1px solid {YELLOW};'
        'border-radius:6px;background:#FFFDF3;">'
        f'<div style="font-size:14px;font-weight:800;color:{INK};margin-bottom:10px;">'
        f'{escape(c.t("detail_how_title"))}</div>'
        '<div style="font-size:13px;color:#4B5563;line-height:1.6;">'
        '<div style="margin-bottom:8px;">'
        + ("Transferencia en USD o EUR. Referencia obligatoria:" if c.lang == "es"
           else "Transfer in USD or EUR. Required payment reference:")
        + f'</div><div style="font-family:ui-monospace,monospace;font-size:12px;'
        f'background:#FFF;border:1px solid #EEE;border-radius:4px;padding:8px 10px;'
        f'margin-bottom:10px;color:{INK};">{escape(ref)}</div>'
        + ("Envíe copia del comprobante a: " if c.lang == "es"
           else "Send a copy of the receipt to: ")
        + mail_links + "</div></div>"
    )


def _source_detail(c: Ctx, s: dict, licenses: list[dict]) -> str:
    name = _source_name(c, s)
    flow_label, fbg, fcol = _flow_meta(c, s["flow_direction"])
    phases = " ".join(
        _tag(c.t(f"phase_{ph}"), "#F1F3F5", MUTE) for ph in _norm_phases(s["phase"])
    )
    verif_key = f"verif_{s['verification_status']}"
    verif_label = c.t(verif_key) if c.bundle.get(verif_key) or STRINGS["en"].get(verif_key) \
        else s["verification_status"]

    committed = _fmt_amount(s["currency"], s.get("amount_committed_original"),
                            s.get("amount_committed_usd"))
    target = _fmt_amount(s["currency"], s.get("amount_target_original"),
                         s.get("amount_target_usd"))
    accepts = ", ".join(s.get("accepts_from") or []) or "—"
    notes = s.get("notes_es") if c.lang == "es" and s.get("notes_es") else s.get("amount_notes")

    url = (s.get("url") or "").strip()
    source_link = ""
    if url.startswith(("http://", "https://")):
        source_link = (
            f'<a href="{escape(url)}" {EXT} '
            f'style="text-decoration:none;display:inline-block;margin:8px 0 4px;'
            f'background:{BLUE};color:#FFF;padding:11px 22px;border-radius:999px;'
            f'font-size:13px;font-weight:700;">{escape(c.t("detail_source_link"))}</a>'
        )

    lic_ctx = ""
    if "GL 60" in (s.get("suggested_license") or ""):
        xlink = (
            f'<br><a href="{c.page_url("licenses", gl="GL 60", anchor="gl-60")}" '
            f'style="color:{BLUE};font-weight:700;text-decoration:none;">'
            f'{escape(c.t("xl_source_license"))}</a>'
        )
        lic_ctx = _kv(c.t("detail_license_ctx"), escape(_gl60_context(c, licenses)) + xlink)

    how = _caf_contribute_block(c) if s["source_key"] == "caf-reconstruction-fund" else ""

    body = (
        f'<a href="{c.href(source=None, pathway=None)}" style="text-decoration:none;'
        f'font-size:13px;font-weight:700;color:{BLUE};">{escape(c.t("detail_back"))}</a>'
        f'<div style="display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:18px 0 6px;">'
        f'{_tag(flow_label, fbg, fcol)}{phases}'
        f'{_tag(c.t("dir_review_badge"), "#FBF3D9", "#8A6100", "#F0DFA8")}</div>'
        f'<h1 style="margin:6px 0 4px;font-size:30px;font-weight:800;color:{INK};'
        f'line-height:1.2;">{escape(name)}</h1>'
        f'<div style="font-size:14px;color:{MUTE};margin-bottom:6px;">{escape(s.get("org") or "")}</div>'
        f'{source_link}'
        f'{how}'
        '<div style="display:flex;flex-wrap:wrap;gap:40px;margin-top:20px;">'
        '<div style="flex:1 1 300px;">'
        + _kv(c.t("detail_committed"), f"<b>{escape(committed)}</b>")
        + _kv(c.t("detail_target"), escape(target))
        + _kv(c.t("detail_accepts"), escape(accepts))
        + _kv(c.t("detail_goes_to"), escape(s.get("funds_go_to") or "—"))
        + "</div><div style=\"flex:1 1 300px;\">"
        + _kv(c.t("detail_verification"), escape(verif_label))
        + _kv(c.t("detail_status"), escape(s.get("status") or "—"))
        + _kv(c.t("detail_org_type"), escape((s.get("org_type") or "").replace("_", " ")))
        + lic_ctx
        + "</div></div>"
        + _kv(c.t("detail_suggested"), escape(s.get("suggested_license") or "—"))
        + _kv(c.t("detail_compliance"), escape(s.get("compliance_notes") or "—"))
        + _kv(c.t("detail_notes"), escape(notes or "—"))
    )
    return (
        '<section style="padding:40px 48px 64px;max-width:960px;">'
        f"{body}</section>"
    )


def _pathway_detail(c: Ctx, p: dict, licenses: list[dict]) -> str:
    verdict = (p.get("compliance_verdict") or "").strip()
    vkey = verdict.lower()
    vbg, vcol, vborder = VERDICT_STYLE.get(vkey, ("#F1F3F5", MUTE, "#E2E5E9"))
    vlabel = c.t(f"verdict_{vkey}") if vkey in ("green", "yellow", "red") else (verdict or "—")
    exp = _parse_date(p.get("expiration_date"))
    exp_str = exp.isoformat() if exp else "—"
    sectors = ", ".join(
        _localize_sector(s, c.lang) for s in (p.get("target_sectors") or [])
    ) or "—"
    license_id = p.get("license_id") or ""
    lic_ctx = ""
    if license_id.upper().replace(" ", "") == "GL60":
        lic_ctx = _kv(c.t("detail_license_ctx"), escape(_gl60_context(c, licenses)))
    # Cross-link to the governing license on the Licenses page.
    license_link = escape(license_id or "—")
    if license_id:
        license_link = (
            f'{escape(license_id)} · '
            f'<a href="{c.page_url("licenses", gl=license_id)}" '
            f'style="color:{BLUE};font-weight:700;text-decoration:none;">'
            f'{escape(c.t("xl_pathway_license"))}</a>'
        )
    body = (
        f'<a href="{c.href(source=None, pathway=None)}" style="text-decoration:none;'
        f'font-size:13px;font-weight:700;color:{BLUE};">{escape(c.t("detail_back"))}</a>'
        f'<div style="margin:18px 0 6px;">'
        f'<span style="font-size:11px;font-weight:700;letter-spacing:0.08em;'
        f'text-transform:uppercase;color:{RED};">{escape(c.t("detail_pathway_kicker"))}</span></div>'
        f'<h1 style="margin:2px 0 18px;font-size:30px;font-weight:800;color:{INK};'
        f'line-height:1.2;">{escape(p.get("fund_name") or "—")}</h1>'
        '<div style="display:flex;flex-wrap:wrap;gap:40px;">'
        '<div style="flex:1 1 280px;">'
        + _kv(c.t("detail_pw_verdict"),
              f'<span style="background:{vbg};color:{vcol};border:1px solid {vborder};'
              f'border-radius:999px;padding:3px 12px;font-size:12px;font-weight:700;">'
              f'{escape(vlabel)}</span>')
        + _kv(c.t("detail_pw_license"), license_link)
        + _kv(c.t("detail_pw_expiry"), escape(exp_str))
        + "</div><div style=\"flex:1 1 280px;\">"
        + _kv(c.t("detail_pw_capital"), escape(_localize_capital(p.get("capital_type") or "", c.lang)))
        + _kv(c.t("detail_pw_sectors"), escape(sectors))
        + lic_ctx
        + "</div></div>"
    )
    return f'<section style="padding:40px 48px 64px;max-width:960px;">{body}</section>'


# ---------------------------------------------------------------------------
# Simple-path section builders (Donate / Send money / Volunteer)
# ---------------------------------------------------------------------------

def simple_disclaimer_html(c: Ctx) -> str:
    """Muted not-legal-advice line closing every simple-path page."""
    return (
        '<p style="margin:26px 0 0;font-size:12.5px;color:#9CA3AF;max-width:640px;'
        f'line-height:1.5;">{escape(c.t("simple_disclaimer"))}</p>'
    )


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------

_BASE_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Open+Sans:wght@400;600;700;800&display=swap');
#MainMenu {visibility:hidden;}
header[data-testid="stHeader"] {display:none;}
/* Hide only Streamlit's own footer, never the app's <footer> in the shell. */
.stApp > footer {visibility:hidden;}
[data-testid="stToolbar"], [data-testid="stDecoration"], [data-testid="stStatusWidget"] {display:none;}
[data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"] {display:none;}
.stApp, [data-testid="stAppViewContainer"], section.main, .main, .block-container {
    background:#FFFFFF !important;
}
/* Full-bleed: the design manages its own padding */
.block-container {
    padding:0 !important;
    max-width:100% !important;
}
[data-testid="stMainBlockContainer"] {padding:0 !important; max-width:100% !important;}
html, body, [class*="css"], .stApp, .stMarkdown, p, span, div, h1, h2, h3, a, button, input, label {
    font-family:'Open Sans', Helvetica, Arial, sans-serif !important;
}
[data-testid="stMarkdownContainer"] > div {width:100%;}
a {color:inherit;}
a.row-link:hover {background:#FBFAF7 !important;}
section[id] {scroll-margin-top:70px;}

/* --- Widget chrome (SPA nav header, breadcrumb, filter pills) --- */
/* Stack html blocks + widget rows flush, like one continuous document. */
[data-testid="stMainBlockContainer"] [data-testid="stVerticalBlock"] {gap:0 !important;}
.st-key-navhdr {padding:15px 48px;border-bottom:1px solid #E7E5DF;background:#FFF;}
.st-key-navhdr [data-testid="stPageLink-NavLink"] {padding:0;background:transparent;}
.st-key-navhdr [data-testid="stPageLink-NavLink"] p
  {font-size:13px;font-weight:600;color:#5B6472;white-space:nowrap;}
.st-key-navhdr [data-testid="stPageLink-NavLink"]:hover p {color:#12172B;}
.st-key-navhdr [data-testid="stPageLink-NavLink"][aria-current="page"] p
  {color:#12172B;font-weight:700;border-bottom:2px solid #CF142B;padding-bottom:2px;}
.st-key-navhdr [data-testid="stButtonGroup"]
  {border:1px solid #D8D5CC;border-radius:999px;padding:2px;width:fit-content;
   margin-left:auto;}
.st-key-navhdr [data-testid="stButtonGroup"] button
  {border:none;border-radius:999px;padding:2px 12px;min-height:26px;
   font-size:12px;font-weight:700;color:#5B6472;background:transparent;}
.st-key-navhdr [data-testid="stButtonGroup"] button[aria-checked="true"],
.st-key-navhdr [data-testid="stButtonGroup"] button[kind$="Active"]
  {background:#00247D !important;color:#FFF !important;}
.st-key-navhdr [data-testid="stButtonGroup"] button p {font-size:12px;font-weight:700;}
.st-key-crumb {padding:16px 48px 0;}
.st-key-crumb [data-testid="stPageLink-NavLink"] {padding:0;background:transparent;}
.st-key-crumb [data-testid="stPageLink-NavLink"] p
  {font-size:13px;font-weight:700;color:#00247D;}
.st-key-dirfilters {background:#FBFAF7;padding:0 48px 14px;}
.st-key-capfilters {padding:2px 48px 8px;}
.st-key-pwfilter {padding:0 48px 10px;}
.st-key-dirfilters [data-testid="stWidgetLabel"] p,
.st-key-capfilters [data-testid="stWidgetLabel"] p
  {font-size:11px;font-weight:700;letter-spacing:0.06em;text-transform:uppercase;
   color:#9CA3AF;}
.st-key-dirfilters [data-testid="stButtonGroup"] button,
.st-key-capfilters [data-testid="stButtonGroup"] button
  {border:1px solid #D8D5CC;border-radius:999px;padding:3px 13px;min-height:28px;
   font-size:12px;font-weight:600;color:#12172B;background:transparent;}
.st-key-dirfilters [data-testid="stButtonGroup"] button[aria-checked="true"],
.st-key-dirfilters [data-testid="stButtonGroup"] button[kind$="Active"],
.st-key-capfilters [data-testid="stButtonGroup"] button[aria-checked="true"],
.st-key-capfilters [data-testid="stButtonGroup"] button[kind$="Active"]
  {background:#00247D !important;color:#FFF !important;border-color:#00247D !important;}
.st-key-dirfilters [data-testid="stButtonGroup"] button p,
.st-key-capfilters [data-testid="stButtonGroup"] button p {font-size:12px;}
.st-key-pwfilter button
  {border:1px solid #D8D5CC;border-radius:999px;padding:3px 14px;min-height:28px;
   font-size:12px;font-weight:700;color:#00247D;background:transparent;}
/* Header flag icon (inline SVG must fill its 34px chip) */
.ve-flag svg {width:100%;height:100%;display:block;}

/* Glossary tooltip (shared component — see gloss() in layout.py) */
.gl-term {border-bottom:1px dotted #9CA3AF;cursor:help;position:relative;}
.gl-term:hover::after, .gl-term:focus::after {
  content:attr(data-tip);position:absolute;left:50%;transform:translateX(-50%);
  top:135%;z-index:60;
  width:min(280px,70vw);background:#12172B;color:#FFF;padding:10px 12px;
  border-radius:6px;font-size:12px;font-weight:400;line-height:1.5;
  white-space:normal;letter-spacing:normal;text-transform:none;text-align:left;}

/* Intent cards (simple front door on Home) */
a.intent-card:hover {border-color:#00247D !important;
  box-shadow:0 3px 14px rgba(0,36,125,0.10);}
</style>
"""


# st.page_link targets (must match the st.Page registrations in app.py).
PAGE_FILES = {
    "home": "pages/1_Home.py",
    "licenses": "pages/2_Licenses.py",
    "pathways": "pages/3_Pathways.py",
    "directory": "pages/4_Directory.py",
    "capital": "pages/5_Capital_Stack.py",
    "about": "pages/6_About.py",
    "remit": "pages/9_Send_Money.py",
}


# Venezuelan flag, square crop (flag-icons project, MIT). An accurate flag —
# yellow/blue/red bands with the 8-star arc — NOT a hand-built tricolor, which
# reads as Colombia/Ecuador. Inlined so the header never depends on static
# file serving; the favicon in app.py uses the same asset.
_FLAG_SVG = (config.ROOT / "assets" / "ve-square.svg").read_text(encoding="utf-8")


def _logo_html(c: Ctx) -> str:
    return (
        f'<a href="{c.page_url("home")}" style="text-decoration:none;display:flex;'
        'align-items:center;gap:12px;">'
        '<div class="ve-flag" style="width:34px;height:34px;border-radius:8px;'
        f'overflow:hidden;flex:none;border:1px solid #E1DFD8;">{_FLAG_SVG}</div>'
        f'<div style="font-weight:800;font-size:16px;letter-spacing:-0.01em;'
        f'color:{BLUE};white-space:nowrap;">Venezuela '
        f'<span style="color:{RED};">Resiliente</span></div></a>'
    )


def _render_header(c: Ctx, active: str) -> None:
    """Header row: HTML logo + st.page_link nav + language segmented control.

    page_link navigation is handled client-side by Streamlit's router (no
    browser reload); the language toggle reruns over the websocket. Query
    params drop on SPA navigation, so lang/auth persist in session_state
    (see app.py) and Ctx falls back to them.
    """
    nav = HEADER_NAV
    # This Streamlit build doesn't stamp aria-current on page links, so mark
    # the active page by its (relative) href instead.
    active_href = PAGE_SLUGS.get(active)
    if active_href:
        st.markdown(
            f'<style>.st-key-navhdr a[data-testid="stPageLink-NavLink"]'
            f'[href="{active_href}"] p {{color:{INK} !important;font-weight:700;'
            f'border-bottom:2px solid {RED};padding-bottom:2px;}}</style>',
            unsafe_allow_html=True,
        )
    with st.container(key="navhdr"):
        cols = st.columns(
            [2.6, 1.2, 0.75, 0.7, 0.75, 0.95, 1.0],
            vertical_alignment="center",
        )
        with cols[0]:
            st.html(_logo_html(c))
        for col, (slug, label_key) in zip(cols[2:6], nav):
            with col:
                st.page_link(PAGE_FILES[slug], label=c.t(label_key))
        with cols[6]:
            sel = st.segmented_control(
                "lang",
                ["ES", "EN"],
                default=("ES" if c.lang == "es" else "EN"),
                key="lang_sel",
                label_visibility="collapsed",
            )
            new_lang = {"ES": "es", "EN": "en"}.get(sel or "", c.lang)
            if new_lang != c.lang:
                st.session_state.lang = new_lang
                st.query_params["lang"] = new_lang
                c.lang = new_lang
                st.rerun()


def render_shell(c: Ctx, active: str) -> None:
    """Top chrome: CSS + flag stripe + widget header (+ breadcrumb off Home)."""
    init_db()
    # Keep session + i18n in sync with the query param for the Admin page.
    st.session_state.lang = c.lang
    # CSS via st.markdown (st.html strips <style> blocks); page HTML via
    # st.html, because Streamlit's markdown renderer forces every link to open
    # in a new tab while st.html leaves anchors alone — same-tab navigation.
    st.markdown(_BASE_CSS, unsafe_allow_html=True)
    st.html(_flag_stripe())
    _render_header(c, active)
    if active != "home":
        with st.container(key="crumb"):
            st.page_link(PAGE_FILES["home"], label=c.t("crumb_home"))


def render_footer(c: Ctx) -> None:
    st.html(_footer(c))


def render_body(body: str) -> None:
    """One full-bleed HTML chunk of the page, styled like the original shell."""
    st.html(
        '<div style="font-family:\'Open Sans\',Helvetica,Arial,sans-serif;'
        f'color:{INK};background:#FFF;width:100%;overflow-x:hidden;">'
        + body
        + "</div>"
    )


def render_page(c: Ctx, active: str, body: str) -> None:
    """Single-chunk page: shell + body + footer (pages without widgets)."""
    render_shell(c, active)
    render_body(body)
    render_footer(c)


def pills_filter(
    c: Ctx, param: str, label_key: str, options: list[tuple[str, object]]
) -> object:
    """One filter row as st.pills, two-way synced with its query param.

    Clicking reruns over the websocket (no page reload) and the URL keeps the
    param so filtered views stay shareable. Returns the selected value.
    """
    labels = [lbl for lbl, _v in options]
    by_label = dict(options)
    cur = getattr(c, param, None)
    default = next((lbl for lbl, v in options if v == cur), labels[0])
    sel = st.pills(c.t(label_key), labels, default=default, key=f"flt_{param}")
    value = by_label.get(sel) if sel else None
    if value != cur:
        if value is None:
            st.query_params.pop(param, None)
        else:
            st.query_params[param] = str(value)
    return value


def breadcrumb(c: Ctx) -> str:
    """Simple '← Home' link for sub-pages."""
    return (
        f'<div style="padding:16px 48px 0;">'
        f'<a href="{c.page_url("home")}" style="text-decoration:none;font-size:13px;'
        f'font-weight:700;color:{BLUE};">{escape(c.t("crumb_home"))}</a></div>'
    )
