import streamlit as st
import streamlit.components.v1 as components
import plotly.express as px
import plotly.graph_objects as go
import requests
import pandas as pd
import datetime as dt



## IMPORTATION DES FONCTIONS
from model.functions import get_kp_series
from model.functions import get_owm_current
from model.functions import (
    geocode_place, get_kp_now, get_weather, darkness_flag,
    chance_score, score_label
)
from pathlib import Path
from model.alerts import send_aurora_alert_email, should_send_alert, validate_email


# ============================================
# TRADUCTION DES NOMS DE PAYS
# ============================================

def translate_country_to_english(place: str) -> str:
    """
    Traduit les noms de pays français en anglais pour l'API de géocodage.
    Permet aux utilisateurs d'entrer "Stockholm, Suède" au lieu de "Stockholm, Sweden".
    """
    translations = {
        # Pays nordiques (destinations aurores)
        "Suède": "Sweden",
        "Norvège": "Norway", 
        "Finlande": "Finland",
        "Islande": "Iceland",
        "Danemark": "Denmark",
        
        # Amérique du Nord
        "Canada": "Canada",  # Identique
        "États-Unis": "United States",
        "USA": "United States",
        "Etats-Unis": "United States",
        "Amérique": "United States",
        
        # Europe
        "France": "France",  # Identique
        "Allemagne": "Germany",
        "Royaume-Uni": "United Kingdom",
        "Angleterre": "United Kingdom",
        "Écosse": "Scotland",
        "Ecosse": "Scotland",
        "Espagne": "Spain",
        "Italie": "Italy",
        "Suisse": "Switzerland",
        "Belgique": "Belgium",
        "Pays-Bas": "Netherlands",
        "Hollande": "Netherlands",
        "Autriche": "Austria",
        "Portugal": "Portugal",
        "Grèce": "Greece",
        
        # Autres
        "Russie": "Russia",
        "Japon": "Japan",
        "Chine": "China",
    }
    
    # Remplacer chaque pays français par son équivalent anglais
    place_en = place
    for fr, en in translations.items():
        if fr in place:
            place_en = place.replace(fr, en)
            break
    
    return place_en


# ---- Configuration de la page ---- #
# ✅ CETTE LIGNE DOIT ÊTRE LA PREMIÈRE COMMANDE STREAMLIT !
st.set_page_config(page_title="AurorAlerte", page_icon="🌌", layout="wide")

# --- Image bannière (fichier local)
BANNER = Path(__file__).parent / "assets" / "aurora_banner.jpg"

if BANNER.exists():
    st.image(str(BANNER), width=1500)
    #st.caption("📸 Photo par Jon Anders Dalan sur Unsplash")  


# -----------------------------
# Barre latérale (paramètres)
# -----------------------------
st.sidebar.header("🔭 Paramètres")

# Zone de texte avec exemple et aide
place = st.sidebar.text_input(
    "Localisation (ville, pays)", 
    value="Stockholm, Suède",
    help="💡 Vous pouvez utiliser les noms français (Suède, Norvège, Finlande) ou anglais (Sweden, Norway, Finland)"
)

quick = st.sidebar.selectbox(
    "Localisations rapides",
    ["—", 
     "Abisko, Suède", 
     "Kiruna, Suède", 
     "Stockholm, Suède", 
     "Tromsø, Norvège", 
     "Rotsund, Norvège", 
     "Kilpisjärvi, Finlande", 
     "Rovaniemi, Finlande", 
     "Banff, Canada", 
     "Fairbanks, États-Unis"]
)
if quick != "—":
    place = quick

w_kp   = st.sidebar.slider("Poids : Indice Kp",      0.0, 1.0, 0.50, 0.05)
w_sky  = st.sidebar.slider("Poids : Ciel dégagé",    0.0, 1.0, 0.35, 0.05)
w_dark = st.sidebar.slider("Poids : Obscurité",      0.0, 1.0, 0.15, 0.05)

refresh = st.sidebar.button("🔄 Actualiser les données")

# -----------------------------
# Rafraîchissement manuel du cache
# -----------------------------

if refresh:
    st.cache_data.clear()
    st.cache_resource.clear()
    st.rerun()

# AJOUTEZ :

st.sidebar.markdown("---")
st.sidebar.subheader("📧 Alertes Email")

alerts_enabled = st.sidebar.checkbox(
    "Activer les alertes email",
    value=False,
    help="Recevez un email quand les conditions sont favorables"
)

if alerts_enabled:
    email_config_ok = all([
        st.secrets.get("email", {}).get("smtp_server"),
        st.secrets.get("email", {}).get("sender_email"),
        st.secrets.get("email", {}).get("sender_password")
    ])
    
    if not email_config_ok:
        st.sidebar.error("❌ Configuration email manquante. Voir secrets.toml")
    else:
        recipient_email = st.sidebar.text_input(
            "Votre email",
            placeholder="votre.email@exemple.com"
        )
        
        kp_threshold = st.sidebar.slider(
            "Seuil Kp minimum",
            3.0, 9.0, 5.0, 0.5
        )
        
        cooldown_hours = st.sidebar.slider(
            "Intervalle entre alertes (h)",
            0.5, 6.0, 1.0, 0.5
        )
        
        if 'last_alert_time' not in st.session_state:
            st.session_state.last_alert_time = None
        if 'alerts_sent_count' not in st.session_state:
            st.session_state.alerts_sent_count = 0


# -----------------------------
# Récupération des données principales
# -----------------------------

# ✅ TRADUCTION AUTOMATIQUE DES NOMS DE PAYS (français → anglais)
place_en = translate_country_to_english(place)

geo = geocode_place(place_en)
if not geo:
    st.error(f"❌ Impossible de trouver la localisation « {place} ».")
    st.info("""
    💡 **Astuces :**
    - Essayez avec le nom en anglais : "Stockholm, Sweden"
    - Vérifiez l'orthographe de la ville
    - Utilisez les localisations rapides dans le menu déroulant ci-dessus
    """)
    st.stop()

