import streamlit as st
import pandas as pd
import os
import json
from datetime import datetime, timedelta
import base64
import time
import io
import shutil
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')

NAZENDINGEN_BESTAND = "nazendingen.xlsx"
BACKUP_MAP = "backups"
UPLOAD_MAP = "uploads"
INSTELLINGEN_BESTAND = "instellingen.json"
LOGO_PATH = "Logo-Rechts-white.png"
KLEUR_GROEN = "#009980"
KLEUR_ACCENT = "#ff9500"

if not os.path.exists(BACKUP_MAP):
    os.makedirs(BACKUP_MAP)
if not os.path.exists(UPLOAD_MAP):
    os.makedirs(UPLOAD_MAP)

# ---- Instellingen laden & opslaan ----
def laad_instellingen():
    if not os.path.exists(INSTELLINGEN_BESTAND):
        instellingen = {
            "teamleden": ["Tijn", "Jordi", "Thijmen", "Maaike", "Ulfet"],
            "bewaar_uur": 26
        }
        opslaan_instellingen(instellingen)
        return instellingen
    with open(INSTELLINGEN_BESTAND, "r", encoding="utf-8") as f:
        return json.load(f)

def opslaan_instellingen(instellingen):
    with open(INSTELLINGEN_BESTAND, "w", encoding="utf-8") as f:
        json.dump(instellingen, f, ensure_ascii=False, indent=2)

# ---- NA ieder inladen van instellingen: set globale TEAMLEDEN en BEWAAR_UUR ----
instellingen = laad_instellingen()
TEAMLEDEN = instellingen.get("teamleden", ["Tijn", "Jordi", "Thijmen", "Maaike", "Ulfet", "Robin", "Elissa"])
BEWAAR_UUR = instellingen.get("bewaar_uur", 26)

# ---- Backup functie ----
def maak_backup(origineel_pad=NAZENDINGEN_BESTAND):
    if os.path.exists(origineel_pad):
        backup_name = f"nazendingen_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        backup_path = os.path.join(BACKUP_MAP, backup_name)
        shutil.copy2(origineel_pad, backup_path)
        return backup_path
    return None

# ---- Dataframe laadfunctie ----
cols_excel = [
    "ID", "Datum aanvraag", "EAN", "Productnaam", "Bestelnummer", "Klantnaam",
    "Nazending", "Fotos", "Status", "Beoordeeld door", "Beoordeling opmerking",
    "Datum beoordeling", "SIU-nummer", "Verzonden door", "Datum verzending",
    "Datum gekozen", "Tijd gekozen", "Niet op voorraad gelezen", "Niet op voorraad gelezen tijd"
]

def laad_dataframe():
    if os.path.exists(NAZENDINGEN_BESTAND):
        df = pd.read_excel(NAZENDINGEN_BESTAND, dtype=str).fillna("")
        # Upgrade oude kolommen
        if "Reden" in df.columns and "Nazending" not in df.columns:
            df["Nazending"] = df["Reden"]
            df.drop(columns=["Reden"], inplace=True)
        for col in cols_excel:
            if col not in df.columns:
                df[col] = ""
    else:
        df = pd.DataFrame(columns=cols_excel)
    return df

df = laad_dataframe()

for key in ["preview_foto", "preview_idx", "delete_request", "filter_klantnaam"]:
    if key not in st.session_state:
        st.session_state[key] = None

