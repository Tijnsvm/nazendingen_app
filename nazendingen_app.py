import streamlit as st
import pandas as pd
import os
import json
from datetime import datetime, timedelta
import base64
import time
import shutil
import matplotlib.pyplot as plt
import matplotlib
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from io import BytesIO
import streamlit as st
matplotlib.use('Agg')

# ===============================
# TIJDZONE (NL) & BASISPADEN
# ===============================
os.environ["TZ"] = "Europe/Amsterdam"
try:
    time.tzset()
except AttributeError:
    pass

NAZENDINGEN_BESTAND = "nazendingen.xlsx"
BACKUP_MAP = "backups"
UPLOAD_MAP = "uploads"
INSTELLINGEN_BESTAND = "instellingen.json"
LOGO_PATH = "Logo-Rechts-white.png"
KLEUR_GROEN = "#009980"
KLEUR_ACCENT = "#ff9500"

for _p in (BACKUP_MAP, UPLOAD_MAP):
    if not os.path.exists(_p):
        os.makedirs(_p)

# ===============================
# INSTELLINGEN
# ===============================
def opslaan_instellingen(instellingen: dict):
    with open(INSTELLINGEN_BESTAND, "w", encoding="utf-8") as f:
        json.dump(instellingen, f, ensure_ascii=False, indent=2)

def laad_instellingen() -> dict:
    if not os.path.exists(INSTELLINGEN_BESTAND):
        instellingen = {
            "teamleden": ["Tijn", "Jordi", "Thijmen", "Maaike", "Ulfet"],
            "bewaar_uur": 26,
            "dark_mode": False,  # toggle thema
        }
        opslaan_instellingen(instellingen)
        return instellingen
    with open(INSTELLINGEN_BESTAND, "r", encoding="utf-8") as f:
        return json.load(f)

instellingen = laad_instellingen()
# === Beheerwachtwoord default (géén UI) ===
if "admin_password" not in instellingen:
    instellingen["admin_password"] = "Vivid123"  # verander dit direct!
    opslaan_instellingen(instellingen)

TEAMLEDEN = instellingen.get("teamleden", [])
BEWAAR_UUR = instellingen.get("bewaar_uur", 26)
DARK_MODE = instellingen.get("dark_mode", False)
# === 📱 Mobiele weergave instelling ===
# Standaard desktopwaarde
THUMB_W = 72

# Check of er eerder al iets is opgeslagen in instellingen of sessie
if "mobiel_compact" not in st.session_state:
    st.session_state["mobiel_compact"] = instellingen.get("mobiel_compact", False)

# Pas thumbnail breedte aan op basis van toggle
if st.session_state["mobiel_compact"]:
    THUMB_W = 56  # compactere thumbnails voor mobiel

# === Beheerwachtwoord instellen (eenmalig) ===
if "admin_password" not in instellingen:
    instellingen["admin_password"] = "Vivid123"  # standaard wachtwoord — verander dit!
    opslaan_instellingen(instellingen)

# ===============================
# DATAFRAME LAAD & SAVE
# ===============================
cols_excel = [
    "ID", "Datum aanvraag", "EAN", "Productnaam", "Bestelnummer", "Klantnaam",
    "Nazending", "Fotos", "Status", "Beoordeeld door", "Beoordeling opmerking",
    "Datum beoordeling", "SIU-nummer", "Verzonden door", "Datum verzending",
    "Datum gekozen", "Tijd gekozen", "Niet op voorraad gelezen", "Niet op voorraad gelezen tijd"
]

def leeg_df():
    return pd.DataFrame(columns=cols_excel)

def laad_dataframe() -> pd.DataFrame:
    if os.path.exists(NAZENDINGEN_BESTAND):
        df = pd.read_excel(NAZENDINGEN_BESTAND, dtype=str).fillna("")
        if "Reden" in df.columns and "Nazending" not in df.columns:
            df["Nazending"] = df["Reden"]
            df.drop(columns=["Reden"], inplace=True)
        for col in cols_excel:
            if col not in df.columns:
                df[col] = ""
        return df
    else:
        df = leeg_df()
        df.to_excel(NAZENDINGEN_BESTAND, index=False)
        return df

def save_df(df: pd.DataFrame):
    df.to_excel(NAZENDINGEN_BESTAND, index=False)

df = laad_dataframe()

def maak_backup(origineel_pad=NAZENDINGEN_BESTAND):
    if os.path.exists(origineel_pad):
        backup_name = f"nazendingen_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        backup_path = os.path.join(BACKUP_MAP, backup_name)
        shutil.copy2(origineel_pad, backup_path)
        return backup_path
    return None

# ===============================
# SESSION STATE NAVIGATIE & PREVIEW
# ===============================
if "active_tab" not in st.session_state:
    st.session_state.active_tab = "📬 Aanvraag indienen"
if "nav_choice" not in st.session_state:
    st.session_state.nav_choice = st.session_state.active_tab
if "filter_klantnaam" not in st.session_state:
    st.session_state.filter_klantnaam = ""
for k in ("preview_foto", "preview_idx"):
    if k not in st.session_state:
        st.session_state[k] = None

def go(tab_label: str):
    """Zet actieve tab voor tegels & radio (geen st.rerun nodig)."""
    st.session_state.active_tab = tab_label
    st.session_state.nav_choice = tab_label

# --- SIU filter state ---
if "siufilter" not in st.session_state:
    st.session_state.siufilter = "Alles"  # "Alles" | "Op voorraad" | "Niet op voorraad"

def go_siu_with_filter(filter_label: str):
    """Zet filter (Alles / Op voorraad / Niet op voorraad) en navigeer naar SIU-tab."""
    st.session_state.siufilter = filter_label
    st.session_state.active_tab = "✏️ SIU invullen (klantenservice)"
    st.session_state.nav_choice = "✏️ SIU invullen (klantenservice)"

# ===============================
# PAGE CONFIG & STYLES
# ===============================
st.set_page_config(page_title="Vivid Green Nazendingen", layout="wide", initial_sidebar_state="auto")