lat, lon, tz = geo["lat"], geo["lon"], geo["timezone"]

# Indice Kp
kp_now, kp_time = None, None
try:
    kp_now, kp_time = get_kp_now()
except Exception as e:
    st.warning(f"⚠️ Impossible de récupérer l'indice Kp : {e}")

# Obscurité
dark, sunrise_utc, sunset_utc = 0, None, None
try:
    dark, sunrise_utc, sunset_utc = darkness_flag(lat, lon)
except Exception as e:
    st.warning(f"⚠️ Impossible de récupérer les heures de lever/coucher du soleil : {e}")

# Météo & couverture nuageuse actuelle
wx, cloud_now = None, None
try:
    wx = get_weather(lat, lon, tz)
    # Rendre les heures météo conscientes du fuseau horaire
    if wx is not None and not wx.empty:
        if wx["time"].dt.tz is None:
            wx["time"] = wx["time"].dt.tz_localize(tz)
        else:
            wx["time"] = wx["time"].dt.tz_convert(tz)

        now_local = pd.Timestamp.now(tz=tz)
        idx = (wx["time"] - now_local).abs().idxmin()
        cloud_now = float(wx.loc[idx, "cloud_total"])

    cloud_now = float(wx.loc[idx, "cloud_total"])

except Exception as e:
    st.warning(f"⚠️ Impossible de récupérer les données météo : {e}")

# Score de probabilité
score = chance_score(kp_now, cloud_now, dark, w1=w_kp, w2=w_sky, w3=w_dark)


# APRÈS : score = chance_score(kp_now, cloud_now, dark, w1=w_kp, w2=w_sky, w3=w_dark)
# AJOUTEZ :

if alerts_enabled and email_config_ok and recipient_email and validate_email(recipient_email):
    if kp_now and should_send_alert(kp_now, kp_threshold, st.session_state.last_alert_time, cooldown_hours):
        smtp_config = {
            'smtp_server': st.secrets['email']['smtp_server'],
            'smtp_port': st.secrets['email']['smtp_port'],
            'sender_email': st.secrets['email']['sender_email'],
            'sender_password': st.secrets['email']['sender_password']
        }
        
        with st.spinner("📧 Envoi de l'alerte..."):
            success, message = send_aurora_alert_email(
                recipient_email, kp_now, f"{geo['name']}, {geo['country']}",
                score, cloud_now, dark, smtp_config
            )
        
        if success:
            st.session_state.last_alert_time = pd.Timestamp.now()
            st.session_state.alerts_sent_count += 1
            st.sidebar.success(f"✅ Alerte envoyée ! Kp={kp_now:.1f}")
        else:
            st.sidebar.error(f"❌ {message}")
    else:
        if st.session_state.last_alert_time and kp_now and kp_now >= kp_threshold:
            time_since = (pd.Timestamp.now() - st.session_state.last_alert_time).total_seconds() / 3600
            time_left = max(0, cooldown_hours - time_since)
            st.sidebar.info(f"⏳ Prochaine alerte dans {time_left:.1f}h")
            
            

# -----------------------------
# En-tête
# -----------------------------
st.title("🌌 Alerte d'Aurores Boréales")
st.caption(f"📍 Localisation : **{geo['name']}** ({geo['country']}) — lat {lat:.3f}, lon {lon:.3f}, fuseau horaire {tz}")

# -----------------------------
# Onglets
# -----------------------------
# APRÈS (7 onglets)
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "🌍 Vue d'ensemble",
    "🗺️ Carte mondiale",  # ← NOUVEAU
    "🌤 Météo actuelle", 
    "📅 Prévisions météo", 
    "📷 Webcams", 
    "🌌 Prévisions aurores", 
    "ℹ️ À propos"
])


kp_series = pd.DataFrame()  # toujours défini, même si la récupération échoue
try:
    kp_series = get_kp_series(limit_minutes=240)  # dernières ~4 heures
except Exception as e:
    st.warning(f"⚠️ Impossible de récupérer la série Kp : {e}")