# ---- PAGE LAYOUT EN STYLES ----
st.set_page_config(page_title="Vivid Green Nazendingen", layout="wide", initial_sidebar_state="auto")
st.markdown(f"""
<style>
body, .stApp {{
    background-color: #f8fcfa !important;
    font-family: 'Montserrat', 'Segoe UI', Arial, sans-serif;
}}
#vivid-header {{
    position: sticky;
    top: 0;
    z-index: 999;
    width: 100vw;
    background: linear-gradient(90deg, {KLEUR_GROEN} 0%, #48bc8c 100%);
    color: white;
    padding: 28px 0 15px 0;
    margin: -60px -1vw 28px -1vw;
    text-align: center;
    box-shadow: 0 2px 16px 0 #00998015;
}}
#vivid-logo {{
    width: 200px;
    max-width: 91vw;
    margin-bottom: 7px;
}}
.header-title {{
    font-size: 2.19rem;
    font-weight: 700;
    letter-spacing: -1px;
    color: white;
    margin-top: 0;
    margin-bottom: 2px;
}}
.header-sub {{
    font-size: 1.09rem;
    color: #d0f7ed;
    margin-bottom: 0;
    margin-top: 2px;
}}
.request-card {{
    border:1.1px solid #e3f9f3;
    border-radius:18px;
    padding:16px 19px 13px 19px;
    margin-bottom:19px;
    box-shadow:0 1px 11px #00998013;
    background: #fff;
    position:relative;
    min-height: 45px;
    transition: box-shadow 0.23s;
}}
.request-card:hover {{
    box-shadow: 0 4px 24px #00998025;
}}
.ean-container {{
    display: flex;
    align-items: center;
    gap: 7px;
}}
@media (max-width: 750px) {{
    .request-card {{ padding:11px 6px 7px 6px; }}
    .stat-card h3 {{ font-size:1.15rem; }}
    .stat-card span {{ font-size:0.89rem; }}
    .ean-container {{ gap: 3px; }}
}}
.progressbar {{
    width: 97%;
    margin: 4px 0 9px 0;
    height: 13px;
    border-radius: 7px;
    background: #e7f7f2;
    overflow: hidden;
    box-shadow: 0 1px 6px #0099800d;
    position: relative;
}}
.progressbar-inner {{
    height: 100%;
    border-radius: 7px;
    background: linear-gradient(90deg, {KLEUR_GROEN} 60%, #48bc8c 100%);
    transition: width 0.45s;
}}
.progress-icons {{
    display: flex;
    justify-content: space-between;
    font-size: 1.04rem;
    margin-top: -7px;
    margin-bottom: 8px;
    color: #00998099;
}}
.stat-card {{
    background: #f5fbf8;
    border-radius: 18px;
    box-shadow: 0 1px 13px 0 #00998012;
    border: 1.1px solid #b0e9dd65;
    padding: 14px 0 10px 0;
    margin: 0 4px 14px 0;
    text-align: center;
}}
.stat-card h3 {{
    margin: 0 0 5px 0;
    font-size: 2.09rem;
    color: {KLEUR_GROEN};
    font-weight: 700;
    letter-spacing: -1px;
    line-height: 1.1em;
}}
.stat-card span {{
    font-size: 1.07rem;
    color: #244d43;
    font-weight: 500;
}}
.status-chip {{
    display: inline-block;
    font-size: 1.03rem;
    font-weight: 700;
    border-radius: 12px;
    padding: 5px 16px;
    margin-bottom: 5px;
}}
.status-aanv {{background:#ffe46a;color:#7d6700;}}
.status-voorraad {{background:#a2f5e1;color:#044e3d;}}
.status-niet {{background:#ff7d7d;color:#fff;}}
.status-verzonden {{background:#b7e6ac;color:#1d6d29;}}
input[type="file"]::file-selector-button {{
    background: {KLEUR_GROEN};
    color: white;
    border: none;
    border-radius: 8px;
    padding: 7px 13px;
    font-size: 1rem;
    font-family: 'Montserrat', 'Segoe UI', Arial, sans-serif;
}}
.stToast {{
    background: #fffbe5;
    border-left: 4px solid {KLEUR_ACCENT};
    padding: 12px 15px 10px 15px;
    border-radius: 11px;
    margin-bottom: 10px;
    color: #333;
    font-weight: 500;
    font-size: 1.05em;
}}
</style>
""", unsafe_allow_html=True)

# ---- HEADER ----
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