# Basisstijl (light mode default)
st.markdown(f"""
<style>
:root {{
  --bg: #f8fcfa;
  --text: #152c26;
  --card: #ffffff;
  --card-border: #e3f9f3;
  --muted: #00998099;
}}
body, .stApp {{
    background-color: var(--bg) !important;
    color: var(--text) !important;
    font-family: 'Montserrat', 'Segoe UI', Arial, sans-serif;
}}
#vivid-header {{
    position: sticky; top: 0; z-index: 999; width: 100vw;
    background: linear-gradient(90deg, {KLEUR_GROEN} 0%, #48bc8c 100%);
    color: white; padding: 28px 0 15px 0; margin: -60px -1vw 28px -1vw; text-align: center;
    box-shadow: 0 2px 16px 0 #00998015;
}}
#vivid-logo {{ width: 200px; max-width: 91vw; margin-bottom: 7px; }}
.header-title {{ font-size: 2.19rem; font-weight: 700; letter-spacing: -1px; color: white; margin: 0 0 2px 0; }}
.header-sub {{ font-size: 1.09rem; color: #d0f7ed; margin: 2px 0 0 0; }}

.request-card {{
    border:1.1px solid var(--card-border); border-radius:18px;
    padding:16px 19px 13px 19px; margin-bottom:19px;
    box-shadow:0 1px 11px #00998013; background: var(--card);
    position:relative; min-height: 45px; transition: box-shadow 0.23s;
}}
.request-card:hover {{ box-shadow: 0 4px 24px #00998025; }}

.ean-container {{ display: flex; align-items: center; gap: 7px; }}

.progressbar {{
    width: 97%; margin: 4px 0 9px 0; height: 13px; border-radius: 7px;
    background: #e7f7f2; overflow: hidden; box-shadow: 0 1px 6px #0099800d; position: relative;
}}
.progressbar-inner {{
    height: 100%; border-radius: 7px; background: linear-gradient(90deg, {KLEUR_GROEN} 60%, #48bc8c 100%);
    transition: width 0.45s;
}}
.progress-icons {{ display: flex; justify-content: space-between; font-size: 1.04rem; margin-top: -7px; margin-bottom: 8px; color: var(--muted); }}

.status-chip {{ display:inline-block; font-size:1.03rem; font-weight:700; border-radius:12px; padding:5px 16px; margin-bottom:5px; }}
.status-aanv {{background:#ffe46a;color:#7d6700;}}
.status-voorraad {{background:#a2f5e1;color:#044e3d;}}
.status-niet {{background:#ff7d7d;color:#fff;}}
.status-verzonden {{background:#b7e6ac;color:#1d6d29;}}

.stToast {{
    background: #fffbe5; border-left: 4px solid {KLEUR_ACCENT}; padding: 12px 15px 10px 15px;
    border-radius: 11px; margin-bottom: 10px; color: #333; font-weight: 500; font-size: 1.05em;
}}

/* 📱 Mobiel: kolommen onder elkaar & grotere tappables */
@media (max-width: 768px) {{
  .request-card {{ padding: 12px !important; }}
  .tile-area .stButton > button {{ font-size: 1.4rem !important; padding: 22px 10px !important; }}
  .stColumns {{ display: block !important; }}
  div[data-testid="column"] {{ width: 100% !important; flex: none !important; }}
}}
</style>
""", unsafe_allow_html=True)

# --- PROFESSIONELE DARK MODE (zet dit ONDERAAN je CSS-blokken) ---
if DARK_MODE:
    st.markdown(f"""
    <style>
    /* ========= PROFESSIONAL DARK THEME (HIGH CONTRAST) ========= */
    :root {{
      --bg: #0c0f10;
      --surface: #141718;
      --surface-2: #1a1e1f;
      --surface-3: #202526;
      --text: #ffffff;             /* Altijd helder wit */
      --muted: #c9d7d4;            /* Sub-tekst / iconen */
      --border: #2b3234;           /* Randen */
      --accent: {KLEUR_GROEN};     /* Jullie merk-groen */
      --accent-weak: #73e6d1;      /* Hover/focus accenten */
      --danger: #ff5a5a;
      --ok: #7be7cf;
      --warn: #ffd24d;
    }}

    /* Basis */
    html, body, .stApp {{
      background-color: var(--bg) !important;
      color: var(--text) !important;
    }}
    h1,h2,h3,h4,h5,h6, p, span, small, strong, em, li, dt, dd, code, pre, kbd {{
      color: var(--text) !important;
    }}
    a, a * {{ color: var(--accent-weak) !important; text-decoration: none; }}
    hr {{ border-color: var(--border) !important; }}

    /* Header blijft brand-identity, tekst helder */
    #vivid-header {{ color: #fff !important; }}
    #vivid-header .header-sub {{ color: #d8fff6 !important; }}

    /* Kaarten / containers */
    .request-card {{
      background: var(--surface) !important;
      color: var(--text) !important;
      border: 1px solid var(--border) !important;
      box-shadow: 0 6px 26px rgba(0,0,0,.35) !important;
    }}

    /* Tegels (klikbare stat-cards) */
    .tile-area .stButton > button,
    .tile-area div.stButton > button,
    .tile-area button[kind],
    .tile-area [data-testid="baseButton-secondary"] {{
      background: var(--surface-2) !important;
      color: var(--text) !important;
      border: 1px solid var(--border) !important;
      box-shadow: 0 8px 28px rgba(0,0,0,.45) !important;
    }}
    .tile-area .stButton > button:hover,
    .tile-area div.stButton > button:hover,
    .tile-area button[kind]:hover,
    .tile-area [data-testid="baseButton-secondary"]:hover {{
      transform: translateY(-3px);
      border-color: var(--accent-weak) !important;
      box-shadow: 0 12px 36px rgba(0,0,0,.55) !important;
    }}
    .tile-area .stButton > button:active {{ transform: translateY(1px); }}

    /* Inputs / velden */
    /* Text/number/email/date/time/textarea */
    .stTextInput input, .stNumberInput input, .stDateInput input, .stTimeInput input,
    .stTextArea textarea {{
      background: var(--surface-2) !important;
      color: var(--text) !important;
      border: 1px solid var(--border) !important;
    }}
    .stTextInput input::placeholder, .stTextArea textarea::placeholder {{
      color: #9db0ac !important;
    }}
    /* Selectbox / multiselect */
    div[data-baseweb="select"] > div {{
      background: var(--surface-2) !important;
      color: var(--text) !important;
      border: 1px solid var(--border) !important;
    }}
    div[data-baseweb="select"] svg {{ fill: var(--text) !important; }}
    /* File uploader */
    .stFileUploader > div {{
      background: var(--surface-2) !important;
      color: var(--text) !important;
      border: 1px dashed var(--border) !important;
    }}
    .stFileUploader label {{ color: var(--text) !important; }}
    /* Checkboxes / radio / labels */
    label, .stCheckbox label, .stRadio label, .stSelectbox label, .stTextInput label,
    .stDateInput label, .stTimeInput label, .stTextArea label, .stFileUploader label {{
      color: var(--text) !important;
    }}
    [data-testid="stRadio"] div[role="radiogroup"] > label > div {{ color: var(--text) !important; }}

    /* Buttons (algemeen) */
    button[kind], .stButton > button {{
      background: var(--surface-3) !important;
      color: var(--text) !important;
      border: 1px solid var(--border) !important;
      box-shadow: 0 6px 20px rgba(0,0,0,.35) !important;
    }}
    button[kind]:hover, .stButton > button:hover {{
      border-color: var(--accent-weak) !important;
      box-shadow: 0 10px 28px rgba(0,0,0,.5) !important;
    }}

    /* Expander */
    [data-testid="stExpander"] details {{
      background: var(--surface-2) !important;
      color: var(--text) !important;
      border: 1px solid var(--border) !important;
    }}
    [data-testid="stExpander"] summary p {{ color: var(--text) !important; }}

    /* Alerts / info/warning/success */
    [data-testid="stAlert"] {{
      background: var(--surface-2) !important;
      border: 1px solid var(--border) !important;
      color: var(--text) !important;
    }}

    /* Progressbar / icons */
    .progressbar {{ background: #1e2526 !important; }}
    .progressbar-inner {{
      background: linear-gradient(90deg, {KLEUR_GROEN} 60%, #48bc8c 100%) !important;
    }}
    .progress-icons {{ color: var(--muted) !important; }}

    /* Status chips (donkere varianten met voldoende contrast) */
    .status-aanv {{ background: var(--warn) !important; color:#2a2400 !important; }}
    .status-voorraad {{ background: var(--ok) !important; color:#07352b !important; }}
    .status-niet {{ background: var(--danger) !important; color:#ffffff !important; }}
    .status-verzonden {{ background:#9be49a !important; color:#0d2e14 !important; }}

    /* Tabel (mocht je later dataframes tonen) */
    .stDataFrame, .stDataFrame table, .stDataFrame td, .stDataFrame th {{
      color: var(--text) !important;
      border-color: var(--border) !important;
      background: var(--surface) !important;
    }}
    .stDataFrame thead th {{ background: var(--surface-2) !important; }}

    /* Dividers / fieldset */
    hr, fieldset {{ border-color: var(--border) !important; }}
    </style>
    """, unsafe_allow_html=True)