# -------- Vue d'ensemble --------
with tab1:
    st.subheader("🌍 Vue d'ensemble")
    st.markdown(" ")
    
    # --- Jauge Indice Kp ---
    fig_kp = go.Figure(go.Indicator(
        mode="gauge+number",
        value=kp_now if kp_now is not None else 0,
        number={'valueformat': '.1f'},
        title={'text': "Indice Kp"},
        gauge={
            "axis": {"range": [0, 9]},
            "bar": {"thickness": 0.30, "color": "white"},
            "steps": [
                {"range": [0, 3], "color": "#c0392b"},
                {"range": [3, 6], "color": "#e3b505"},
                {"range": [6, 9], "color": "#2e8540"},
            ],
        }
    ))
    fig_kp.update_layout(height=250, margin=dict(l=25,r=25,t=30,b=10))

    # --- Jauge Ciel dégagé ---
    fig_cloud = go.Figure(go.Indicator(
        mode="gauge+number",
        value=100 - (cloud_now if cloud_now is not None else 100),
        number={'suffix': "%"},
        title={'text': "Ciel dégagé %"},
        gauge={
            "axis": {"range": [0, 100]},
            "bar": {"thickness": 0.30, "color": "white"},
            "steps": [
                {"range": [0, 30], "color": "#c0392b"},
                {"range": [30, 70], "color": "#e3b505"},
                {"range": [70, 100], "color": "#2e8540"},
            ]
        }
    ))
    fig_cloud.update_layout(height=250, margin=dict(l=25,r=25,t=30,b=10))

    # --- Jauge Score de probabilité ---
    fig_score = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        number={'valueformat': '.2f'},
        title={'text': f"Score de Probabilité {score_label(score)}"},
        gauge={
            "axis": {"range": [0, 1]},
            "bar": {"thickness": 0.30, "color": "white"},
            "steps": [
                {"range": [0, 0.4], "color": "#c0392b"},
                {"range": [0.4, 0.7], "color": "#e3b505"},
                {"range": [0.7, 1.0], "color": "#2e8540"},
            ]
        }
    ))
    fig_score.update_layout(height=250, margin=dict(l=25,r=25,t=30,b=10))


    # Disposition avec espacement (5 colonnes)
    col1, col_sp1, col2, col_sp2, col3 = st.columns([1, 0.2, 1, 0.2, 1])

    col1.plotly_chart(fig_kp, use_container_width=True)
    col1.caption("💡 **Indice Kp** : Mesure l'activité géomagnétique. Plus il est élevé, plus les aurores sont visibles au sud.")
    
    col2.plotly_chart(fig_cloud, use_container_width=True)
    col2.caption("💡 **Ciel dégagé** : Pourcentage de ciel sans nuages. 70%+ = bonnes conditions d'observation.")
    
    col3.plotly_chart(fig_score, use_container_width=True)
    col3.caption("💡 **Score global** : Combine Kp, météo et obscurité. 0.7+ = excellentes conditions !")


    st.caption("""
**Comment lire ces indicateurs :**
- **Kp > 5** = activité aurorale forte (aurores visibles)
- **Ciel dégagé %** : plus c'est élevé, mieux c'est
- **Score de Probabilité** : combine Kp, nuages et obscurité sur une échelle de 0 à 1
  - 0.0-0.4 : Faible probabilité 🔴
  - 0.4-0.7 : Probabilité moyenne 🟡  
  - 0.7-1.0 : Excellente probabilité 🟢
""")
    
    with st.expander("📊 Historique récent de l'indice Kp (4 dernières heures)"):
        if not kp_series.empty:
            # Graphique linéaire
            fig_kp_line = px.line(
                kp_series, x="time_tag", y="kp_index",
                labels={"time_tag": "Temps (UTC)", "kp_index": "Indice Kp (1-min)"},
                title="Indice Kp (1 minute) — récent"
            )
            st.plotly_chart(fig_kp_line, use_container_width=True)

            # Tableau
            st.dataframe(kp_series.tail(20), use_container_width=True)

            # Téléchargement CSV
            csv_bytes = kp_series.to_csv(index=False).encode("utf-8")
            st.download_button(
                "📥 Télécharger l'historique Kp (CSV)",
                data=csv_bytes,
                file_name=f"kp_recent_{pd.Timestamp.now(tz='UTC').strftime('%Y%m%d_%H%M')}Z.csv",
                mime="text/csv"
            )
        else:
            st.info("ℹ️ Aucune donnée Kp retournée par NOAA SWPC.")


    st.markdown("---")       

    st.caption("📡 Source de données : API Open-Meteo et NOAA SWPC (temps réel).")
   
