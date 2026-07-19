# Landing page redesign — handoff for Claude Code

Redesign of the Home page of `venezuela-finance-navigator` (Streamlit).
The approved visual reference is `Landing Page.dc.html` in this project.

## What changed and why

Diaspora donors / families are the primary audience. The old page buried
"¿Cómo quiere ayudar?" below a title banner, a long welcome section, and
a countdown band. The redesign:

1. **Removed** the blue "Navegador de Financiamiento…" title banner
   (`_title_banner`) — redundant with the logo and hero.
2. **Hero rewritten**: headline ("Navegador de Financiamiento para la Reconstrucción"), one-sentence lead, two CTAs ("Quiero ayudar →"
   scrolls to intent cards; "Explorar el navegador" scrolls to the
   expert section). The Donaciones/Transferencias sub-blurbs are gone —
   they duplicated the intent cards.
3. **Countdown band** kept, moved directly under the hero, with a
   "Ver la licencia →" link to the Licenses page. Shorter note copy.
4. **Intent section** is now the main event: three EQUAL cards on the
   warm `#FBFAF7` band — Donar (red), Enviar dinero (blue), Fondos para
   ONG (green `#146C43`, promoted from slim banner to full card). Each
   card ends with an explicit colored CTA line instead of a bare `→`.
5. **Expert navigator** demoted to a compact grid titled "El navegador
   completo" with the subtitle "Para financiadores, ONG y especialistas
   en cumplimiento". Accent bars removed; teasers kept.

## Steps

### 1. Replace `pages/1_Home.py`

Copy `handoff/pages_1_Home.py` over `pages/1_Home.py` verbatim.

### 2. Add these keys to `STRINGS` in `layout.py`

To the `"es"` dict:

```python
"home_hero_title": "Navegador de Financiamiento para la Reconstrucción",
"home_hero_lead": (
    "Iniciativa independiente que reúne información verificada para "
    "facilitar donaciones y envíos de dinero destinados a las labores de "
    "reconstrucción tras el terremoto del {date} en Venezuela, de manera "
    "legal, segura y transparente."
),
"home_cta_help": "Quiero ayudar →",
"home_cta_explore": "Explorar el navegador",
"gl60_countdown_short": (
    "La Licencia General 60 (GL 60) autoriza hoy los envíos desde "
    "EE. UU. y vence el {date}."
),
"gl60_see_license": "Ver la licencia →",
"intent_donate_cta": "Ver dónde donar →",
"intent_remit_cta": "Ver cómo enviar →",
"intent_ngo_cta": "Ver financiadores →",
"fullnav_heading": "El navegador completo",
"fullnav_sub": "Para financiadores, ONG y especialistas en cumplimiento",
```

To the `"en"` dict:

```python
"home_hero_title": "Reconstruction Finance Navigator",
"home_hero_lead": (
    "An independent initiative that gathers verified information to make "
    "donations and money transfers for reconstruction after the {date} "
    "earthquake in Venezuela easier — legally, safely, and transparently."
),
"home_cta_help": "I want to help →",
"home_cta_explore": "Explore the navigator",
"gl60_countdown_short": (
    "General License 60 (GL 60) allows transfers from the U.S. today "
    "and expires on {date}."
),
"gl60_see_license": "See the license →",
"intent_donate_cta": "See where to donate →",
"intent_remit_cta": "See how to send →",
"intent_ngo_cta": "See funders →",
"fullnav_heading": "The full navigator",
"fullnav_sub": "For funders, NGOs, and compliance specialists",
```

Also update the NGO intent copy (both dicts) — the card title works
better in first person now:

- es `intent_ngo_t`: `"Busco fondos para mi organización"`
- en `intent_ngo_t`: `"Looking for funds for my organization"`

### 3. Nothing else changes

Header, footer, and all other pages stay as they are. `render_page`
already handles the shell. The `#donar` / `#full-navigator` anchors are
plain in-page anchors; `section[id] {scroll-margin-top:70px}` in
`_BASE_CSS` already covers them (the intent section sets its own
`scroll-margin-top` inline too).

### 4. Mobile layout (reference: `Landing Page Mobile.dc.html`)

The grid layouts in `pages_1_Home.py` already stack on narrow screens
(`auto-fit minmax(...)`). To match the approved mobile design, add these
rules to `_BASE_CSS` in `layout.py`:

```css
@media (max-width:640px) {
  /* Hero CTA becomes a single full-width button */
  .home-hero-ctas a {display:block;flex:1 1 100%;text-align:center;}
  /* Hide the secondary "Explorar el navegador" CTA on phones */
  .home-hero-ctas a:nth-child(2) {display:none;}
}
```

and put `class="home-hero-ctas"` on the hero CTA row div in
`_hero()` (`pages_1_Home.py`). Mobile-specific details from the
reference design, all already satisfied by the responsive grids:
intent cards stack vertically full-width; the navigator collapses to
compact tappable rows (title + teaser + `›`); the hero photo sits
below the CTA full-bleed; all tap targets ≥44px tall.

### 5. Verify

Run `streamlit run app.py`, check ES and EN, desktop and ~375px width
(cards use `grid auto-fit minmax(280px,1fr)` so they stack cleanly),
and compare against the reference design.