# --- Forceer groene tegels: override Streamlit primary overal ---
st.markdown("""
<style>
/* 1) Overschrijf theme-variabelen die Streamlit gebruikt */
:root {
  /* klassieke theme var */
  --primary-color: #009980 !important;

  /* nieuwe button vars (1.30+) */
  --button-primary-bg: #009980 !important;
  --button-primary-text-color: #ffffff !important;
  --button-primary-border-color: #009980 !important;

  /* extra aliases die sommige builds gebruiken */
  --color-primary: #009980 !important;
  --bg-primary: #009980 !important;
}

/* 2) Pak alle primary-knop varianten vast (oude én nieuwe DOM) */
button[kind="primary"],
[data-testid="baseButton-primary"],
[data-testid="baseButton-primary"]:not(:disabled),
button[kind="primary"]:not(:disabled) {
  background: #009980 !important;
  color: #ffffff !important;
  border-color: #009980 !important;
}

/* 3) Zorg dat tekst binnen de knop ook wit blijft */
[data-testid="baseButton-primary"] *, 
button[kind="primary"] * {
  color: #ffffff !important;
}

/* 4) Hover/active states ook groen houden */
[data-testid="baseButton-primary"]:hover,
button[kind="primary"]:hover {
  background: #00ab92 !important;
  border-color: #00c8a6 !important;
}
[data-testid="baseButton-primary"]:active,
button[kind="primary"]:active {
  background: #00886f !important;
  border-color: #00886f !important;
}

/* 5) (optioneel) jouw grote tegel-styling */
[data-testid="baseButton-primary"] {
  border-radius: 28px !important;
  padding: 48px 18px 40px 18px !important;
  width: 100% !important;
  text-align: center !important;
  font-weight: 900 !important;
  font-size: 2.2rem !important;
  line-height: 1.2 !important;
  letter-spacing: -0.3px !important;
  white-space: pre-line !important;
  box-shadow: 0 14px 36px rgba(0,0,0,0.14) !important;
}

/* Eerste regel (cijfer) extra groot */
[data-testid="baseButton-primary"] p:first-child { 
  font-size: 3.4rem !important; 
  margin: 0 !important;
  font-weight: 900 !important;
}

/* Dark mode vlak iets donkerder */
@media (prefers-color-scheme: dark) {
  [data-testid="baseButton-primary"] {
    background: linear-gradient(180deg, var(--surface-2, #1a1e1f) 0%, var(--surface, #141718) 100%) !important;
  }
}

/* 📱 Mobiel compacter */
@media (max-width: 900px) {
  [data-testid="baseButton-primary"] {
    padding: 32px 14px 26px 14px !important;
    font-size: 1.7rem !important;
  }
  [data-testid="baseButton-primary"] p:first-child { font-size: 2.5rem !important; }
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
/* ✨ Shimmer/glans via geanimeerde achtergrond (werkt altijd) */
[data-testid="baseButton-primary"],
button[kind="primary"] {
  position: relative !important;
  color: #ffffff !important;
  border-radius: 28px !important;
  border: 2px solid #009980 !important;

  /* Groene basis + diagonale lichte strook als glans */
  background: linear-gradient(
      110deg,
      #00ab92 0%,
      #009980 28%,
      rgba(255,255,255,0.28) 45%,
      #009980 62%,
      #00886f 100%
  ) !important;
  background-size: 220% 100% !important;
  animation: tileShine 3.6s ease-in-out infinite;
}

/* Hover: iets sneller en een tikje groter */
[data-testid="baseButton-primary"]:hover,
button[kind="primary"]:hover {
  animation-duration: 2.4s;
  transform: translateY(-4px) scale(1.02);
  transition: transform .25s ease;
}

/* 📱 Mobiel: minder “heftig” */
@media (max-width: 900px) {
  [data-testid="baseButton-primary"],
  button[kind="primary"] {
    animation-duration: 4.2s;
  }
}

/* De animatie laat de glans-strook rustig over de knop lopen */
@keyframes tileShine {
  0%   { background-position: 220% 0; }
  50%  { background-position:   0% 0; }
  100% { background-position:   0% 0; }
}
</style>
""", unsafe_allow_html=True)

