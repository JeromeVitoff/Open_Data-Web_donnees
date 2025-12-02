# Open_Data-Web_donnees

Thème :  Chasseur d'aurores boréales. 

Problématique : "Comment savoir quand et où observer des aurores boréales pour ne pas rater ma photo ?

Lien vers dashboard: https://web-production-ff2d6.up.railway.app/

Un tableau de bord interactif développé avec Streamlit pour surveiller et explorer en temps réel les probabilités d'observation des aurores polaires (Aurora Borealis & Australis).

![Python](https://img.shields.io/badge/Python-3.11-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-red)
![License](https://img.shields.io/badge/License-Educational-green)

---

## 📋 Table des Matières

- [Aperçu](#-aperçu)
- [Fonctionnalités](#-fonctionnalités)
- [Technologies](#-technologies-utilisées)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [Utilisation](#-utilisation)
- [Structure du Projet](#-structure-du-projet)
- [APIs Utilisées](#-apis-utilisées)
- [Captures d'Écran](#-captures-décran)
- [Roadmap](#-roadmap)
- [Auteur](#-auteur)

---

## 🎯 Aperçu

Ce projet a été développé dans le cadre du **Master 2 - Open Data et Web** pour explorer :
- L'intégration de données en temps réel depuis plusieurs APIs publiques
- La visualisation interactive de données météorologiques et géomagnétiques
- Le développement d'applications web avec Streamlit et Plotly

Le dashboard combine des données géomagnétiques (indice Kp), météorologiques (nuages, vent, visibilité) et astronomiques (obscurité) pour calculer un **Score de Probabilité** d'observation des aurores boréales.

---

## ✨ Fonctionnalités

### 🌍 Vue d'Ensemble
- **Jauge Indice Kp** : Activité géomagnétique en temps réel depuis NOAA SWPC
- **Jauge Ciel Dégagé** : Pourcentage de ciel sans nuages
- **Score de Probabilité** : Métrique composite (Kp + météo + obscurité)
- **Historique Kp** : Graphique des 4 dernières heures (téléchargeable en CSV)

### 🌤 Météo Actuelle
- Conditions météo en direct via OpenWeatherMap API
- Température, ressenti, humidité, pression
- Couverture nuageuse et vent
- Icône météo animée

### 📅 Prévisions Météo (48h)
**Explorateur Interactif** :
- Sélection de variables (jusqu'à 5 simultanées)
- Curseur temporel et zoom
- Marqueurs pour fenêtres d'observation optimales
- Export CSV des prévisions

**Graphiques détaillés** :
- Nuages totaux et par couches (bas/moyen/haut)
- Température et point de rosée
- Vent et rafales
- Précipitations et visibilité

### 📷 Webcams en Direct
- 6 webcams depuis des sites d'observation mondiaux
- Suède, Norvège, Finlande, Islande, Canada, USA
- Flux YouTube intégrés
- Disponibilité saisonnière (septembre-mars)

### 🌌 Prévisions Aurores
- **Animations OVATION** : Modèle NOAA mis à jour toutes les 5 minutes
- Hémisphères Nord et Sud
- Contrôle de la fenêtre temporelle (30-180 min)
- Vitesse d'animation ajustable (1-8 fps)
- Téléchargement des GIF générés

### ℹ️ À Propos
- Documentation complète des APIs
- Guide d'utilisation
- Conseils d'observation (saison, heure, lieu)
- Sources de données

---

## 📊 Technologies Utilisées

### Backend & Framework
- **Python 3.11** : Langage principal
- **Streamlit 1.28+** : Framework web pour le dashboard
- **Pandas** : Manipulation et analyse de données
- **Requests** : Appels HTTP aux APIs

### Visualisation
- **Plotly** : Graphiques interactifs
- **Plotly Express** : Création rapide de visualisations
- **Plotly Graph Objects** : Jauges personnalisées

### Traitement d'Images
- **Pillow (PIL)** : Création des GIF animés
- **io / BytesIO** : Manipulation d'images en mémoire

### APIs Externes (Gratuites)
| API | Usage | Limite | Documentation |
|-----|-------|--------|---------------|
| **NOAA SWPC** | Indice Kp, Aurores | ∞ (publique) | [Lien](https://www.swpc.noaa.gov/) |
| **Open-Meteo** | Prévisions 48h | 10k req/jour | [Lien](https://open-meteo.com/) |
| **OpenWeatherMap** | Météo actuelle | 60 req/min | [Lien](https://openweathermap.org/) |
| **Sunrise-Sunset** | Jour/Nuit | ∞ (publique) | [Lien](https://sunrise-sunset.org/api) |

---

## 🚀 Installation

### Prérequis
- Python 3.11 ou supérieur
- pip (gestionnaire de packages Python)
- Compte OpenWeatherMap (gratuit)

### Étapes

```bash
# 1. Cloner le dépôt
git clone https://github.com/votre-username/aurora-dashboard.git
cd aurora-dashboard

# 2. Créer un environnement virtuel
python -m venv venv

# 3. Activer l'environnement virtuel
# Sur macOS/Linux :
source venv/bin/activate

# Sur Windows :
venv\Scripts\activate

# 4. Installer les dépendances
pip install -r requirements.txt

# 5. Créer le fichier de configuration des secrets
mkdir -p .streamlit
touch .streamlit/secrets.toml
```

---

## 🔑 Configuration

### 1. Clé API OpenWeatherMap

Créez un compte gratuit sur [OpenWeatherMap](https://openweathermap.org/api) et obtenez votre clé API.

### 2. Fichier `.streamlit/secrets.toml`

Créez le fichier et ajoutez votre clé :

```toml
# .streamlit/secrets.toml

OPENWEATHER_API_KEY = "votre_cle_api_32_caracteres"
```

**⚠️ Important** : Ce fichier est dans `.gitignore` pour ne pas exposer votre clé.

### 3. Fichier `.streamlit/config.toml` (Optionnel)

Pour personnaliser le thème :

```toml
[theme]
primaryColor = "#e3b505"
backgroundColor = "#0e1117"
secondaryBackgroundColor = "#262730"
textColor = "#fafafa"
font = "sans serif"
```

---

## 💻 Utilisation

### Lancer le Dashboard

```bash
# S'assurer que l'environnement virtuel est activé
source venv/bin/activate  # macOS/Linux
venv\Scripts\activate     # Windows

# Lancer l'application
streamlit run aurora_app.py
```

L'application s'ouvrira automatiquement dans votre navigateur à l'adresse : `http://localhost:8501`

### Navigation

1. **Sidebar** :
   - Sélectionnez votre localisation (ou utilisez les localisations rapides)
   - Ajustez les poids du Score de Probabilité
   - Actualisez les données manuellement

2. **Onglets** :
   - **Vue d'ensemble** : Indicateurs principaux et score global
   - **Météo actuelle** : Conditions en temps réel
   - **Prévisions météo** : Analyse détaillée des 48 prochaines heures
   - **Webcams** : Flux vidéo en direct
   - **Prévisions aurores** : Animations OVATION
   - **À propos** : Documentation et aide

### Fonctionnalités Interactives

- **Graphiques Plotly** : Survol pour voir les valeurs, zoom, déplacement
- **Sélection temporelle** : Boutons 6h/12h/24h/Tout
- **Téléchargements** : CSV des données Kp et prévisions météo
- **GIF animés** : Téléchargement des animations aurores personnalisées

---

## 📁 Structure du Projet

```
aurora-dashboard/
│
├── aurora_app.py                 # Application principale Streamlit
├── aurora_app_fr.py             # Version française (avec traductions)
│
├── model/
│   └── functions.py             # Fonctions de récupération de données
│                                  - geocode_place()
│                                  - get_kp_now()
│                                  - get_kp_series()
│                                  - get_weather()
│                                  - get_owm_current()
│                                  - darkness_flag()
│                                  - chance_score()
│
├── assets/
│   └── aurora_banner.jpg        # Image bannière du dashboard
│
├── .streamlit/
│   ├── config.toml              # Configuration du thème Streamlit
│   └── secrets.toml             # Clés API (à créer, non versionné)
│
├── requirements.txt             # Dépendances Python
├── .gitignore                   # Fichiers à ignorer par Git
├── README.md                    # Ce fichier
│
└── screenshots/                 # Captures d'écran (optionnel)
    ├── overview.png
    ├── future-weather.png
    └── aurora-forecast.png
```

---

## 🔧 APIs Utilisées

### 1. NOAA Space Weather Prediction Center

**Endpoints utilisés** :
- `https://services.swpc.noaa.gov/json/boulder_k_index_1m.json`
  - Indice Kp en temps réel (résolution 1 minute)
- `https://services.swpc.noaa.gov/images/animations/ovation/north/`
  - Images OVATION hémisphère Nord
- `https://services.swpc.noaa.gov/images/animations/ovation/south/`
  - Images OVATION hémisphère Sud

**Données récupérées** :
- Indice Kp (activité géomagnétique)
- Horodatage UTC
- Cartes de probabilité d'aurores

**Licence** : Données publiques NOAA (pas de clé requise)

---

### 2. Open-Meteo API

**Endpoints utilisés** :
- `https://api.open-meteo.com/v1/forecast`
  - Prévisions météo 48h
- `https://geocoding-api.open-meteo.com/v1/search`
  - Géocodage des villes

**Données récupérées** :
- Couverture nuageuse totale, basse, moyenne, haute (%)
- Température et point de rosée (°C)
- Humidité relative (%)
- Vent et rafales (m/s)
- Précipitations et probabilité (mm, %)
- Visibilité (km)

**Licence** : CC BY 4.0 (10 000 requêtes/jour gratuites)

---

### 3. OpenWeatherMap API

**Endpoint utilisé** :
- `https://api.openweathermap.org/data/2.5/weather`

**Données récupérées** :
- Température actuelle et ressentie (°C)
- Humidité (%)
- Couverture nuageuse (%)
- Vent (m/s)
- Pression atmosphérique (hPa)
- Description météo
- Icône météo

**Authentification** : Clé API requise (gratuite)

**Limite gratuite** : 60 requêtes/minute, 1000 requêtes/jour

---

### 4. Sunrise-Sunset API

**Endpoint utilisé** :
- `https://api.sunrise-sunset.org/json`

**Données récupérées** :
- Heure du lever du soleil (UTC)
- Heure du coucher du soleil (UTC)
- Durée du jour

**Utilisation dans le dashboard** :
- Calcul du flag d'obscurité (`dark = 1` si nuit, `0` sinon)
- Pondération du Score de Probabilité

**Licence** : Publique (pas de clé requise)

---

## 📸 Captures d'Écran

### Vue d'Ensemble
![Vue d'ensemble](screenshots/overview.png)
*Jauges Kp, Ciel Dégagé et Score de Probabilité avec explications*

### Prévisions Météo - Explorateur Interactif
![Prévisions météo](screenshots/future-weather.png)
*Graphique multi-variables avec curseur temporel et fenêtres suggérées*

### Prévisions Aurores - Animations OVATION
![Prévisions aurores](screenshots/aurora-forecast.png)
*GIF animés des hémisphères Nord et Sud (90 dernières minutes)*

---

## 🗺️ Roadmap

### ✅ Fonctionnalités Implémentées

- [x] Récupération temps réel de l'indice Kp
- [x] Météo actuelle (OpenWeatherMap)
- [x] Prévisions météo 48h (Open-Meteo)
- [x] Calcul du Score de Probabilité composite
- [x] Graphiques interactifs Plotly
- [x] Animations OVATION (GIF personnalisables)
- [x] Webcams en direct (YouTube)
- [x] Export CSV des données
- [x] Traduction complète en français
- [x] Descriptions pédagogiques sous chaque graphique

### 🚧 En Développement

- [ ] Carte interactive mondiale des probabilités d'aurores (GeoJSON)
- [ ] Système d'alertes par email (quand Kp > seuil)


---

## 📖 Documentation Technique

### Fonction `chance_score()`

Le Score de Probabilité est calculé comme suit :

```python
def chance_score(kp, cloud_pct, dark_flag, w1=0.5, w2=0.35, w3=0.15):
    """
    Calcule un score de 0 à 1 pour les chances d'observer une aurore.
    
    Args:
        kp (float): Indice Kp (0-9)
        cloud_pct (float): Couverture nuageuse (0-100%)
        dark_flag (int): 1 si nuit, 0 si jour
        w1, w2, w3 (float): Poids des facteurs (doivent sommer à 1.0)
    
    Returns:
        float: Score entre 0 (impossible) et 1 (excellent)
    
    Formule:
        score = w1 * (kp/9) + w2 * (1 - cloud/100) + w3 * dark_flag
    """
    kp_norm = min(kp / 9.0, 1.0) if kp else 0
    cloud_norm = 1.0 - (cloud_pct / 100.0) if cloud_pct else 0
    dark = dark_flag if dark_flag else 0
    
    return w1 * kp_norm + w2 * cloud_norm + w3 * dark
```

**Interprétation** :
- **0.0 - 0.4** : Faible probabilité 🔴
- **0.4 - 0.7** : Probabilité moyenne 🟡
- **0.7 - 1.0** : Excellente probabilité 🟢

### Mise en Cache Streamlit

Les fonctions d'appel API utilisent `@st.cache_data(ttl=300)` :
- **ttl=300** : Cache de 5 minutes
- Évite les appels API redondants
- Améliore les performances

```python
@st.cache_data(ttl=300)
def get_kp_now():
    # Appel API seulement si cache expiré
    ...
```

---

## 🤝 Contribution

Ce projet est développé dans un cadre académique, mais les suggestions sont bienvenues !

**Pour signaler un bug ou proposer une amélioration** :
1. Ouvrez une [Issue](https://github.com/votre-username/aurora-dashboard/issues)
2. Décrivez le problème ou la fonctionnalité souhaitée
3. Ajoutez des captures d'écran si pertinent

---

## 📄 Licence

**Usage Éducatif et Recherche**

Ce projet utilise des données publiques de la NOAA et est fourni à des fins éducatives dans le cadre du cours de Open Data et Web.

**Données** :
- NOAA : Domaine public (données gouvernementales US)
- Open-Meteo : CC BY 4.0
- OpenWeatherMap : Attribution requise

---

## 🙏 Remerciements

### Données et APIs
- **NOAA Space Weather Prediction Center** - Données Kp et modèle OVATION
- **Open-Meteo** - API météo gratuite et performante
- **OpenWeatherMap** - Conditions météo actuelles
- **Sunrise-Sunset.org** - Calculs astronomiques

### Technologies
- **Streamlit** - Framework de développement rapide
- **Plotly** - Bibliothèque de visualisation interactive
- **Python Community** - Pandas, Requests, Pillow

### Inspiration
- Projets de météo spatiale sur GitHub
- Communauté des chasseurs d'aurores
- Forums d'astrophotographie

---

## 👨‍💻 Auteur

**Adjimon Jérôme VITFFODJI et Alvin INGABIRE**  
Étudiant Master 2 - MIASHS cours de Open Data et Web  
Montpellier, France


---

## 📚 Ressources Utiles

### Apprendre la Météo Spatiale
- [NOAA Space Weather Scales](https://www.swpc.noaa.gov/noaa-scales-explanation)
- [Spaceweather.com](https://spaceweather.com/)
- [Aurora Service Europe](https://www.aurora-service.eu/)

### Streamlit
- [Documentation officielle](https://docs.streamlit.io/)
- [Gallery d'exemples](https://streamlit.io/gallery)

### Plotly
- [Plotly Python](https://plotly.com/python/)
- [Graphiques interactifs](https://plotly.com/python/plotly-fundamentals/)

---

## 🌟 Statistiques du Projet

![Lines of Code](https://img.shields.io/badge/Lines%20of%20Code-~1500-blue)
![Files](https://img.shields.io/badge/Files-4-green)
![APIs](https://img.shields.io/badge/APIs-4-orange)
![Graphiques](https://img.shields.io/badge/Graphiques-15+-red)

---

**Développé avec ❤️ et Streamlit**  
**Bon chasseur d'aurores ! 🌌✨**

---

*Dernière mise à jour : Novembre 2025*
