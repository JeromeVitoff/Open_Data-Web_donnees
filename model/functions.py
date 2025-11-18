# model/functions.py

import requests
import pandas as pd
import datetime as dt
import pytz
import streamlit as st
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# -------------------------------------------------------------------
# NOAA SWPC — Kp index (current + recent series)
# -------------------------------------------------------------------

def get_kp_now():
    """Fetch latest Kp index value and time."""
    url = "https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json"
    r = requests.get(url, timeout=15)
    r.raise_for_status()
    data = r.json()

    # last row is most recent
    last = data[-1]
    time_tag = pd.to_datetime(last[0])
    kp_val = float(last[1]) if last[1] is not None else None
    return kp_val, time_tag



@st.cache_data(ttl=300, show_spinner=False)  # cache 5 min
def get_kp_series(limit_minutes=240):
    """Fetch recent Kp index (1-min values) and return last `limit_minutes` as UTC tz-aware."""
    url = "https://services.swpc.noaa.gov/json/planetary_k_index_1m.json"
    r = requests.get(url, timeout=15)
    r.raise_for_status()
    data = r.json()

    df = pd.DataFrame(data)
    # Force UTC tz-aware timestamps
    df["time_tag"] = pd.to_datetime(df["time_tag"], utc=True)
    df["kp_index"] = pd.to_numeric(df["kp_index"], errors="coerce")
    df = df.dropna(subset=["kp_index"]).sort_values("time_tag")

    cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(minutes=limit_minutes)
    df = df[df["time_tag"] >= cutoff]
    return df

# -------------------------------------------------------------------
# Open-Meteo — Forecast Weather
# -------------------------------------------------------------------

def get_weather(lat, lon, tz):
    """Fetch hourly weather forecast (next 48h) from Open-Meteo."""
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": [
            "cloudcover",
            "cloudcover_low",
            "cloudcover_mid",
            "cloudcover_high",
            "temperature_2m",
            "dewpoint_2m",
            "relative_humidity_2m",
            "visibility",
            "windspeed_10m",
            "windgusts_10m",
            "precipitation",
            "precipitation_probability",
        ],
        "timezone": tz,
        "forecast_days": 2,
    }
    r = requests.get(url, params=params, timeout=15)
    r.raise_for_status()
    data = r.json()

    if "hourly" not in data:
        return None

    hr = data["hourly"]
    df = pd.DataFrame({
        "time": pd.to_datetime(hr["time"]),
        "cloud_total": hr["cloudcover"],
        "cloud_low": hr["cloudcover_low"],
        "cloud_mid": hr["cloudcover_mid"],
        "cloud_high": hr["cloudcover_high"],
        "temp_c": hr["temperature_2m"],
        "dewpoint_c": hr["dewpoint_2m"],
        "rh_pct": hr["relative_humidity_2m"],
        "visibility_km": [v/1000 if v is not None else None for v in hr["visibility"]],
        "wind_ms": hr["windspeed_10m"],
        "gust_ms": hr["windgusts_10m"],
        "precip_mm": hr["precipitation"],
        "precip_prob": hr["precipitation_probability"],
    })
    return df

# -------------------------------------------------------------------
# Sunrise–Sunset API — Darkness flag
# -------------------------------------------------------------------

def darkness_flag(lat, lon):
    """Return darkness=1 if night at given lat/lon, plus sunrise/sunset times."""
    url = "https://api.sunrise-sunset.org/json"
    params = {"lat": lat, "lng": lon, "formatted": 0}
    r = requests.get(url, params=params, timeout=15)
    r.raise_for_status()
    data = r.json()["results"]

    sunrise_utc = pd.to_datetime(data["sunrise"])
    sunset_utc = pd.to_datetime(data["sunset"])
    now_utc = pd.Timestamp.utcnow()

    dark = 1 if (now_utc < sunrise_utc) or (now_utc > sunset_utc) else 0
    return dark, sunrise_utc, sunset_utc

# -------------------------------------------------------------------
# Geocoding — Open-Meteo
# -------------------------------------------------------------------

def geocode_place(place: str):
    """Resolve place name to lat/lon via Open-Meteo geocoding."""
    url = "https://geocoding-api.open-meteo.com/v1/search"
    r = requests.get(url, params={"name": place, "count": 1}, timeout=15)
    r.raise_for_status()
    js = r.json()
    if not js.get("results"):
        return None
    rec = js["results"][0]
    return {
        "name": rec["name"],
        "country": rec.get("country", ""),
        "lat": rec["latitude"],
        "lon": rec["longitude"],
        "timezone": rec["timezone"],
    }

# -------------------------------------------------------------------
# Chance score computation
# -------------------------------------------------------------------

def chance_score(kp, cloud, dark, w1=0.5, w2=0.35, w3=0.15):
    """Compute simple weighted score for aurora visibility (0–1)."""
    if kp is None or cloud is None:
        return 0
    kp_norm = min(kp / 9, 1.0)         # scale Kp to 0–1
    sky_norm = max(0, min((100 - cloud) / 100, 1.0))  # clear sky %
    score = w1*kp_norm + w2*sky_norm + w3*dark
    return round(score, 2)

def score_label(score):
    if score < 0.4:
        return "(Low)"
    elif score < 0.7:
        return "(Moderate)"
    else:
        return "(High)"

# -------------------------------------------------------------------
# OpenWeatherMap — Current Weather (with cache + retries)
# -------------------------------------------------------------------

@st.cache_resource
def _owm_session():
    s = requests.Session()
    retry = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    s.mount("https://", HTTPAdapter(max_retries=retry))
    return s

@st.cache_data(ttl=600, show_spinner=False)   # cache for 10 minutes
def get_owm_current(lat: float, lon: float, api_key: str, units: str = "metric"):
    """Fetch current weather from OpenWeatherMap with caching and rate-limit handling."""
    lat = round(float(lat), 3)
    lon = round(float(lon), 3)
    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {"lat": lat, "lon": lon, "appid": api_key, "units": units}

    r = _owm_session().get(url, params=params, timeout=15)

    if r.status_code == 429:
        return {"error": "rate_limited", "message": "OpenWeatherMap rate limit reached. Please try again shortly."}

    r.raise_for_status()
    data = r.json()

    icon = (data.get("weather") or [{}])[0].get("icon")
    desc = (data.get("weather") or [{}])[0].get("description") or ""
    return {
        "raw": data,
        "city": data.get("name"),
        "country": (data.get("sys") or {}).get("country"),
        "desc": f" — {desc.title()}" if desc else "",
        "temp_c": (data.get("main") or {}).get("temp"),
        "feels_like_c": (data.get("main") or {}).get("feels_like"),
        "humidity_pct": (data.get("main") or {}).get("humidity"),
        "cloud_pct": (data.get("clouds") or {}).get("all"),
        "wind_ms": (data.get("wind") or {}).get("speed"),
        "pressure_hpa": (data.get("main") or {}).get("pressure"),
        "icon_url": f"https://openweathermap.org/img/wn/{icon}@2x.png" if icon else None,
    }