# --- MOBIEL CSS ---
st.markdown("""
<style>
@media (max-width: 900px) {
  .stColumns, [data-testid="stHorizontalBlock"] { display: block !important; }
  div[data-testid="column"] { width: 100% !important; flex: none !important; padding: 0 !important; }
  .request-card { padding: 14px 12px !important; border-radius: 20px !important; margin-bottom: 14px !important; }
  [data-testid="baseButton-primary"], button[kind="primary"] {
    padding: 28px 14px 24px 14px !important;
    font-size: 1.6rem !important;
    min-height: 64px !important;
  }
  [data-testid="baseButton-primary"] p:first-child { font-size: 2.2rem !important; }
  .stTextInput input, .stNumberInput input, .stDateInput input, .stTimeInput input,
  .stTextArea textarea, div[data-baseweb="select"] > div, .stFileUploader > div {
    min-height: 48px !important;
    font-size: 16px !important;
  }
  label, .stCheckbox label, .stRadio label, .stSelectbox label,
  .stTextInput label, .stDateInput label, .stTimeInput label,
  .stTextArea label, .stFileUploader label { font-size: 0.95rem !important; }
  .progress-icons { font-size: 1rem !important; }
  .status-chip { font-size: 0.95rem !important; padding: 6px 14px !important; }
  .request-card img { max-width: 100% !important; height: auto !important; }
}
</style>
""", unsafe_allow_html=True)