with tab2:
    st.subheader("🗺️ Carte Mondiale des Probabilités d'Aurores")
    st.markdown(" ")
    
    # Récupérer l'indice Kp actuel
    kp_display = kp_now if kp_now is not None else 0
    
    # Message d'information
    st.info(f"""
    💡 **Indice Kp actuel : {kp_display:.1f}**
    
    Cette carte montre les latitudes où les aurores sont visibles selon l'indice Kp.
    Plus le Kp est élevé, plus les aurores sont visibles au sud.
    """)
    
    # Définition des zones selon Kp
    kp_zones = {
        0: 66.5, 1: 64.5, 2: 62.4, 3: 60.4, 4: 58.3,
        5: 56.3, 6: 54.2, 7: 52.2, 8: 50.1, 9: 48.1
    }
    
    lat_limit = kp_zones.get(int(kp_display), 66.5)
    
    # Création des données
    latitudes = list(range(90, 39, -5))
    colors, labels, sizes = [], [], []
    
    for lat in latitudes:
        if lat >= lat_limit:
            colors.append('rgba(46, 133, 64, 0.7)')
            labels.append('Zone visible')
            sizes.append(60)
        else:
            colors.append('rgba(192, 57, 43, 0.5)')
            labels.append('Hors zone')
            sizes.append(40)
    
    # Création de la carte
    fig = go.Figure()
    
    # Bandes de latitude
    for i, lat in enumerate(latitudes):
        lons = list(range(-180, 181, 20))
        lats = [lat] * len(lons)
        
        fig.add_trace(go.Scattergeo(
            lon=lons, lat=lats, mode='markers',
            marker=dict(size=sizes[i], color=colors[i], line=dict(width=0)),
            name=labels[i],
            showlegend=(i == 0 or (i == len(latitudes)//2 and labels[i] != labels[0])),
            hovertemplate=f'<b>Latitude {lat}°N</b><br>{labels[i]}<extra></extra>'
        ))
    
    # Ligne de limite
    lons_line = list(range(-180, 181, 5))
    lats_line = [lat_limit] * len(lons_line)
    
    fig.add_trace(go.Scattergeo(
        lon=lons_line, lat=lats_line, mode='lines',
        line=dict(color='gold', width=4, dash='dash'),
        name=f'Limite aurores (Kp {kp_display:.1f})',
        hovertemplate=f'<b>Limite visibilité</b><br>Latitude: {lat_limit:.1f}°N<extra></extra>'
    ))
    
    # Marqueur localisation actuelle
    fig.add_trace(go.Scattergeo(
        lon=[lon], lat=[lat], mode='markers+text',
        marker=dict(size=20, color='yellow', symbol='star', line=dict(width=2, color='black')),
        text=[geo['name']], textposition='top center',
        name='Votre localisation',
        hovertemplate=f"<b>{geo['name']}</b><br>Lat: {lat:.2f}°<br>Lon: {lon:.2f}°<extra></extra>"
    ))
    
    # Configuration
    fig.update_layout(
        title=dict(text=f"Visibilité des Aurores Boréales (Kp = {kp_display:.1f})", x=0.5, xanchor='center', font=dict(size=20)),
        geo=dict(
            projection_type='orthographic',
            projection_rotation=dict(lon=0, lat=70, roll=0),
            center=dict(lon=0, lat=70),
            showland=True, landcolor='rgb(243, 243, 243)',
            coastlinecolor='rgb(204, 204, 204)',
            showocean=True, oceancolor='rgb(230, 245, 255)',
            showcountries=True, countrycolor='rgb(204, 204, 204)',
            lataxis=dict(range=[40, 90]),
        ),
        height=650, showlegend=True,
        legend=dict(yanchor="top", y=0.99, xanchor="right", x=0.0, bgcolor='rgba(255, 255, 255, 0.8)')
    )
    
    st.plotly_chart(fig, use_container_width=True)
    st.markdown("---")
    
    # Tableau d'interprétation
    st.markdown("### 📊 Guide d'Interprétation des Latitudes")
    st.markdown(" ")
    
    interpretation_data = {
        "Kp": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
        "Latitude limite": ["66.5°N", "64.5°N", "62.4°N", "60.4°N", "58.3°N", "56.3°N", "54.2°N", "52.2°N", "50.1°N", "48.1°N"],
        "Régions visibles": [
            "🇬🇱 Groenland, Nord Islande", "🇮🇸 Islande, Nord Norvège",
            "🇳🇴 Tromsø, Nord Finlande", "🇫🇮 Rovaniemi, Nord Suède",
            "🇸🇪 Stockholm, Helsinki", "🏴󠁧󠁢󠁳󠁣󠁴󠁿 Écosse, Sud Norvège",
            "🇬🇧 Nord Angleterre", "🇬🇧 Londres, Amsterdam",
            "🇧🇪 Bruxelles, Paris Nord", "🇫🇷 Paris, Munich"
        ],
        "Fréquence": [
            "Toutes les nuits claires", "Très fréquent", "Fréquent",
            "Régulier", "Occasionnel", "Rare", "Très rare",
            "Exceptionnel", "Tempête majeure", "Tempête extrême"
        ]
    }
    
    df_interpretation = pd.DataFrame(interpretation_data)
    
    def highlight_current_kp(row):
        if row.name == int(kp_display):
            return ['background-color: #2e8540; color: white; font-weight: bold'] * len(row)
        return [''] * len(row)
    
    st.dataframe(df_interpretation.style.apply(highlight_current_kp, axis=1), use_container_width=True)
    st.markdown(" ")
    
    # Message selon Kp
    if kp_display >= 7:
        st.success(f"🎆 **Conditions EXCEPTIONNELLES !** Kp {kp_display:.1f} → Aurores jusqu'à {lat_limit:.1f}°N")
    elif kp_display >= 5:
        st.warning(f"🟡 **Bonnes conditions !** Kp {kp_display:.1f} → Aurores jusqu'à {lat_limit:.1f}°N")
    elif kp_display >= 3:
        st.info(f"🔵 **Conditions normales** Kp {kp_display:.1f} → Aurores jusqu'à {lat_limit:.1f}°N")
    else:
        st.info(f"⚪ **Activité faible** Kp {kp_display:.1f} → Limité aux régions polaires ({lat_limit:.1f}°N+)")
    
    st.markdown("---")
    
    # Guide d'utilisation
    st.markdown("### 💡 Comment Utiliser Cette Carte")
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        **🟢 Zone verte : Aurores visibles**
        - Au-dessus de la limite Kp
        - Bonnes chances d'observation
        - Vérifiez la météo locale
        
        **🔴 Zone rouge : Aurores non visibles**
        - En-dessous de la limite
        - Attendez une activité plus forte
        """)
    
    with col2:
        st.markdown("""
        **⭐ Étoile jaune : Votre position**
        - Votre localisation actuelle
        - Dans la zone verte ? GO ! 🎉
        
        **📏 Ligne dorée : Limite d'aurores**
        - Latitude minimale
        - Dépend du Kp
        """)
    
    st.markdown("---")
    st.caption("📡 Source : NOAA SWPC (indice Kp) + Modèle de latitude géomagnétique")


# -------- Météo actuelle (OpenWeatherMap) --------
with tab3:
    st.subheader("🌤 Météo Actuelle")
    st.markdown(" ")
    st.markdown(" ")

    api_key = st.secrets.get("OPENWEATHER_API_KEY")
    if not api_key:
        st.error("❌ Clé API OpenWeatherMap introuvable. Ajoutez-la dans `.streamlit/secrets.toml` sous OPENWEATHER_API_KEY.")
    else:
        try:
            # Utilise la fonction mise en cache
            owm = get_owm_current(lat, lon, api_key, units="metric")

            # Si limite de requêtes atteinte
            if isinstance(owm, dict) and owm.get("error") == "rate_limited":
                st.warning(owm["message"])
            else:
                # Première ligne : localisation + icône + description
                c1, c2, c3 = st.columns([0.2, 0.6, 0.8])

                if owm.get("icon_url"):
                    c1.image(owm["icon_url"], width=90)

                city = owm.get("city") or geo["name"]
                country = owm.get("country") or geo["country"]
                desc = (owm.get("desc", "") or "").lstrip("-–— ").capitalize()


                # Disposition sur deux lignes : ville/pays en grand + description en dessous
                c2.markdown(
                    f"""
                    <div style="text-align:center;">
                        <div style="font-size:24px; font-weight:600;">
                            {city}, {country}
                        </div>
                        <div style="font-size:18px; color:#fff;">
                            {desc}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                c3.markdown(" ")

                st.markdown("---")


                # Indicateurs clés
                k1, k2, k3, k4 = st.columns(4)
                k1.metric("Température (°C)", f"{owm['temp_c']:.1f}" if owm['temp_c'] is not None else "—")
                k2.metric("Ressenti (°C)", f"{owm['feels_like_c']:.1f}" if owm['feels_like_c'] is not None else "—")
                k3.metric("Humidité (%)", f"{owm['humidity_pct']}" if owm['humidity_pct'] is not None else "—")
                k4.metric("Nuages (%)", f"{owm['cloud_pct']}" if owm['cloud_pct'] is not None else "—")

                st.markdown("---")

                k5, k6 = st.columns([0.2, 0.6])
                k5.metric("Vent (m/s)", f"{owm['wind_ms']:.1f}" if owm['wind_ms'] is not None else "—")
                k6.metric("Pression (hPa)", f"{owm['pressure_hpa']}" if owm['pressure_hpa'] is not None else "—")
                
                st.markdown(" ")
                st.info("""
                💡 **Pourquoi c'est important :** 
                - **Nuages < 30%** : Bonnes chances de voir les aurores
                - **Vent fort** : Peut disperser les nuages rapidement
                - **Température basse** : Typique des nuits claires, idéal pour les aurores
                """)

        except Exception as e:
            st.error(f"❌ Impossible de récupérer les données OpenWeatherMap : {e}")

        st.markdown("---")
        st.caption("📡 Source de données : API OpenWeather (temps réel)")


# -------- Prévisions météo --------
with tab4:
    st.subheader("☁️ Prévisions Météo (48 prochaines heures)")
    st.markdown(" ")

    if wx is None or wx.empty:
        st.info("ℹ️ Données météo indisponibles.")
    else:
        # ---- Sous-onglets pour cette section
        sub1, sub2, sub3, sub4, sub5 = st.tabs([
            "🔍 Explorateur météo interactif",
            "☁️ Nuages",
            "🌡️ Température",
            "💨 Vent",
            "🌧️ Précipitations & Visibilité"
        ])

        # =====================================================================
        # 1) EXPLORATEUR MÉTÉO INTERACTIF
        # =====================================================================
        with sub1:
            # ---- Contrôles : choisir les variables à afficher
            st.markdown(" ")
            st.markdown("**Choisissez les variables à explorer**")
            st.markdown(" ")

            var_options = {
                "Nuages totaux (%)": "cloud_total",
                "Nuages bas (%)": "cloud_low",
                "Nuages moyens (%)": "cloud_mid",
                "Nuages hauts (%)": "cloud_high",
                "Température (°C)": "temp_c",
                "Point de rosée (°C)": "dewpoint_c",
                "Humidité relative (%)": "rh_pct",
                "Visibilité (km)": "visibility_km",
                "Vent (m/s)": "wind_ms",
                "Rafales (m/s)": "gust_ms",
                "Précipitations (mm)": "precip_mm",
                "Probabilité précip. (%)": "precip_prob",
            }
            default_vars = ["Nuages totaux (%)", "Probabilité précip. (%)", "Visibilité (km)"]

            picked_labels = st.multiselect(
                "Variables",
                options=list(var_options.keys()),
                default=default_vars,
                max_selections=5,
                help="Sélectionnez jusqu'à 5 variables à comparer sur la même chronologie."
            )

            picked_cols = [var_options[lbl] for lbl in picked_labels] or ["cloud_total"]
            pretty_map  = {v: k for k, v in var_options.items()}

            st.markdown(" ")

            # ---- Seuils d'observation optimaux
            st.markdown("**Fenêtres d'observation optimales**")
            st.markdown(" ")
            cloud_thresh  = st.slider("Nuages max (%)", 0, 100, 40, 5)
            precip_thresh = st.slider("Probabilité précip. max (%)", 0, 100, 20, 5)

            best_df = wx.copy()
            best_df["ok"] = (best_df["cloud_total"] <= cloud_thresh) & (best_df["precip_prob"] <= precip_thresh)
            suggested = best_df.loc[
                best_df["ok"], ["time", "cloud_total", "precip_prob", "visibility_km", "wind_ms"]
            ]

            # ---- Construction du DataFrame pour Plotly
            plot_df = wx[["time"] + picked_cols].copy()
            long_df = plot_df.melt(id_vars="time", var_name="variable", value_name="value")
            long_df["variable"] = long_df["variable"].map(pretty_map)

            # ---- Graphique Plotly interactif
            fig = px.line(
                long_df,
                x="time", y="value", color="variable",
                labels={"time": "Temps", "value": "", "variable": ""}
            )

            fig.update_layout(
                title=dict(
                    text="Explorateur Météo Interactif (48h)",
                    x=0.0, xanchor="left",
                    y=0.99, yanchor="top",
                    font=dict(size=20)
                ),
                hovermode="x unified",
                margin=dict(l=1, r=1, t=140, b=1),
                legend=dict(orientation="h", y=1.1, yanchor="bottom", x=0, xanchor="left")
            )

            fig.update_xaxes(
                rangeslider=dict(visible=True),
                rangeselector=dict(
                    x=0, xanchor="left",
                    y=1.50, yanchor="top",
                    buttons=[
                        dict(count=6,  label="6h",  step="hour", stepmode="backward"),
                        dict(count=12, label="12h", step="hour", stepmode="backward"),
                        dict(count=24, label="24h", step="hour", stepmode="backward"),
                        dict(step="all", label="Tout")
                    ]
                ),
                title_standoff=12
            )

            # ---- Texte de survol personnalisé avec unités
            units = {
                "Nuages totaux (%)": "%",
                "Nuages bas (%)": "%",
                "Nuages moyens (%)": "%",
                "Nuages hauts (%)": "%",
                "Température (°C)": "°C",
                "Point de rosée (°C)": "°C",
                "Humidité relative (%)": "%",
                "Visibilité (km)": " km",
                "Vent (m/s)": " m/s",
                "Rafales (m/s)": " m/s",
                "Précipitations (mm)": " mm",
                "Probabilité précip. (%)": "%"
            }
            for tr in fig.data:
                label = tr.name
                unit = units.get(label, "")
                tr.update(hovertemplate=f"%{{x|%Y-%m-%d %H:%M}}<br>{label}: %{{y}}{unit}<extra></extra>")

            # ---- Si nous avons des fenêtres suggérées, ajouter des marqueurs
            if not suggested.empty:
                anchor_series = pretty_map.get(picked_cols[0], "Nuages totaux (%)") if picked_cols else "Nuages totaux (%)"
                xs = suggested["time"]
                ys = long_df.loc[long_df["variable"] == anchor_series].set_index("time").reindex(xs)["value"]
                fig.add_scatter(
                    x=xs, y=ys,
                    mode="markers", name="Suggéré",
                    marker=dict(size=9, symbol="star", color="gold"),
                    hovertemplate="%{x|%Y-%m-%d %H:%M}<br>Fenêtre suggérée<extra></extra>"
                )

            # ---- Afficher le graphique
            st.markdown(" ")
            st.plotly_chart(fig, use_container_width=True)
            st.markdown(" ")
            st.info("💡 **Lecture du graphique :** Recherchez les périodes où les nuages sont bas (<30%), les précipitations faibles (<20%) et la visibilité haute (>10km). Ces fenêtres sont marquées par des étoiles dorées.")
            st.caption("💡 Utilisez le curseur et les boutons pour zoomer/défiler.")
            st.markdown("---")

            # ---- Afficher le tableau et le bouton de téléchargement
            if not suggested.empty:
                st.markdown("**Heures recommandées pour l'observation :**")
                st.dataframe(
                    suggested.rename(columns={
                        "time": "Heure",
                        "cloud_total": "Nuages (%)",
                        "precip_prob": "Prob. précip. (%)",
                        "visibility_km": "Visibilité (km)",
                        "wind_ms": "Vent (m/s)"
                    }),
                    use_container_width=True
                )
            else:
                st.info("ℹ️ Aucune heure ne correspond aux seuils. Essayez de les assouplir.")

            st.download_button(
                "📥 Télécharger les prévisions 48h (CSV)",
                data=wx.to_csv(index=False).encode("utf-8"),
                file_name="previsions_meteo_48h.csv",
                mime="text/csv"
            )

            st.markdown("---")
            st.caption("📡 Source de données : API Open-Meteo (temps réel).")


        # =====================================================================
        # 2) NUAGES
        # =====================================================================
        with sub2:
           
            left, right = st.columns(2)

            with left:
                fig_total = px.line(
                    wx, x="time", y="cloud_total",
                    labels={"time": "Temps", "cloud_total": "Couverture nuageuse (%)"},
                    title="Couverture Nuageuse Totale"
                )
                st.plotly_chart(fig_total, use_container_width=True)
                st.info("💡 **Idéal pour les aurores :** Moins de 30% de nuages. Les aurores se produisent à 100-400 km d'altitude, bien au-dessus des nuages.")

                st.markdown("---")

                st.caption("📡 Source de données : API Open-Meteo (temps réel).")

            with right:
                layers = wx[["time", "cloud_low", "cloud_mid", "cloud_high"]].melt(
                    id_vars="time", var_name="layer", value_name="cloud_pct"
                )
                layer_names = {
                    "cloud_low": "Nuages bas",
                    "cloud_mid": "Nuages moyens",
                    "cloud_high": "Nuages hauts"
                }
                layers["layer"] = layers["layer"].map(layer_names)
                fig_stack = px.area(
                    layers, x="time", y="cloud_pct", color="layer",
                    labels={"time": "Temps", "cloud_pct": "Nuages (%)", "layer": "Couche"},
                    title="Couches Nuageuses (Empilées)"
                )
                st.plotly_chart(fig_stack, use_container_width=True)
                st.info("💡 **Astuce :** Les nuages bas (0-2 km) bloquent le plus la vue. Les nuages hauts (6-12 km) sont souvent transparents aux aurores.")

                st.markdown("---")
                

        # =====================================================================
        # 3) TEMPÉRATURE
        # =====================================================================
        with sub3:
            fig_temp = px.line(
                wx, x="time", y=["temp_c", "dewpoint_c"],
                labels={"time": "Temps", "value": "°C", "variable": ""},
                title="Température & Point de Rosée (°C)"
            )
            # Traduire la légende
            fig_temp.for_each_trace(lambda t: t.update(name={
                'temp_c': 'Température',
                'dewpoint_c': 'Point de rosée'
            }.get(t.name, t.name)))
            
            st.plotly_chart(fig_temp, use_container_width=True)
            st.info("💡 **Indicateur de ciel clair :** Quand température et point de rosée sont proches, l'humidité est élevée = risque de brouillard/nuages. Un écart >5°C = air sec = ciel dégagé.")

            st.markdown("---")

            st.caption("📡 Source de données : API Open-Meteo (temps réel).")

        # =====================================================================
        # 4) VENT
        # =====================================================================
        with sub4:
            fig_wind = px.line(
                wx, x="time", y=["wind_ms", "gust_ms"],
                labels={"time": "Temps", "value": "m/s", "variable": ""},
                title="Vent & Rafales"
            )
            # Traduire la légende
            fig_wind.for_each_trace(lambda t: t.update(name={
                'wind_ms': 'Vent',
                'gust_ms': 'Rafales'
            }.get(t.name, t.name)))
            
            st.plotly_chart(fig_wind, use_container_width=True)
            st.info("💡 **Impact sur l'observation :** Un vent modéré (5-15 m/s) peut disperser les nuages rapidement. Attention : vent fort (>20 m/s) = difficulté à stabiliser un appareil photo.")

            st.markdown("---")

            st.caption("📡 Source de données : API Open-Meteo (temps réel).")

        # =====================================================================
        # 5) PRÉCIPITATIONS & VISIBILITÉ
        # =====================================================================
        with sub5:
            c1, c2 = st.columns(2)

            with c1:
                fig_prob = px.bar(
                    wx, x="time", y="precip_prob",
                    labels={"time": "Temps", "precip_prob": "Probabilité de précipitations (%)"},
                    title="Probabilité de Précipitations"
                )
                st.plotly_chart(fig_prob, use_container_width=True)
                st.info("💡 **Critique pour les aurores :** Précipitations (pluie/neige) = nuages épais garantis. Visez <20% de probabilité pour une bonne observation.")

                st.markdown("---")

                st.caption("📡 Source de données : API Open-Meteo (temps réel).")

            with c2:
                fig_vis = px.line(
                    wx, x="time", y="visibility_km",
                    labels={"time": "Temps", "visibility_km": "Visibilité (km)"},
                    title="Visibilité"
                )
                st.plotly_chart(fig_vis, use_container_width=True)
                st.info("💡 **Visibilité optimale :** >10 km = excellent. <5 km = brouillard/brume qui bloque la vue des aurores. Combine avec le % de nuages pour le meilleur résultat.")

                st.markdown("---")

                
# -------- Webcams --------
with tab5:
    st.subheader("📷 Webcams en Direct")
    st.markdown("Restez informé avec des vues en direct du ciel et des aurores depuis différents sites.")

    st.markdown(" ")
    st.markdown(" ")
    
    st.info("⚠️ **Note :** La disponibilité des webcams varie selon la saison et l'heure. Certains flux peuvent être hors ligne pendant les mois d'été (soleil de minuit) ou en maintenance.")

    st.markdown(" ")

    # Rangée 1
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### Parc National d'Abisko, Suède 🇸🇪")
        st.video("https://www.youtube.com/watch?v=TfOgRJr0Ab8")
        st.caption("🕐 En direct quand actif • Meilleure période : septembre-mars")

    with col2:
        st.markdown("#### Lac Apavatn, Islande 🇮🇸")
        st.video("https://www.youtube.com/watch?v=feB3BzDj9mo")
        st.caption("🕐 En direct quand actif • Saison des aurores : septembre-avril")

    st.markdown("---")

    # Rangée 2
    col3, col4 = st.columns(2)
    with col3:
        st.markdown("#### Banff, Canada 🇨🇦")
        st.video("https://www.youtube.com/watch?v=Y-Pd4S2y654")
        st.caption("🕐 En direct • Parc national des Rocheuses")

    with col4:
        st.markdown("#### Rotsund, Norvège 🇳🇴")
        st.video("https://www.youtube.com/watch?v=vuHCnnjijgI")
        st.caption("🕐 En direct • Nord de la Norvège")

    st.markdown("---")

    # Rangée 3
    col5, col6 = st.columns(2)
    with col5:
        st.markdown("#### Kilpisjärvi, Finlande 🇫🇮")
        st.video("https://www.youtube.com/watch?v=ccTVAhJU5lg&ab_channel=Starlapland%2FSamuliKorvanen")
        st.caption("🕐 En direct • Laponie finlandaise")

    with col6:
        st.markdown("#### Alaska, États-Unis 🇺🇸")
        st.video("https://www.youtube.com/watch?v=O52zDyxg5QI&ab_channel=ExploreZenDen")
        st.caption("🕐 En direct 24/7 • L'un des meilleurs sites d'aurores")

    st.markdown("---")    

    st.caption("💡 **Astuce :** Les webcams fonctionnent mieux pendant la nuit locale. Vérifiez les décalages horaires !")
    st.caption("📺 Source de données : Flux YouTube en direct.")


# -------- Prévisions Aurores — Animation 30 Minutes --------

with tab6:
    import io
    import time
    from datetime import datetime, timedelta, timezone
    from urllib.parse import urlencode
    import requests
    from PIL import Image  

    st.subheader("🌌 Prévisions Aurores Boréales")


    # Auto-actualisation toutes les 5 minutes (si streamlit-autorefresh est installé)
    try:
        from streamlit_autorefresh import st_autorefresh
        st_autorefresh(interval=300_000, key="aurora_anim_autorefresh")
    except Exception:
        pass

    # ---- Contrôles (optionnels)
    cc1, cc2 = st.columns(2)
    with cc1:
        minutes_window = st.selectbox("Fenêtre temporelle", [30, 60, 90, 120, 180], index=2)  # défaut 90
    with cc2:
        fps = st.slider("Vitesse d'animation (images/sec)", 1, 8, 4)

        st.markdown(" ")    

    # Fonction auxiliaire : récupérer les images récentes en PIL
    def fetch_frames(hemi: str, minutes_window: int, step_min: int = 5) -> list[Image.Image]:
        now_utc = datetime.now(timezone.utc)
        # arrondir à 5 min près
        rounded = now_utc - timedelta(minutes=now_utc.minute % 5,
                                      seconds=now_utc.second,
                                      microseconds=now_utc.microsecond)
        frames = []
        steps = max(1, minutes_window // step_min)
        for i in range(steps, -1, -1):  # du plus ancien au plus récent
            t = rounded - timedelta(minutes=i * step_min)
            stamp = t.strftime("%Y-%m-%d_%H%M")
            base = f"https://services.swpc.noaa.gov/images/animations/ovation/{hemi}/"
            fname = f"aurora_{'N' if hemi=='north' else 'S'}_{stamp}.jpg"
            url = base + fname + "?" + urlencode({"t": int(t.timestamp())})
            try:
                r = requests.get(url, timeout=10)
                if r.status_code == 200 and r.headers.get("Content-Type", "").startswith("image"):
                    img = Image.open(io.BytesIO(r.content)).convert("RGB")
                    frames.append(img)
            except Exception:
                continue
        return frames

    # Fonction auxiliaire : créer un GIF (en octets) à partir des images
    def make_gif(frames: list[Image.Image], fps: int) -> bytes | None:
        if not frames:
            return None
        buf = io.BytesIO()
        duration_ms = int(1000 / max(1, fps))
        frames[0].save(
            buf, format="GIF", save_all=True,
            append_images=frames[1:],
            duration=duration_ms, loop=0, disposal=2
        )
        return buf.getvalue()

    # URLs des images statiques (pour référence)
    ts = int(time.time())
    north_still_url = f"https://services.swpc.noaa.gov/images/aurora-forecast-northern-hemisphere.jpg?{urlencode({'t': ts})}"
    south_still_url = f"https://services.swpc.noaa.gov/images/aurora-forecast-southern-hemisphere.jpg?{urlencode({'t': ts})}"

    # Récupérer et assembler les animations
    with st.spinner("⏳ Chargement des dernières images OVATION de NOAA…"):
        north_frames = fetch_frames("north", minutes_window, step_min=5)
        south_frames = fetch_frames("south", minutes_window, step_min=5)
        north_gif = make_gif(north_frames, fps)
        south_gif = make_gif(south_frames, fps)

    # Disposition : deux panneaux côte à côte
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"#### Hémisphère Nord ({minutes_window} dernières min)")
        st.markdown(" ")
        st.markdown(" ")

        if north_gif:
            st.image(north_gif, use_container_width=True)
            st.markdown(" ")
            st.caption("🟢 Vert = probabilité faible d'aurores")
            st.caption("🟡 Jaune/Rouge = activité plus intense")
            st.caption("☀️ Le côté ensoleillé est plus clair")
        else:
            st.info("ℹ️ Aucune image récente disponible pour l'hémisphère Nord.")
            st.image(north_still_url, use_container_width=True)

    with c2:
        st.markdown(f"#### Hémisphère Sud ({minutes_window} dernières min)")
        st.markdown(" ")
        st.markdown(" ")

        if south_gif:
            st.image(south_gif, use_container_width=True)
        else:
            st.info("ℹ️ Aucune image récente disponible pour l'hémisphère Sud.")
            st.image(south_still_url, use_container_width=True)

    st.markdown("---")
    
    st.info("""
    💡 **Comment lire ces cartes :**
    - **Zone verte** : Probabilité d'aurores faible à modérée (visible seulement dans l'Arctique)
    - **Zone jaune/orange** : Activité aurorale forte (visible jusqu'en Scandinavie du Sud)
    - **Zone rouge** : Tempête géomagnétique majeure (aurores visibles jusqu'en Europe centrale !)
    - **Côté clair** : Hémisphère en plein jour (soleil de minuit)
    
    Les cartes se mettent à jour toutes les 5 minutes depuis le modèle OVATION de NOAA.
    """)

    # Ouvrir la page produit NOAA
    st.link_button(
        "🔗 Ouvrir la page produit NOAA",
        "https://www.swpc.noaa.gov/products/aurora-30-minute-forecast",
        use_container_width=True
    )

    st.markdown(" ")

    # Boutons de téléchargement des GIF
    try:
        col_dl1, col_dl2 = st.columns(2)
        with col_dl1:
            if north_gif:
                st.download_button(
                    "📥 Télécharger animation Nord (GIF)",
                    data=north_gif,
                    file_name=f"aurore_nord_{minutes_window}min_{fps}fps.gif",
                    mime="image/gif",
                    use_container_width=True
                )
        with col_dl2:
            if south_gif:
                st.download_button(
                    "📥 Télécharger animation Sud (GIF)",
                    data=south_gif,
                    file_name=f"aurore_sud_{minutes_window}min_{fps}fps.gif",
                    mime="image/gif",
                    use_container_width=True
                )
        st.markdown(" ")
    except Exception as e:
        st.info(f"ℹ️ Impossible de créer les GIF téléchargeables ({e}). Vous pouvez toujours faire un clic droit sur les images pour les enregistrer.")

    st.caption("🔄 Les images se rafraîchissent toutes les 5 minutes environ. Si elles semblent anciennes, le modèle peut avoir du retard.")

    st.markdown("---")

    st.caption("📡 Source de données : NOAA SWPC — Modèle OVATION (mise à jour toutes les 5 minutes)")



# -------- À propos --------
with tab7:
    st.subheader("ℹ️ À Propos")

    st.markdown("""
**Ce que fait ce tableau de bord**
- Surveille **l'activité géomagnétique (indice Kp)** depuis NOAA SWPC
- Récupère **la météo actuelle et prévue** (nuages, vent, précipitations, température, visibilité) depuis Open-Meteo et OpenWeatherMap
- Intègre **les calculs d'obscurité** depuis l'API Sunrise-Sunset
- Affiche **des webcams en direct** depuis des sites d'observation d'aurores dans le monde
- Montre **les prévisions NOAA d'aurores à 30 minutes** (avec animation)
- Combine plusieurs facteurs dans un simple **Score de Probabilité** d'observation d'aurores

**APIs et Sources de Données**
- [NOAA SWPC](https://www.swpc.noaa.gov/) — Indice Kp & Prévisions aurores
- [Open-Meteo](https://open-meteo.com/) — Prévisions météo & géocodage
- [OpenWeatherMap](https://openweathermap.org/) — Météo actuelle
- [Sunrise-Sunset](https://sunrise-sunset.org/api) — Cycle jour-nuit / obscurité
- [Webcams Aurores](https://virmalised.ee/virmaliste-live-kaamerad/) — Flux webcam externes

**Améliorations prévues**
- Carte interactive mondiale des probabilités d'aurores (flux JSON modèle OVATION)
- Plus d'intégrations de webcams (YouTube + SkylineWebcams)
- Alertes personnalisées quand le Score de Probabilité est élevé

**Comment utiliser ce dashboard**
1. **Sélectionnez votre localisation** dans la barre latérale (ou utilisez les localisations rapides)
2. **Ajustez les poids** selon vos priorités (Kp, ciel dégagé, obscurité)
3. **Consultez la Vue d'ensemble** pour le score de probabilité en temps réel
4. **Vérifiez les Prévisions météo** pour planifier votre sortie
5. **Surveillez les Prévisions aurores** pour l'activité géomagnétique en direct

**Meilleure période pour observer les aurores :**
- 🗓️ **Saison** : Septembre à mars (équinoxes = pic d'activité)
- 🕐 **Heure** : 22h-2h du matin (pic statistique)
- 🌍 **Lieu** : Au-dessus du cercle polaire arctique (Kp 3-4 suffit)
- 🌌 **Conditions** : Ciel dégagé + nuit noire + Kp ≥ 5 = 🎆 JACKPOT !
""")

    st.markdown("---")

# -------- Créé par --------

    st.subheader("👨🏾‍💻👨🏾‍💻 Créé par :")
    st.markdown(" ")
    st.subheader("Adjimon Jérôme VITOFFODJI et Alvin INGABIRE")
    st.markdown("""
            
Designer Open Data et Web des Données  

Ce tableau de bord a été créé dans le cadre d'un projet Streamlit pour explorer **les données en temps réel, les APIs et la visualisation interactive**.

""")