# ---- STATUS CHIP EN PROGRESS ----
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
    <div class="progressbar"><div class="progressbar-inner" style="width:{pct}%"></div></div>
    """
    return html

def stats_cards(df):
    nu = datetime.now()

    # Bestaande tellers
    s1 = int((df["Status"] == "Aangevraagd").sum())
    s2 = int((df["Status"] == "SIU ingevoerd").sum())

    # Verzonden in de afgelopen BEWAAR_UUR
    df_verzonden = df[df["Status"] == "Verzonden"].copy()
    df_verzonden["Datum verzending dt"] = pd.to_datetime(df_verzonden["Datum verzending"], errors="coerce")
    df_verzonden = df_verzonden[df_verzonden["Datum verzending dt"].notna()]
    df_verzonden = df_verzonden[(nu - df_verzonden["Datum verzending dt"]) < timedelta(hours=BEWAAR_UUR)]
    s3 = int(len(df_verzonden))

    # Aparte tellers voor Op voorraad / Niet op voorraadst
    s_op_voorraad = int((df["Status"] == "Op voorraad").sum())
    s_niet_voorraad = int((df["Status"] == "Niet op voorraad").sum())

    # Vijf kolommen: Aangevraagd, Op voorraad, Niet op voorraad, SIU ingevuld, Verzonden
    col1, col2, col3, col4, col5 = st.columns(5)

    col1.markdown(
        f'<div class="stat-card"><h3>{s1}</h3><span>Aangevraagd ⏳</span></div>',
        unsafe_allow_html=True
    )
    col2.markdown(
        f'<div class="stat-card"><h3>{s_op_voorraad}</h3><span>Op voorraad ✅</span></div>',
        unsafe_allow_html=True
    )
    col3.markdown(
        f'<div class="stat-card"><h3>{s_niet_voorraad}</h3><span>Niet op voorraad ❌</span></div>',
        unsafe_allow_html=True
    )
    col4.markdown(
        f'<div class="stat-card"><h3>{s2}</h3><span>SIU ingevuld 📝</span></div>',
        unsafe_allow_html=True
    )
    col5.markdown(
        f'<div class="stat-card"><h3>{s3}</h3><span>Verzonden 📤 (laatste {BEWAAR_UUR} uur)</span></div>',
        unsafe_allow_html=True
    )

# ---- TABS ----
tab1, tab2, tab3, tab4, tab5, tab6, = st.tabs([
    "📬 Aanvraag indienen", 
    "📋 Beoordelen aanvragen", 
    "✏️ SIU invullen (klantenservice)",
    "🚚 Versturen (magazijn)",
    "📦 Verzonden pakketten",
    "⚙️ Instellingen",

])

# TAB 1: Aanvraag indienen
with tab1:
    stats_cards(df)
    vandaag = datetime.now().date()
    nu = datetime.now()
    tijden = [f"{h:02d}:{m:02d}" for h in range(9, 15) for m in range(60)]
    tijd_nu = nu.strftime("%H:%M")
    tijd_start = datetime.strptime("09:00", "%H:%M").time()
    tijd_eind = datetime.strptime("14:59", "%H:%M").time()
    if tijd_start <= nu.time() <= tijd_eind:
        tijden_dt = [datetime.strptime(t, "%H:%M") for t in tijden]
        nu_dt = datetime.strptime(tijd_nu, "%H:%M")
        tijdverschillen = [abs((t - nu_dt).total_seconds()) for t in tijden_dt]
        default_index = tijdverschillen.index(min(tijdverschillen))
    else:
        default_index = 0

    st.markdown("#### Nieuwe nazending aanvragen")
    with st.form("aanvraag_form", clear_on_submit=True):
        ean = st.text_input("EAN-nummer")
        productnaam = st.text_input("Productnaam")
        bestelnummer = st.text_input("Bestelnummer")
        klantnaam = st.text_input("Klantnaam")
        nazending = st.text_area("Wat moet er nagezonden worden?")
        datum_gekozen = st.date_input("Datum", value=vandaag)
        tijd_gekozen = st.selectbox(
            "Tijd",
            options=tijden,
            index=default_index,
            key="tijd_gekozen_form"
        )
        fotos = st.file_uploader("Upload eventueel foto's (meerdere mogelijk)", type=["jpg", "jpeg", "png"], accept_multiple_files=True)
        submitted = st.form_submit_button("📬 Aanvraag indienen")
        if submitted:
            foto_paden = []
            if fotos:
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
            df = pd.concat([df, pd.DataFrame([aanvraag])], ignore_index=True)
            df.to_excel(NAZENDINGEN_BESTAND, index=False)
            st.success("Aanvraag succesvol ingediend! 🎉")
            st.rerun()

    # Zoekfilter op klantnaam
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
            cols = st.columns([1.5,1.5,2.2,2.1,1.3,1.2,0.3])
            cols[0].markdown(
                f"<div class='ean-container'><b>EAN:</b> {row['EAN']}</div>"
                f"<span style='font-size:0.94em;color:#009980bb'><b>Datum:</b> {row.get('Datum gekozen','-')}</span><br>"
                f"<span style='font-size:0.94em;color:#009980bb'><b>Tijd:</b> {row.get('Tijd gekozen','-')}</span>",
                unsafe_allow_html=True
            )
            cols[1].markdown(f"**Product:**<br>{row['Productnaam']}<br><b>Bestelnummer:</b> {row['Bestelnummer']}", unsafe_allow_html=True)
            cols[2].markdown(f"**Nazending:**<br>{row['Nazending']}", unsafe_allow_html=True)
            cols[3].markdown(progress_html(row['Status']), unsafe_allow_html=True)
            cols[4].markdown(status_chip(row['Status']), unsafe_allow_html=True)
            fotos = []
            try: fotos = json.loads(row.get("Fotos", "[]"))
            except: pass
            preview_this = False
            with cols[5]:
                if fotos:
                    foto_row = st.columns(len(fotos))
                    for j, foto in enumerate(fotos):
                        if os.path.exists(foto):
                            with foto_row[j]:
                                st.image(foto, width=60)
                                if st.button("👁️", key=f"preview_aanv_{row['ID']}_{j}"):
                                    st.session_state.preview_foto = foto
                                    st.session_state.preview_idx = f"aanv_{row['ID']}_{j}"
                                    st.rerun()
                            if (
                                st.session_state.preview_foto == foto
                                and st.session_state.preview_idx == f"aanv_{row['ID']}_{j}"
                            ):
                                preview_this = True
                        else:
                            st.write("_Foto ontbreekt_")
                else:
                    st.write("_Geen foto's_")
            with cols[6]:
                if st.button("❌", key=f"verwijder_aanv_{row['ID']}"):
                    st.session_state.delete_request = (row['ID'], "aanv")
            if (
                st.session_state.delete_request is not None and
                st.session_state.delete_request[0] == row["ID"] and
                st.session_state.delete_request[1] == "aanv"
            ):
                with st.expander("⚠️ Weet je zeker dat je deze aanvraag wilt verwijderen?", expanded=True):
                    colX, colY = st.columns([2,1])
                    with colX:
                        st.markdown("**Dit kan niet ongedaan worden gemaakt.**")
                    with colY:
                        if st.button("Verwijder definitief", key=f"def_verwijder_aanv_{row['ID']}"):
                            df = df[df["ID"] != row["ID"]]
                            df.to_excel(NAZENDINGEN_BESTAND, index=False)
                            st.session_state.delete_request = None
                            st.success("Aanvraag verwijderd!")
                            st.rerun()
                        if st.button("Annuleer", key=f"annuleer_aanv_{row['ID']}"):
                            st.session_state.delete_request = None
            if preview_this:
                with st.expander("🔍 Preview foto", expanded=True):
                    st.image(st.session_state.preview_foto, use_container_width=True, caption="Klik buiten deze preview om te sluiten.")
                    if st.button("Sluit preview", key=f"sluit_preview_aanv_{row['ID']}_{j}"):
                        st.session_state.preview_foto = None
                        st.session_state.preview_idx = None
                        st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.info("Geen aanvragen in deze status gevonden.")

# --------- TAB 2: Beoordelen aanvragen ---------
with tab2:
    instellingen = laad_instellingen()
    TEAMLEDEN = instellingen["teamleden"]
    stats_cards(df)
    st.markdown("### Beoordelen aanvragen door magazijn")
    df_show = df[df["Status"] == "Aangevraagd"].copy()
    if not df_show.empty:
        df_show["Datum aanvraag sort"] = pd.to_datetime(df_show["Datum aanvraag"], errors="coerce")
        df_show = df_show.sort_values("Datum aanvraag sort", ascending=False)
        for _, row in df_show.iterrows():
            st.markdown(f"<div class='request-card'>", unsafe_allow_html=True)
            cols = st.columns([1.5,1.5,2.2,2.1,1.3,1.2,0.3])
            cols[0].markdown(
                f"<div class='ean-container'><b>EAN:</b> {row['EAN']}</div>"
                f"<span style='font-size:0.94em;color:#009980bb'><b>Datum:</b> {row.get('Datum gekozen','-')}</span><br>"
                f"<span style='font-size:0.94em;color:#009980bb'><b>Tijd:</b> {row.get('Tijd gekozen','-')}</span>",
                unsafe_allow_html=True
            )
            cols[1].markdown(f"**Product:**<br>{row['Productnaam']}<br><b>Bestelnummer:</b> {row['Bestelnummer']}", unsafe_allow_html=True)
            cols[2].markdown(f"**Nazending:**<br>{row['Nazending']}", unsafe_allow_html=True)
            cols[3].markdown(progress_html(row['Status']), unsafe_allow_html=True)
            status_display = row['Status']
            cols[4].markdown(status_chip(status_display), unsafe_allow_html=True)
            fotos = []
            try: fotos = json.loads(row.get("Fotos", "[]"))
            except: pass
            preview_this = False
            with cols[5]:
                if fotos:
                    foto_row = st.columns(len(fotos))
                    for j, foto in enumerate(fotos):
                        if os.path.exists(foto):
                            with foto_row[j]:
                                st.image(foto, width=60)
                                if st.button("👁️", key=f"preview_beoord_{row['ID']}_{j}"):
                                    st.session_state.preview_foto = foto
                                    st.session_state.preview_idx = f"beoord_{row['ID']}_{j}"
                                    st.rerun()
                            if (
                                st.session_state.preview_foto == foto
                                and st.session_state.preview_idx == f"beoord_{row['ID']}_{j}"
                            ):
                                preview_this = True
                        else:
                            st.write("_Foto ontbreekt_")
                else:
                    st.write("_Geen foto's_")
            with cols[6]:
                if st.button("❌", key=f"verwijder_beoord_{row['ID']}"):
                    st.session_state.delete_request = (row['ID'], "beoord")
            if (
                st.session_state.delete_request is not None and
                st.session_state.delete_request[0] == row["ID"] and
                st.session_state.delete_request[1] == "beoord"
            ):
                with st.expander("⚠️ Weet je zeker dat je deze aanvraag wilt verwijderen?", expanded=True):
                    colX, colY = st.columns([2,1])
                    with colX:
                        st.markdown("**Dit kan niet ongedaan worden gemaakt.**")
                    with colY:
                        if st.button("Verwijder definitief", key=f"def_verwijder_beoord_{row['ID']}"):
                            df = df[df["ID"] != row["ID"]]
                            df.to_excel(NAZENDINGEN_BESTAND, index=False)
                            st.session_state.delete_request = None
                            st.success("Aanvraag verwijderd!")
                            st.rerun()
                        if st.button("Annuleer", key=f"annuleer_beoord_{row['ID']}"):
                            st.session_state.delete_request = None
            if preview_this:
                with st.expander("🔍 Preview foto", expanded=True):
                    st.image(st.session_state.preview_foto, use_container_width=True, caption="Klik buiten deze preview om te sluiten.")
                    if st.button("Sluit preview", key=f"sluit_preview_beoord_{row['ID']}_{j}"):
                        st.session_state.preview_foto = None
                        st.session_state.preview_idx = None
                        st.rerun()
            opm = row.get('Beoordeling opmerking', '')
            if opm:
                st.markdown(
                    f"<span style='color:#009980;font-size:1.04em;'>Opmerking magazijn: <b>{opm}</b></span>",
                    unsafe_allow_html=True
                )
            colA, colB, colC = st.columns([2,2.7,2])
            met_opm = colB.text_input("Opmerking/voorraad info", key=f"opm_{row['ID']}")
            beoordeeld_door = colA.selectbox("Beoordeeld door:", options=TEAMLEDEN, key=f"beoord_{row['ID']}")
            if colC.button("🟢 Op voorraad", key=f"voorraad_{row['ID']}"):
                df.loc[df["ID"] == row["ID"], "Status"] = "Op voorraad"
                df.loc[df["ID"] == row["ID"], "Beoordeeld door"] = beoordeeld_door
                df.loc[df["ID"] == row["ID"], "Datum beoordeling"] = datetime.now().strftime("%Y-%m-%d %H:%M")
                df.loc[df["ID"] == row["ID"], "Beoordeling opmerking"] = met_opm
                df.to_excel(NAZENDINGEN_BESTAND, index=False)
                st.success("Status aangepast naar 'Op voorraad'")
                st.rerun()
            if colC.button("❌ Niet op voorraad", key=f"niet_{row['ID']}"):
                df.loc[df["ID"] == row["ID"], "Status"] = "Niet op voorraad"
                df.loc[df["ID"] == row["ID"], "Beoordeeld door"] = beoordeeld_door
                df.loc[df["ID"] == row["ID"], "Datum beoordeling"] = datetime.now().strftime("%Y-%m-%d %H:%M")
                df.loc[df["ID"] == row["ID"], "Beoordeling opmerking"] = met_opm
                df.to_excel(NAZENDINGEN_BESTAND, index=False)
                st.success("Status aangepast naar 'Niet op voorraad'")
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.info("Geen aanvragen om te beoordelen.")

# --------- TAB 3: SIU invullen ---------
with tab3:
    instellingen = laad_instellingen()
    TEAMLEDEN = instellingen["teamleden"]
    stats_cards(df)
    st.markdown("### Afronden & verzenden nazending")
    nu = datetime.now()
    niet_voorraad_df = df[(df["Status"] == "Niet op voorraad")].copy()
    if not niet_voorraad_df.empty:
        niet_voorraad_df["Datum aanvraag sort"] = pd.to_datetime(niet_voorraad_df["Datum aanvraag"], errors="coerce")
        niet_voorraad_df = niet_voorraad_df.sort_values("Datum aanvraag sort", ascending=False)
        st.markdown("#### Niet op voorraad aanvragen (door magazijn gemeld)")
        for _, row in niet_voorraad_df.iterrows():
            gelezen = row.get("Niet op voorraad gelezen", "") == "Ja"
            gelezen_tijd = row.get("Niet op voorraad gelezen tijd", "")
            laten_zien = True
            if gelezen and gelezen_tijd:
                try:
                    gelezen_moment = datetime.strptime(str(gelezen_tijd), "%Y-%m-%d %H:%M:%S")
                    if (nu - gelezen_moment) > timedelta(hours=1):
                        laten_zien = False
                except Exception:
                    pass
            if laten_zien:
                st.markdown(f"<div class='request-card'>", unsafe_allow_html=True)
                st.markdown(
                    f"<b>EAN:</b> {row['EAN']}<br>"
                    f"<span style='font-size:0.94em;color:#009980bb'><b>Datum:</b> {row.get('Datum gekozen','-')}</span><br>"
                    f"<span style='font-size:0.94em;color:#009980bb'><b>Tijd:</b> {row.get('Tijd gekozen','-')}</span><br>"
                    f"<span style='font-size:0.94em;color:#009980bb'><b>Beoordeeld door:</b> {row.get('Beoordeeld door','')}</span><br>"
                    f"<b>Product:</b> {row['Productnaam']}<br>"
                    f"<b>Nazending:</b> {row['Nazending']}<br>"
                    f"<b>Bestelnummer:</b> {row['Bestelnummer']}<br>"
                    f"<b>Opmerking magazijn:</b> {row.get('Beoordeling opmerking','')}",
                    unsafe_allow_html=True)

                # FOTO PREVIEW hier:
                fotos = []
                try: fotos = json.loads(row.get("Fotos", "[]"))
                except: pass
                preview_this = False
                if fotos:
                    foto_row = st.columns(len(fotos))
                    for j, foto in enumerate(fotos):
                        if os.path.exists(foto):
                            with foto_row[j]:
                                st.image(foto, width=60)
                                if st.button("👁️", key=f"preview_siu_{row['ID']}_{j}"):
                                    st.session_state.preview_foto = foto
                                    st.session_state.preview_idx = f"siu_{row['ID']}_{j}"
                                    st.rerun()
                            if (
                                st.session_state.preview_foto == foto
                                and st.session_state.preview_idx == f"siu_{row['ID']}_{j}"
                            ):
                                preview_this = True
                        else:
                            st.write("_Foto ontbreekt_")
                else:
                    st.write("_Geen foto's_")
                if preview_this:
                    with st.expander("🔍 Preview foto", expanded=True):
                        st.image(st.session_state.preview_foto, use_container_width=True, caption="Klik buiten deze preview om te sluiten.")
                        if st.button("Sluit preview", key=f"sluit_preview_siu_{row['ID']}_{j}"):
                            st.session_state.preview_foto = None
                            st.session_state.preview_idx = None
                            st.rerun()

                col1, col2 = st.columns([2, 1])
                if not gelezen:
                    if col2.button("✔️ Ik heb dit gelezen", key=f"gelezen_{row['ID']}"):
                        df.loc[df["ID"] == row["ID"], "Niet op voorraad gelezen"] = "Ja"
                        df.loc[df["ID"] == row["ID"], "Niet op voorraad gelezen tijd"] = nu.strftime("%Y-%m-%d %H:%M:%S")
                        df.to_excel(NAZENDINGEN_BESTAND, index=False)
                        st.rerun()
                else:
                    col2.success("Afgehandeld (verdwijnt na 1 uur)")
                st.markdown("</div>", unsafe_allow_html=True)
    op_voorraad_df = df[df["Status"] == "Op voorraad"].copy()
    if not op_voorraad_df.empty:
        op_voorraad_df["Datum aanvraag sort"] = pd.to_datetime(op_voorraad_df["Datum aanvraag"], errors="coerce")
        op_voorraad_df = op_voorraad_df.sort_values("Datum aanvraag sort", ascending=False)
        st.markdown("#### SIU-nummer invoeren voor op voorraad nazendingen")
        for _, row in op_voorraad_df.iterrows():
            st.markdown(f"<div class='request-card'>", unsafe_allow_html=True)
            cols = st.columns([1.5,1.4,2.3,2.2,2.1,1.2])
            cols[0].markdown(
                f"<div class='ean-container'><b>EAN:</b> {row['EAN']}</div>"
                f"<span style='font-size:0.94em;color:#009980bb'><b>Datum:</b> {row.get('Datum gekozen','-')}</span><br>"
                f"<span style='font-size:0.94em;color:#009980bb'><b>Tijd:</b> {row.get('Tijd gekozen','-')}</span><br>"
                f"<span style='font-size:0.94em;color:#009980bb'><b>Beoordeeld door:</b> {row.get('Beoordeeld door','')}</span>",
                unsafe_allow_html=True
            )
            cols[1].markdown(f"**Product:**<br>{row['Productnaam']}<br><b>Bestelnummer:</b> {row['Bestelnummer']}", unsafe_allow_html=True)
            cols[2].markdown(f"**Nazending:**<br>{row['Nazending']}", unsafe_allow_html=True)
            cols[3].markdown(f"**Opmerking magazijn:**<br>{row.get('Beoordeling opmerking','')}", unsafe_allow_html=True)
            
            # FOTO PREVIEW hier:
            fotos = []
            try: fotos = json.loads(row.get("Fotos", "[]"))
            except: pass
            preview_this = False
            if fotos:
                foto_row = st.columns(len(fotos))
                for j, foto in enumerate(fotos):
                    if os.path.exists(foto):
                        with foto_row[j]:
                            st.image(foto, width=60)
                            if st.button("👁️", key=f"preview_siu_{row['ID']}_{j}"):
                                st.session_state.preview_foto = foto
                                st.session_state.preview_idx = f"siu_{row['ID']}_{j}"
                                st.rerun()
                        if (
                            st.session_state.preview_foto == foto
                            and st.session_state.preview_idx == f"siu_{row['ID']}_{j}"
                        ):
                            preview_this = True
                    else:
                        st.write("_Foto ontbreekt_")
            else:
                st.write("_Geen foto's_")
            if preview_this:
                with st.expander("🔍 Preview foto", expanded=True):
                    st.image(st.session_state.preview_foto, use_container_width=True, caption="Klik buiten deze preview om te sluiten.")
                    if st.button("Sluit preview", key=f"sluit_preview_siu_{row['ID']}_{j}"):
                        st.session_state.preview_foto = None
                        st.session_state.preview_idx = None
                        st.rerun()
            
            siu = cols[4].text_input("SIU-nummer invoeren", value=str(row.get("SIU-nummer","")), key=f"siu_{row['ID']}")
            if cols[5].button("SIU opslaan", key=f"save_siu_{row['ID']}"):
                df.loc[df["ID"] == row["ID"], "SIU-nummer"] = str(siu)
                df.loc[df["ID"] == row["ID"], "Status"] = "SIU ingevoerd"
                df.to_excel(NAZENDINGEN_BESTAND, index=False)
                st.success("SIU-nummer opgeslagen!")
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.info("Geen op voorraad aanvragen om af te handelen.")

# --------- TAB 4: Versturen magazijn ---------
with tab4:
    instellingen = laad_instellingen()
    TEAMLEDEN = instellingen["teamleden"]
    stats_cards(df)
    st.markdown("### Magazijn: pakketten verzenden")
    siu_df = df[df["Status"] == "SIU ingevoerd"].copy()
    if not siu_df.empty:
        siu_df["Datum aanvraag sort"] = pd.to_datetime(siu_df["Datum aanvraag"], errors="coerce")
        siu_df = siu_df.sort_values("Datum aanvraag sort", ascending=False)
        for _, row in siu_df.iterrows():
            st.markdown(f"<div class='request-card'>", unsafe_allow_html=True)
            cols = st.columns([1.5,1.4,2.3,1.8,1.2,2.0])
            cols[0].markdown(
                f"<div class='ean-container'><b>EAN:</b> {row['EAN']}</div>"
                f"<span style='font-size:0.94em;color:#009980bb'><b>Datum:</b> {row.get('Datum gekozen','-')}</span><br>"
                f"<span style='font-size:0.94em;color:#009980bb'><b>Tijd:</b> {row.get('Tijd gekozen','-')}</span><br>"
                f"<span style='font-size:0.94em;color:#009980bb'><b>Beoordeeld door:</b> {row.get('Beoordeeld door','')}</span>",
                unsafe_allow_html=True
            )
            cols[1].markdown(f"**Product:**<br>{row['Productnaam']}<br><b>Bestelnummer:</b> {row['Bestelnummer']}", unsafe_allow_html=True)
            cols[2].markdown(f"**Nazending:**<br>{row['Nazending']}", unsafe_allow_html=True)
            cols[3].markdown(f"**SIU-nummer:**<br>{row.get('SIU-nummer','')}", unsafe_allow_html=True)

            # FOTO PREVIEW hier:
            fotos = []
            try: fotos = json.loads(row.get("Fotos", "[]"))
            except: pass
            preview_this = False
            if fotos:
                foto_row = st.columns(len(fotos))
                for j, foto in enumerate(fotos):
                    if os.path.exists(foto):
                        with foto_row[j]:
                            st.image(foto, width=60)
                            if st.button("👁️", key=f"preview_verstuur_{row['ID']}_{j}"):
                                st.session_state.preview_foto = foto
                                st.session_state.preview_idx = f"verstuur_{row['ID']}_{j}"
                                st.rerun()
                        if (
                            st.session_state.preview_foto == foto
                            and st.session_state.preview_idx == f"verstuur_{row['ID']}_{j}"
                        ):
                            preview_this = True
                    else:
                        st.write("_Foto ontbreekt_")
            else:
                st.write("_Geen foto's_")
            if preview_this:
                with st.expander("🔍 Preview foto", expanded=True):
                    st.image(st.session_state.preview_foto, use_container_width=True, caption="Klik buiten deze preview om te sluiten.")
                    if st.button("Sluit preview", key=f"sluit_preview_verstuur_{row['ID']}_{j}"):
                        st.session_state.preview_foto = None
                        st.session_state.preview_idx = None
                        st.rerun()

            with cols[5]:
                verzonden_door = st.selectbox("Verzonden door:", options=TEAMLEDEN, key=f"verz_{row['ID']}")
                colA, colB = st.columns([1,1])
                with colA:
                    pakket_kar = st.checkbox("Pakket ligt op de kar?", key=f"kar_{row['ID']}")
                with colB:
                    if st.button("✅ Markeer als verzonden", key=f"verzend_{row['ID']}"):
                        if not pakket_kar:
                            st.warning("Vink eerst aan dat het pakket op de kar ligt.")
                        else:
                            df.loc[df["ID"] == row["ID"], "Status"] = "Verzonden"
                            df.loc[df["ID"] == row["ID"], "Verzonden door"] = verzonden_door
                            df.loc[df["ID"] == row["ID"], "Datum verzending"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            df.to_excel(NAZENDINGEN_BESTAND, index=False)
                            st.success("Nazending gemarkeerd als verzonden!")
                            st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.info("Geen pakketten klaar om te verzenden.")

# --------- TAB 5: Verzonden pakketten ---------
with tab5:
    instellingen = laad_instellingen()
    BEWAAR_UUR = instellingen["bewaar_uur"]
    stats_cards(df)
    st.markdown(f"### Overzicht van verzonden nazendingen (laatste {BEWAAR_UUR} uur)")
    df_show = df[df["Status"] == "Verzonden"].copy()
    if not df_show.empty:
        df_show["Datum verzending dt"] = pd.to_datetime(df_show["Datum verzending"], errors="coerce")
        nu = datetime.now()
        df_show = df_show[df_show["Datum verzending dt"].notna()]
        df_show = df_show[(nu - df_show["Datum verzending dt"]) < timedelta(hours=BEWAAR_UUR)]
        df_show = df_show.sort_values("Datum verzending dt", ascending=False)
        for _, row in df_show.iterrows():
            verzend_moment = row["Datum verzending dt"]
            if pd.isnull(verzend_moment):
                resterend = "Onbekend"
            else:
                deadline = verzend_moment + timedelta(hours=BEWAAR_UUR)
                rest_td = deadline - nu
                seconden = int(rest_td.total_seconds())
                if seconden < 0:
                    seconden = 0
                uren = seconden // 3600
                minuten = (seconden % 3600) // 60
                secs = seconden % 60
                resterend = f"{uren:02d}:{minuten:02d}:{secs:02d}"
            st.markdown(
                f"<div style='background:#e7f7f2;padding:9px 14px 8px 14px;border-radius:13px;"
                f"font-size:1.09em;font-weight:600;color:#009980;margin-bottom:6px;margin-top:7px;'>"
                f"Deze aanvraag wordt automatisch verwijderd over <span id='timer_{row['ID']}'><b>{resterend}</b></span>."
                f"</div>",
                unsafe_allow_html=True
            )
            st.markdown(f"<div class='request-card'>", unsafe_allow_html=True)
            cols = st.columns([1.5,1.5,2.3,2.2,1.3,1.2,0.2])
            cols[0].markdown(
                f"<div class='ean-container'><b>EAN:</b> {row['EAN']}</div>"
                f"<span style='font-size:0.91em;color:#009980bb'><b>Datum:</b> {row.get('Datum gekozen','-')}</span><br>"
                f"<span style='font-size:0.91em;color:#009980bb'><b>Tijd:</b> {row.get('Tijd gekozen','-')}</span><br>"
                f"<span style='font-size:0.91em;color:#009980bb'><b>Verzonden door:</b> {row.get('Verzonden door','')}</span>",
                unsafe_allow_html=True
            )
            cols[1].markdown(f"**Product:**<br>{row['Productnaam']}<br><b>Bestelnummer:</b> {row['Bestelnummer']}", unsafe_allow_html=True)
            cols[2].markdown(f"**Nazending:**<br>{row['Nazending']}", unsafe_allow_html=True)
            cols[3].markdown(progress_html(row['Status']), unsafe_allow_html=True)
            cols[4].markdown(status_chip(row['Status']), unsafe_allow_html=True)
            
            # FOTO PREVIEW hier:
            fotos = []
            try: fotos = json.loads(row.get("Fotos", "[]"))
            except: pass
            preview_this = False
            if fotos:
                foto_row = st.columns(len(fotos))
                for j, foto in enumerate(fotos):
                    if os.path.exists(foto):
                        with foto_row[j]:
                            st.image(foto, width=60)
                            if st.button("👁️", key=f"preview_verzonden_{row['ID']}_{j}"):
                                st.session_state.preview_foto = foto
                                st.session_state.preview_idx = f"verzonden_{row['ID']}_{j}"
                                st.rerun()
                        if (
                            st.session_state.preview_foto == foto
                            and st.session_state.preview_idx == f"verzonden_{row['ID']}_{j}"
                        ):
                            preview_this = True
                    else:
                        st.write("_Foto ontbreekt_")
            else:
                st.write("_Geen foto's_")
            if preview_this:
                with st.expander("🔍 Preview foto", expanded=True):
                    st.image(st.session_state.preview_foto, use_container_width=True, caption="Klik buiten deze preview om te sluiten.")
                    if st.button("Sluit preview", key=f"sluit_preview_verzonden_{row['ID']}_{j}"):
                        st.session_state.preview_foto = None
                        st.session_state.preview_idx = None
                        st.rerun()

            st.markdown("</div>", unsafe_allow_html=True)
        st.info(f"Verzonden pakketten verdwijnen automatisch uit dit overzicht na {BEWAAR_UUR} uur.")
        st.markdown("""