# ===============================
# HEADER
# ===============================
def get_logo_base64():
    if not os.path.exists(LOGO_PATH): return ""
    with open(LOGO_PATH, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")

logo_base64 = get_logo_base64()
st.markdown(f"""
<div id="vivid-header">
    {f'<img id="vivid-logo" src="data:image/png;base64,{logo_base64}"/>' if logo_base64 else ''}
    <div class="header-title">📦 Nazending Systeem</div>
    <div class="header-sub">Efficiënt, vriendelijk & altijd overzicht – samen voor topservice!</div>
</div>
""", unsafe_allow_html=True)

# ===============================
# HELPERS: status/progress/tiles/photos
# ===============================
status_map = {
    "Aangevraagd":    ("status-chip status-aanv",      "🟡 Aangevraagd"),
    "Op voorraad":    ("status-chip status-voorraad",  "🟢 Op voorraad"),
    "Niet op voorraad":("status-chip status-niet",     "❌ Niet op voorraad"),
    "SIU ingevoerd":  ("status-chip status-voorraad",  "🔵 SIU ingevuld"),
    "Verzonden":      ("status-chip status-verzonden", "✅ Verzonden"),
}
def status_chip(status):
    c, t = status_map.get(status, ("status-chip",""))
    return f'<span class="{c}">{t}</span>'

def progress_html(status):
    pct = {"Aangevraagd":7, "Op voorraad":45, "Niet op voorraad":45, "SIU ingevoerd":70, "Verzonden":100}.get(status,7)
    icons = '<div class="progress-icons">🟡 Aanvraag <span>📦 Magazijn</span> <span style="float:right;">✅ Verzonden</span></div>'
    html = f"""{icons}
    <div class="progressbar"><div class="progressbar-inner" style="width:{pct}%"></div></div>"""
    return html

def stats_cards(df):
    """Klikbare, grote tegels boven elk tabblad — met duidelijk SIU-overzicht en magazijn-versturen."""
    nu = datetime.now()

    # Tellers
    s_aangevraagd   = int((df["Status"] == "Aangevraagd").sum())         # Tegel 1 + 2
    s_op_voorraad   = int((df["Status"] == "Op voorraad").sum())          # = SIU te vullen
    s_niet_voorraad = int((df["Status"] == "Niet op voorraad").sum())     # info in SIU-overzicht
    s_siu_ingevuld  = int((df["Status"] == "SIU ingevoerd").sum())        # = klaar voor VERSTUREN

    df_verzonden = df[df["Status"] == "Verzonden"].copy()
    df_verzonden["Datum verzending dt"] = pd.to_datetime(df_verzonden["Datum verzending"], errors="coerce")
    df_verzonden = df_verzonden[df_verzonden["Datum verzending dt"].notna()]
    df_verzonden = df_verzonden[(nu - df_verzonden["Datum verzending dt"]) < timedelta(hours=BEWAAR_UUR)]
    s_verz_recent = int(len(df_verzonden))                                 # Tegel 5

    # Layout: 5 tegels bovenaan
    col1, col2, col3, col4, col5 = st.columns(5)

    # 1) Aangevraagd -> Aanvraag indienen
    with col1:
        st.button(
            f"🟡 {s_aangevraagd}\nAangevraagd",
            use_container_width=True, type="primary",
            key="tile_aangevraagd",
            on_click=go, args=("📬 Aanvraag indienen",)
        )

    # 2) Te beoordelen -> Beoordelen aanvragen (magazijn bepaalt: op voorraad / niet op voorraad)
    with col2:
        st.button(
            f"📝 {s_aangevraagd}\nTe beoordelen",
            use_container_width=True, type="primary",
            key="tile_tebeoordelen",
            on_click=go, args=("📋 Beoordelen aanvragen",)
        )

    # 3) SIU-overzicht (gecombineerd) -> SIU tab met default filter "Op voorraad"
    #    DUIDELIJKE tekst: X = SIU te vullen (op voorraad), Y = niet op voorraad
    with col3:
        st.button(
            f"🖊️ SIU in te vullen: {s_op_voorraad} | Niet op voorraad❌: {s_niet_voorraad}",
            use_container_width=True, type="primary",
            key="tile_siu_overzicht",
            on_click=go_siu_with_filter, args=("Op voorraad",)  # standaard filter
        )

    # 4) Versturen (magazijn) -> naar tab "🚚 Versturen (magazijn)"
    #    Teller = SIU ingevoerd (klaar om te verzenden)
    with col4:
        st.button(
            f"🚚 {s_siu_ingevuld}\nVersturen (magazijn)",
            use_container_width=True, type="primary",
            key="tile_versturen_magazijn",
            on_click=go, args=("🚚 Versturen (magazijn)",)
        )

    # 5) Verzonden (laatste BEWAAR_UUR uur)
    with col5:
        st.button(
            f"📦 {s_verz_recent}\nVerzonden (laatste {BEWAAR_UUR} uur)",
            use_container_width=True, type="primary",
            key="tile_verzonden",
            on_click=go, args=("📦 Verzonden pakketten",)
        )

def render_photos(row, prefix: str, thumb_width: int = 72):
    """Toont thumbnails + optionele grote preview per aanvraag. prefix zorgt voor unieke keys."""
    import json, os
    fotos = []
    try:
        fotos = json.loads(row.get("Fotos", "[]"))
    except Exception:
        fotos = []
    if not fotos:
        st.write("_Geen foto's_")
        return

    ncols = min(4, len(fotos))
    cols = st.columns(ncols)
    for j, foto in enumerate(fotos):
        c = cols[j % ncols]
        with c:
            if os.path.exists(foto):
                st.image(foto, width=thumb_width)
                if st.button("👁️", key=f"preview_{prefix}_{row['ID']}_{j}"):
                    st.session_state.preview_foto = foto
                    st.session_state.preview_idx = f"{prefix}_{row['ID']}_{j}"
                    st.rerun()
            else:
                st.write("_Foto ontbreekt_")

    if st.session_state.get("preview_foto") and st.session_state.get("preview_idx","").startswith(f"{prefix}_{row['ID']}_"):
        with st.expander("🔍 Preview foto", expanded=True):
            st.image(st.session_state.preview_foto, use_container_width=True, caption="Klik op 'Sluit' om te sluiten.")
            if st.button("Sluit", key=f"close_{prefix}_{row['ID']}"):
                st.session_state.preview_foto = None
                st.session_state.preview_idx = None
                st.rerun()

# ===============================
# TAB 1 — Aanvraag indienen
# ===============================
def render_tab1(df):
    stats_cards(df)
    vandaag = datetime.now().date()
    nu = datetime.now()
    tijden = [f"{h:02d}:{m:02d}" for h in range(9, 22) for m in range(60)]
    tijd_nu = nu.strftime("%H:%M")
    tijd_start = datetime.strptime("09:00", "%H:%M").time()
    tijd_eind = datetime.strptime("22:00", "%H:%M").time()
    if tijd_start <= nu.time() <= tijd_eind:
        tijden_dt = [datetime.strptime(t, "%H:%M") for t in tijden]
        nu_dt = datetime.strptime(tijd_nu, "%H:%M")
        tijdverschillen = [abs((t - nu_dt).total_seconds()) for t in tijden_dt]
        default_index = tijdverschillen.index(min(tijdverschillen))
    else:
        default_index = 0

    st.markdown("#### Nieuwe nazending aanvragen")
    with st.form("aanvraag_form", clear_on_submit=True):
        ean = st.text_input("EAN-nummer *")
        productnaam = st.text_input("Productnaam")
        bestelnummer = st.text_input("Bestelnummer *")
        klantnaam = st.text_input("Klantnaam *")
        nazending = st.text_area("Wat moet er nagezonden worden?")
        datum_gekozen = st.date_input("Datum", value=vandaag)
        tijd_gekozen = st.selectbox("Tijd", options=tijden, index=default_index, key="tijd_gekozen_form")
        fotos = st.file_uploader("Upload foto(s) *", type=["jpg", "jpeg", "png"], accept_multiple_files=True)

        submitted = st.form_submit_button("📬 Aanvraag indienen")
        if submitted:
            if not ean or not bestelnummer or not fotos or len(fotos) == 0:
                st.error("⚠️ Vul EAN-nummer, bestelnummer én voeg minimaal 1 foto toe.")
            else:
                foto_paden = []
                tijd = datetime.now().strftime("%Y%m%d%H%M%S")
                for idx, foto in enumerate(fotos):
                    ext = foto.name.split(".")[-1]
                    pad = os.path.join(UPLOAD_MAP, f"{ean}_{tijd}_{idx}.{ext}")
                    with open(pad, "wb") as f:
                        f.write(foto.read())
                    foto_paden.append(pad)

                aanvraag = {
                    "ID": f"{ean}_{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
                    "Datum aanvraag": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "EAN": ean,
                    "Productnaam": productnaam,
                    "Bestelnummer": bestelnummer,
                    "Klantnaam": klantnaam,
                    "Nazending": nazending,
                    "Fotos": json.dumps(foto_paden),
                    "Status": "Aangevraagd",
                    "Beoordeeld door": "",
                    "Beoordeling opmerking": "",
                    "Datum beoordeling": "",
                    "SIU-nummer": "",
                    "Verzonden door": "",
                    "Datum verzending": "",
                    "Datum gekozen": str(datum_gekozen),
                    "Tijd gekozen": tijd_gekozen,
                    "Niet op voorraad gelezen": "",
                    "Niet op voorraad gelezen tijd": "",
                }
                df2 = pd.concat([df, pd.DataFrame([aanvraag])], ignore_index=True)
                save_df(df2)
                st.success("Aanvraag succesvol ingediend! 🎉")
                st.rerun()

    # Overzicht Aangevraagd
    st.markdown("<div style='margin-top:12px; margin-bottom:10px'><b>Zoeken op klantnaam:</b></div>", unsafe_allow_html=True)
    filter_klant = st.text_input("Filter klantnaam (optioneel)", value=st.session_state.filter_klantnaam or "", key="filter_klantnaam_input")
    st.session_state.filter_klantnaam = filter_klant

    df_show = df[df["Status"] == "Aangevraagd"].copy()
    if filter_klant:
        df_show = df_show[df_show["Klantnaam"].str.contains(filter_klant, case=False, na=False)]
    if not df_show.empty:
        df_show["Datum aanvraag sort"] = pd.to_datetime(df_show["Datum aanvraag"], errors="coerce")
        df_show = df_show.sort_values("Datum aanvraag sort", ascending=False)
        for _, row in df_show.iterrows():
            st.markdown(f"<div class='request-card'>", unsafe_allow_html=True)
            cols = st.columns([1.3,1.2,1.7,2.0,1.0,1.4,0.3])
            cols[0].markdown(f"<b>Klant:</b> {row.get('Klantnaam','-')}<br><b>EAN:</b> {row['EAN']}", unsafe_allow_html=True)
            cols[1].markdown(f"**Bestelnummer:**<br>{row['Bestelnummer']}", unsafe_allow_html=True)
            cols[2].markdown(f"**Product:**<br>{row['Productnaam']}", unsafe_allow_html=True)
            cols[3].markdown(f"**Nazending:**<br>{row['Nazending']}", unsafe_allow_html=True)
            cols[4].markdown(progress_html(row['Status']), unsafe_allow_html=True)
            cols[5].markdown(status_chip(row['Status']), unsafe_allow_html=True)
            with cols[6]:
                if st.button("❌", key=f"verwijder_aanv_{row['ID']}"):
                    df2 = df[df["ID"] != row["ID"]].copy()
                    save_df(df2)
                    st.success("Aanvraag verwijderd!")
                    st.rerun()
            render_photos(row, "aanv")  # 📸
            st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.info("Geen aanvragen in deze status gevonden.")

# ===============================
# TAB 2 — Beoordelen aanvragen
# ===============================
def render_tab2(df):
    stats_cards(df)
    df_show = df[df["Status"] == "Aangevraagd"].copy()
    if not df_show.empty:
        df_show["Datum aanvraag sort"] = pd.to_datetime(df_show["Datum aanvraag"], errors="coerce")
        df_show = df_show.sort_values("Datum aanvraag sort", ascending=False)
        st.markdown("### Beoordelen aanvragen door magazijn")
        for _, row in df_show.iterrows():
            st.markdown(f"<div class='request-card'>", unsafe_allow_html=True)
            cols = st.columns([1.3,1.2,1.7,2.0,1.0,1.4])
            cols[0].markdown(f"<b>Klant:</b> {row.get('Klantnaam','-')}<br><b>EAN:</b> {row['EAN']}", unsafe_allow_html=True)
            cols[1].markdown(f"**Bestelnummer:**<br>{row['Bestelnummer']}", unsafe_allow_html=True)
            cols[2].markdown(f"**Product:**<br>{row['Productnaam']}", unsafe_allow_html=True)
            cols[3].markdown(f"**Nazending:**<br>{row['Nazending']}", unsafe_allow_html=True)
            cols[4].markdown(progress_html(row['Status']), unsafe_allow_html=True)
            cols[5].markdown(status_chip(row['Status']), unsafe_allow_html=True)

            met_opm = st.text_input("Opmerking/voorraad info", key=f"opm_{row['ID']}")
            beoordeeld_door = st.selectbox("Beoordeeld door:", options=TEAMLEDEN, key=f"beoord_{row['ID']}")
            colA, colB = st.columns(2)
            if colA.button("🟢 Op voorraad", key=f"voorraad_{row['ID']}"):
                df2 = df.copy()
                df2.loc[df2["ID"] == row["ID"], ["Status","Beoordeeld door","Datum beoordeling","Beoordeling opmerking"]] = [
                    "Op voorraad", beoordeeld_door, datetime.now().strftime("%Y-%m-%d %H:%M"), met_opm
                ]
                save_df(df2)
                st.success("Status aangepast naar 'Op voorraad'")
                st.rerun()
            if colB.button("❌ Niet op voorraad", key=f"niet_{row['ID']}"):
                df2 = df.copy()
                df2.loc[df2["ID"] == row["ID"], ["Status","Beoordeeld door","Datum beoordeling","Beoordeling opmerking"]] = [
                    "Niet op voorraad", beoordeeld_door, datetime.now().strftime("%Y-%m-%d %H:%M"), met_opm
                ]
                save_df(df2)
                st.success("Status aangepast naar 'Niet op voorraad'")
                st.rerun()
            render_photos(row, "beoord")  # 📸
            st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.info("Geen aanvragen om te beoordelen.")

# ===============================
# TAB 3 — SIU invullen (klantenservice)
# ===============================
def render_tab3(df):
    stats_cards(df)
    nu = datetime.now()

    # Niet op voorraad meldingen (max 1 uur zichtbaar na 'gelezen')
    niet_voorraad_df = df[(df["Status"] == "Niet op voorraad")].copy()
    if not niet_voorraad_df.empty:
        niet_voorraad_df["Datum aanvraag sort"] = pd.to_datetime(niet_voorraad_df["Datum aanvraag"], errors="coerce")
        niet_voorraad_df = niet_voorraad_df.sort_values("Datum aanvraag sort", ascending=False)
        st.markdown("#### Niet op voorraad aanvragen (door magazijn gemeld)")
        for _, row in niet_voorraad_df.iterrows():
            gelezen = row.get("Niet op voorraad gelezen", "") == "Ja"
            gelezen_tijd = row.get("Niet op voorraad gelezen tijd", "")
            toon = True
            if gelezen and gelezen_tijd:
                try:
                    gelezen_moment = datetime.strptime(str(gelezen_tijd), "%Y-%m-%d %H:%M:%S")
                    if (nu - gelezen_moment) > timedelta(hours=1):
                        toon = False
                except Exception:
                    pass
            if toon:
                st.markdown(f"<div class='request-card'>", unsafe_allow_html=True)
                st.markdown(
                    f"<b>Klant:</b> {row.get('Klantnaam','-')}<br>"
                    f"<b>EAN:</b> {row['EAN']}<br>"
                    f"<b>Bestelnummer:</b> {row['Bestelnummer']}<br>"
                    f"<b>Product:</b> {row['Productnaam']}<br>"
                    f"<b>Nazending:</b> {row['Nazending']}<br>"
                    f"<b>Opmerking magazijn:</b> {row.get('Beoordeling opmerking','')}",
                    unsafe_allow_html=True
                )
                render_photos(row, "nietvoorraad")  # 📸
                col1, col2 = st.columns([2, 1])
                if not gelezen:
                    if col2.button("✔️ Ik heb dit gelezen", key=f"gelezen_{row['ID']}"):
                        df2 = df.copy()
                        df2.loc[df2["ID"] == row["ID"], ["Niet op voorraad gelezen","Niet op voorraad gelezen tijd"]] = [
                            "Ja", nu.strftime("%Y-%m-%d %H:%M:%S")
                        ]
                        save_df(df2)
                        st.rerun()
                else:
                    col2.success("Afgehandeld (verdwijnt na 1 uur)")
                st.markdown("</div>", unsafe_allow_html=True)

    # SIU invullen voor op voorraad
    op_voorraad_df = df[df["Status"] == "Op voorraad"].copy()
    if not op_voorraad_df.empty:
        op_voorraad_df["Datum aanvraag sort"] = pd.to_datetime(op_voorraad_df["Datum aanvraag"], errors="coerce")
        op_voorraad_df = op_voorraad_df.sort_values("Datum aanvraag sort", ascending=False)
        st.markdown("#### SIU-nummer invoeren voor op voorraad nazendingen")
        for _, row in op_voorraad_df.iterrows():
            st.markdown(f"<div class='request-card'>", unsafe_allow_html=True)
            cols = st.columns([1.5,1.4,2.3,2.2,2.1,1.2])
            cols[0].markdown(
                f"<b>Klant:</b> {row.get('Klantnaam','-')}<br>"
                f"<b>EAN:</b> {row['EAN']}<br>"
                f"<b>Beoordeeld door:</b> {row.get('Beoordeeld door','')}",
                unsafe_allow_html=True
            )
            cols[1].markdown(f"**Bestelnummer:**<br>{row['Bestelnummer']}", unsafe_allow_html=True)
            cols[2].markdown(f"**Product:**<br>{row['Productnaam']}", unsafe_allow_html=True)
            cols[3].markdown(f"**Opmerking magazijn:**<br>{row.get('Beoordeling opmerking','')}", unsafe_allow_html=True)

            render_photos(row, "opvoorraad")  # 📸

            siu = cols[4].text_input("SIU-nummer invoeren", value=str(row.get("SIU-nummer","")), key=f"siu_{row['ID']}")
            if cols[5].button("SIU opslaan", key=f"save_siu_{row['ID']}"):
                df2 = df.copy()
                df2.loc[df2["ID"] == row["ID"], ["SIU-nummer","Status"]] = [str(siu), "SIU ingevoerd"]
                save_df(df2)
                st.success("SIU-nummer opgeslagen!")
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.info("Geen op voorraad aanvragen om af te handelen.")

# ===============================
# TAB 4 — Versturen (magazijn)
# ===============================
def render_tab4(df):
    stats_cards(df)
    siu_df = df[df["Status"] == "SIU ingevoerd"].copy()
    if not siu_df.empty:
        siu_df["Datum aanvraag sort"] = pd.to_datetime(siu_df["Datum aanvraag"], errors="coerce")
        siu_df = siu_df.sort_values("Datum aanvraag sort", ascending=False)
        st.markdown("### Magazijn: pakketten verzenden")
        for _, row in siu_df.iterrows():
            st.markdown(f"<div class='request-card'>", unsafe_allow_html=True)
            cols = st.columns([1.5,1.4,2.3,1.8,1.2,2.0])
            cols[0].markdown(
                f"<b>Klant:</b> {row.get('Klantnaam','-')}<br>"
                f"<b>EAN:</b> {row['EAN']}<br>"
                f"<b>Beoordeeld door:</b> {row.get('Beoordeeld door','')}",
                unsafe_allow_html=True
            )
            cols[1].markdown(f"**Bestelnummer:**<br>{row['Bestelnummer']}", unsafe_allow_html=True)
            cols[2].markdown(f"**Nazending:**<br>{row['Nazending']}", unsafe_allow_html=True)
            cols[3].markdown(f"**SIU-nummer:**<br>{row.get('SIU-nummer','')}", unsafe_allow_html=True)

            render_photos(row, "verstuur")  # 📸

            with cols[5]:
                verzonden_door = st.selectbox("Verzonden door:", options=TEAMLEDEN, key=f"verz_{row['ID']}")
                colA, colB = st.columns(2)
                pakket_kar = colA.checkbox("Pakket ligt op de kar?", key=f"kar_{row['ID']}")
                if colB.button("✅ Markeer als verzonden", key=f"verzend_{row['ID']}"):
                    if not pakket_kar:
                        st.warning("Vink eerst aan dat het pakket op de kar ligt.")
                    else:
                        df2 = df.copy()
                        df2.loc[df2["ID"] == row["ID"], ["Status","Verzonden door","Datum verzending"]] = [
                            "Verzonden", verzonden_door, datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        ]
                        save_df(df2)
                        st.success("Nazending gemarkeerd als verzonden!")
                        st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.info("Geen pakketten klaar om te verzenden.")

# ===============================
# TAB 5 — Verzonden pakketten
# ===============================
def render_tab5(df):
    stats_cards(df)

    st.markdown("### Filter verzonden pakketten")
    colf1, colf2, colf3 = st.columns(3)
    with colf1:
        f_klant = st.text_input("Filter op klantnaam")
    with colf2:
        f_bestel = st.text_input("Filter op bestelnummer")
    with colf3:
        f_siu = st.text_input("Filter op SIU-nummer")

    df_show = df[df["Status"] == "Verzonden"].copy()
    if f_klant:
        df_show = df_show[df_show["Klantnaam"].str.contains(f_klant, case=False, na=False)]
    if f_bestel:
        df_show = df_show[df_show["Bestelnummer"].str.contains(f_bestel, case=False, na=False)]
    if f_siu:
        df_show = df_show[df_show["SIU-nummer"].str.contains(f_siu, case=False, na=False)]

    if not df_show.empty:
        df_show["Datum verzending dt"] = pd.to_datetime(df_show["Datum verzending"], errors="coerce")
        nu = datetime.now()
        df_show = df_show[df_show["Datum verzending dt"].notna()]
        df_show = df_show[(nu - df_show["Datum verzending dt"]) < timedelta(hours=BEWAAR_UUR)]
        df_show = df_show.sort_values("Datum verzending dt", ascending=False)

        st.markdown(f"#### Overzicht (laatste {BEWAAR_UUR} uur)")
        for _, row in df_show.iterrows():
            st.markdown(f"<div class='request-card'>", unsafe_allow_html=True)
            cols = st.columns([1.3,1.2,1.7,2.0,1.0,1.4])
            cols[0].markdown(f"<b>Klant:</b> {row.get('Klantnaam','-')}<br><b>EAN:</b> {row['EAN']}", unsafe_allow_html=True)
            cols[1].markdown(f"**Bestelnummer:**<br>{row['Bestelnummer']}", unsafe_allow_html=True)
            cols[2].markdown(f"**Product:**<br>{row['Productnaam']}", unsafe_allow_html=True)
            cols[3].markdown(f"**Nazending:**<br>{row['Nazending']}", unsafe_allow_html=True)
            cols[4].markdown(f"**SIU:**<br>{row.get('SIU-nummer','')}", unsafe_allow_html=True)
            cols[5].markdown(status_chip(row['Status']), unsafe_allow_html=True)
            render_photos(row, "verzonden")  # 📸
            st.markdown("</div>", unsafe_allow_html=True)

        st.info(f"Pakketten verdwijnen automatisch uit dit overzicht na {BEWAAR_UUR} uur.")
    else:
        st.info("Geen verzonden pakketten die aan je filter voldoen.")

# ===============================
# TAB 6 — Instellingen
# ===============================
def render_tab6(df):
    st.header("⚙️ Instellingen")

    # Teamleden
    st.subheader("Teamleden beheren")
    nieuwe_naam = st.text_input("Nieuw teamlid toevoegen")
    if st.button("➕ Toevoegen"):
        if nieuwe_naam and nieuwe_naam not in instellingen["teamleden"]:
            instellingen["teamleden"].append(nieuwe_naam)
            opslaan_instellingen(instellingen)
            st.success(f"Toegevoegd: {nieuwe_naam}")
            st.rerun()
    if instellingen["teamleden"]:
        verwijder = st.selectbox("Verwijder teamlid", ["(selecteer)"] + instellingen["teamleden"])
        if st.button("🗑️ Verwijderen"):
            if verwijder != "(selecteer)":
                instellingen["teamleden"].remove(verwijder)
                opslaan_instellingen(instellingen)
                st.warning(f"{verwijder} verwijderd uit teamleden!")
                st.rerun()
    st.markdown(f"**Huidige teamleden:** {', '.join(instellingen['teamleden'])}")

    st.divider()

    # Bewaarperiode
    st.subheader("Maximale bewaartijd verzonden pakketten")
    nieuw_uur = st.slider("Aantal uur", min_value=6, max_value=168, value=instellingen.get("bewaar_uur", 26), step=1)
    if nieuw_uur != instellingen.get("bewaar_uur", 26):
        instellingen["bewaar_uur"] = nieuw_uur
        opslaan_instellingen(instellingen)
        st.success(f"Nieuwe bewaarperiode: {nieuw_uur} uur")
        st.rerun()
    st.info(f"Pakketten verdwijnen nu automatisch na **{instellingen['bewaar_uur']} uur** uit tabblad 'Verzonden pakketten'.")

    st.divider()

    # 🌙 Dark mode
    st.subheader("Weergave")
    dm = st.checkbox("🌙 Dark mode inschakelen (witte tekst)", value=instellingen.get("dark_mode", False))
    if dm != instellingen.get("dark_mode", False):
        instellingen["dark_mode"] = dm
        opslaan_instellingen(instellingen)
        st.success("Thema aangepast. Pagina wordt vernieuwd…")
        st.rerun()

    st.divider()

    # Back-up & export
    st.subheader("Back-up & export")
    if os.path.exists(NAZENDINGEN_BESTAND):
        with open(NAZENDINGEN_BESTAND, "rb") as f:
            st.download_button(
                label="📤 Download nazendingen.xlsx",
                data=f,
                file_name=f"nazendingen_backup_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📤 Download als CSV",
            data=csv,
            file_name=f"nazendingen_backup_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv"
        )

    st.divider()

    # ========================
    # 4. Data resetten (beveiligd)
    # ========================
    st.subheader("⚠️ Data resetten (beveiligd)")

    with st.expander("Gevaarlijk! Alleen uitvoeren als je 100% zeker bent.", expanded=False):
        wachtwoord_input = st.text_input("Voer wachtwoord in om ALLE data te resetten", type="password", key="admin_pw_reset")
        col_rst_a, col_rst_b = st.columns([1, 3])
        with col_rst_a:
            if st.button("🧨 Reset alle data", key="btn_reset_all"):
                if wachtwoord_input == instellingen.get("admin_password", ""):
                    # wis het bestand en zet leeg terug
                    if os.path.exists(NAZENDINGEN_BESTAND):
                        os.remove(NAZENDINGEN_BESTAND)
                    df2 = leeg_df()
                    save_df(df2)
                    maak_backup()
                    st.success("✅ Alle data gewist & systeem teruggezet naar leeg!")
                    st.rerun()
                else:
                    st.error("❌ Onjuist wachtwoord. Data is NIET gewist.")


# ===============================
# ROUTER (radio + tegels)
# ===============================
TAB_LABELS = [
    "📬 Aanvraag indienen",
    "📋 Beoordelen aanvragen",
    "✏️ SIU invullen (klantenservice)",
    "🚚 Versturen (magazijn)",
    "📦 Verzonden pakketten",
    "⚙️ Instellingen",
]
TAB_FUNCS = {
    "📬 Aanvraag indienen": lambda: render_tab1(df),
    "📋 Beoordelen aanvragen": lambda: render_tab2(df),
    "✏️ SIU invullen (klantenservice)": lambda: render_tab3(df),
    "🚚 Versturen (magazijn)": lambda: render_tab4(df),
    "📦 Verzonden pakketten": lambda: render_tab5(df),
    "⚙️ Instellingen": lambda: render_tab6(df),
}

if st.session_state.active_tab not in TAB_FUNCS:
    st.session_state.active_tab = TAB_LABELS[0]
    st.session_state.nav_choice = TAB_LABELS[0]

def _on_nav_change():
    st.session_state.active_tab = st.session_state.nav_choice

st.radio(
    "Navigatie",
    TAB_LABELS,
    horizontal=True,
    key="nav_choice",
    on_change=_on_nav_change,
    label_visibility="collapsed",
)

# Render
TAB_FUNCS[st.session_state.active_tab]()

#st.write("Secrets geladen ✅")
#st.write(st.secrets["google"]["client_email"])
#st.write("Drive map ID:", st.secrets["drive"]["uploads_folder_id"])

