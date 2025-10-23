# ======================================================
# 🌌 Streamlit Dashboard : Chasseur d’Aurores Boréales
# Auteur : Adjimon Jérôme
# ======================================================

import streamlit as st
import pandas as pd
import requests
import plotly.express as px
from datetime import datetime
from geopy.geocoders import Nominatim
import time

# ------------------------------------------------------
# 1️⃣ CONFIG
st.set_page_config(page_title="Chasseur d’Aurores", layout="wide")

URLS = {
    "boulder_k_index": "https://services.swpc.noaa.gov/json/boulder_k_index_1m.json",
    "aurora_ovation": "https://services.swpc.noaa.gov/json/ovation_aurora_latest.json",
    "solar_flux": "https://services.swpc.noaa.gov/json/f107_cm_flux.json"
}

# ------------------------------------------------------
# 2️⃣ UTILITAIRES

@st.cache_data(ttl=600)
def load_json(url):
    """Charge les données JSON depuis NOAA avec cache de 10 min."""
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"Erreur de chargement : {e}")
        return None


@st.cache_data(ttl=3600)
def reverse_geocode(lat, lon):
    """Convertit lat/lon en nom de lieu."""
    geolocator = Nominatim(user_agent="aurora_app")
    try:
        location = geolocator.reverse((lat, lon), language="en", timeout=10)
        if location and "address" in location.raw:
            addr = location.raw["address"]
            return addr.get("city") or addr.get("town") or addr.get("state") or addr.get("country")
    except:
        return None
    return None

# ------------------------------------------------------
# 3️⃣ SIDEBAR

st.sidebar.title("🌌 Paramètres")
show_map = st.sidebar.checkbox("Afficher la carte mondiale", True)
show_k = st.sidebar.checkbox("Afficher l’indice K", True)
show_flux = st.sidebar.checkbox("Afficher le flux solaire F10.7", True)

st.sidebar.info("Source : NOAA SWPC Data Services")

# ------------------------------------------------------
# 4️⃣ Indice K (activité géomagnétique)

if show_k:
    st.header("🧭 Indice K en temps réel (Station Boulder)")
    data_k = load_json(URLS["boulder_k_index"])
    if data_k:
        df_k = pd.DataFrame(data_k)
        time_col = "time_tag" if "time_tag" in df_k else "time_tag_str"
        df_k["time"] = pd.to_datetime(df_k[time_col])
        k_col = [c for c in df_k.columns if 'k' in c.lower()][0]
        fig_k = px.line(df_k, x="time", y=k_col, title="Indice K - Activité géomagnétique", markers=True)
        fig_k.add_hline(y=5, line_dash="dash", line_color="red", annotation_text="Seuil d’aurore (K≥5)")
        st.plotly_chart(fig_k, use_container_width=True)
    else:
        st.warning("Impossible de charger l’indice K")

# ------------------------------------------------------
# 5️⃣ Carte mondiale des aurores

if show_map:
    st.header("🗺️ Carte mondiale des aurores boréales (OVATION)")
    aurora = load_json(URLS["aurora_ovation"])
    if aurora and "coordinates" in aurora:
        df_aurora = pd.DataFrame(aurora["coordinates"], columns=["lat", "lon", "prob"])
        df_aurora["lieu"] = df_aurora.apply(lambda r: reverse_geocode(r.lat, r.lon), axis=1)
        df_aurora["lieu"] = df_aurora["lieu"].fillna("Inconnu")

        fig_map = px.scatter_geo(
            df_aurora,
            lat="lat",
            lon="lon",
            color="prob",
            hover_name="lieu",
            color_continuous_scale="plasma",
            projection="natural earth",
            title="Probabilité d’aurore (%)"
        )
        st.plotly_chart(fig_map, use_container_width=True)
    else:
        st.warning("Données OVATION non disponibles.")

# ------------------------------------------------------
# 6️⃣ Flux solaire F10.7

if show_flux:
    st.header("☀️ Activité Solaire : Flux F10.7")
    flux_data = load_json(URLS["solar_flux"])
    if flux_data:
        df_flux = pd.DataFrame(flux_data)
        time_col = "time_tag" if "time_tag" in df_flux else "time_tag_str"
        df_flux["time"] = pd.to_datetime(df_flux[time_col])
        flux_col = [c for c in df_flux.columns if 'flux' in c.lower()][0]
        fig_flux = px.line(df_flux, x="time", y=flux_col, title="Flux solaire F10.7 (activité radio du Soleil)")
        st.plotly_chart(fig_flux, use_container_width=True)
    else:
        st.warning("Impossible de charger les données de flux solaire.")

# ------------------------------------------------------
# 7️⃣ Conclusion
st.success("🌠 Dashboard mis à jour avec les données NOAA en temps réel !")
st.caption("Dernière actualisation : " + datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"))