<script>
function updateTimers() {
    var timers = document.querySelectorAll('[id^="timer_"]');
    timers.forEach(function(timerElem) {
        var timeText = timerElem.textContent.trim();
        if (timeText.match(/^\d\d:\d\d:\d\d$/)) {
            var parts = timeText.split(":");
            var totalSeconds = (+parts[0])*3600 + (+parts[1])*60 + (+parts[2]);
            if (totalSeconds > 0) {
                totalSeconds -= 1;
                var h = String(Math.floor(totalSeconds/3600)).padStart(2,'0');
                var m = String(Math.floor((totalSeconds%3600)/60)).padStart(2,'0');
                var s = String(totalSeconds%60).padStart(2,'0');
                timerElem.innerHTML = "<b>"+h+":"+m+":"+s+"</b>";
            }
        }
    });
    setTimeout(updateTimers, 1000);
}
setTimeout(updateTimers, 1000);
</script>
""", unsafe_allow_html=True)
    else:
        st.info(f"Er zijn geen verzonden aanvragen die minder dan {BEWAAR_UUR} uur geleden zijn verstuurd.")

# --------- TAB 6: Instellingen ---------
with tab6:
    instellingen = laad_instellingen()
    st.header("⚙️ Instellingen")

    # 1. Teamleden beheren
    st.subheader("Teamleden beheren")
    nieuwe_naam = st.text_input("Nieuw teamlid toevoegen", key="nieuw_teamlid_input")
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

    # 2. Bewaarperiode verzonden pakketten
    st.subheader("Maximale bewaartijd verzonden pakketten")
    nieuw_uur = st.slider("Aantal uur", min_value=6, max_value=72, value=instellingen.get("bewaar_uur", 26), step=1)
    if nieuw_uur != instellingen.get("bewaar_uur", 26):
        instellingen["bewaar_uur"] = nieuw_uur
        opslaan_instellingen(instellingen)
        st.success(f"Nieuwe bewaarperiode: {nieuw_uur} uur")
        st.rerun()
    st.info(f"Pakketten verdwijnen nu automatisch na **{instellingen['bewaar_uur']} uur** uit tabblad 'Verzonden pakketten'.")

    st.divider()

    # 3. Back-up & export
    st.subheader("Back-up & export")
    if st.button("📤 Download Excel-backup"):
        with open(NAZENDINGEN_BESTAND, "rb") as f:
            st.download_button(
                label="Download nazendingen.xlsx",
                data=f,
                file_name="nazendingen_backup.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    if st.button("📤 Download als CSV"):
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="Download nazendingen.csv",
            data=csv,
            file_name="nazendingen_backup.csv",
            mime="text/csv"
        )

    st.divider()

    # 4. Data resetten (alles wissen)
    st.subheader("⚠️ Data resetten (let op!)")
    if st.button("🧨 Wis alle aanvragen & zet alles terug naar 0"):
        os.remove(NAZENDINGEN_BESTAND) if os.path.exists(NAZENDINGEN_BESTAND) else None
        df = pd.DataFrame(columns=cols_excel)
        df.to_excel(NAZENDINGEN_BESTAND, index=False)
        maak_backup() 
        st.success("Alle data gewist & systeem teruggezet naar leeg!")
        st.rerun()

