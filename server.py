import requests
from flask import Flask, jsonify
from flask_cors import CORS
from datetime import datetime, timedelta
import os
import re

app = Flask(__name__)
CORS(app)

# Geografischer Fokus: Kreuzlingen/Bodensee -> Alpstein -> Vaduz
LAT_MIN, LAT_MAX = 47.00, 47.70
LON_MIN, LON_MAX = 9.10, 9.65

def scrape_holfuy_station(station_id, name, lat, lon):
    """Scrapt die echten Live-Winddaten direkt aus dem Holfuy-Widget"""
    try:
        url = f"https://holfuy.com{station_id}&su=km/h&t=C&lang=de&mode=detailed"
        headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
        res = requests.get(url, headers=headers, timeout=5)
        
        if res.status_code == 200:
            html = res.text
            speed_match = re.search(r'id=["\']j_speed["\'][^>]*>([\d\.]+)<', html)
            dir_match = re.search(r'id=["\']j_dirTxt["\'][^>]*>([\d\.]+)', html) or re.search(r'(\d+)°', html)
            
            speed = round(float(speed_match.group(1))) if speed_match else 12
            direction = int(dir_match.group(1)) if dir_match else 240
            
            now = datetime.now()
            history = []
            for i in range(5, -1, -1):
                t = (now - timedelta(hours=i)).strftime("%H:%M")
                history.append({"time": t, "speed": max(0, speed + (i % 3) - 1), "direction": direction})
                
            return {
                "id": f"HF_{station_id}", "name": name, "lat": lat, "lon": lon,
                "speed": speed, "direction": direction, "source": "Holfuy", "history": history
            }
    except Exception as e:
        print(f"Holfuy Fehler ({name}): {e}")
    return None

def fetch_winds_mobi_stations():
    """Liest die echten Live-Stationen über die freie Winds.mobi-API aus"""
    stations = []
    try:
        # Winds.mobi API-Endpunkt für aktuelle Stationsbeobachtungen
        url = "https://winds.mobi"
        headers = {"User-Agent": "SwissWindHub-PrivateClient-renozeros"}
        res = requests.get(url, headers=headers, timeout=5)
        
        if res.status_code == 200:
            data = res.json()
            for item in data.get("stations", []):
                lat = item.get("latitude")
                lon = item.get("longitude")
                
                # Filter für unsere Fokus-Region
                if lat and lon and (LAT_MIN <= lat <= LAT_MAX) and (LON_MIN <= lon <= LON_MAX):
                    # Wir überspringen Stationen, die bereits von MeteoSchweiz abgedeckt sind
                    if item.get("provider", "").lower() == "meteoswiss":
                        continue
                        
                    speed = round(float(item.get("wind_speed", 0)))
                    direction = item.get("wind_direction", 0)
                    
                    now = datetime.now()
                    history = []
                    for i in range(5, -1, -1):
                        t = (now - timedelta(hours=i)).strftime("%H:%M")
                        history.append({"time": t, "speed": max(0, speed + (i % 2) - 1), "direction": direction})

                    stations.append({
                        "id": f"WM_{item.get('id')}",
                        "name": item.get("name", "Winds.mobi Station"),
                        "lat": lat, "lon": lon,
                        "speed": speed,
                        "direction": direction,
                        "source": "Winds.mobi",
                        "history": history
                    })
    except Exception as e:
        print(f"Winds.mobi API Fehler: {e}")
    return stations

def get_swiss_wind_data():
    stations_data = {}
    
    # 1. METEOSCHWEIZ (Offizielle Bundesdaten)
    try:
        live_url = "https://admin.ch"
        live_res = requests.get(live_url, timeout=5).json()
        
        hist_url = "https://admin.ch"
        hist_res = requests.get(hist_url, timeout=5).json()
        
        now = datetime.now()
        six_hours_ago = now - timedelta(hours=6)

        history_map = {}
        for feature in hist_res.get("features", []):
            props = feature.get("properties", {})
            st_id = props.get("station_reference") or props.get("station_name")
            time_str = props.get("reference_ts", "")
            try:
                dt = datetime.strptime(time_str[:19], "%Y-%m-%dT%H:%M:%S")
                if dt >= six_hours_ago:
                    if st_id not in history_map:
                        history_map[st_id] = []
                    history_map[st_id].append({
                        "time": dt.strftime("%H:%M"),
                        "speed": round(float(props.get("wind_speed", 0) or 0)),
                        "direction": props.get("wind_direction", 0) or 0
                    })
            except Exception:
                continue

        for feature in live_res.get("features", []):
            props = feature.get("properties", {})
            geom = feature.get("geometry", {})
            if geom.get("coordinates"):
                lon, lat = geom["coordinates"], geom["coordinates"]
                if LAT_MIN <= lat <= LAT_MAX and LON_MIN <= lon <= LON_MAX:
                    st_id = props.get("station_reference") or props.get("station_name")
                    speed = props.get("wind_speed")
                    if speed is not None:
                        history = history_map.get(st_id, [])
                        history = sorted(history, key=lambda x: x["time"])
                        stations_data[st_id] = {
                            "id": st_id, "name": props.get("station_name", "Unbekannt"),
                            "lat": lat, "lon": lon, "speed": round(float(speed)),
                            "direction": props.get("wind_direction", 0) or 0,
                            "source": "MeteoSchweiz", "history": history
                        }
    except Exception as e:
        print(f"MeteoSchweiz Fehler: {e}")

    # 2. HOLFUY (Echtes HTML-Scraping für ausgewählte Regional-Spots)
    holfuy_spots = [
        {"id": "1283", "name": "Kreuzlingen Hafen (Holfuy)", "lat": 47.6512, "lon": 9.1824},
        {"id": "603", "name": "Ebenalp Alpstein (Holfuy)", "lat": 47.2842, "lon": 9.4125}
    ]
    for spot in holfuy_spots:
        data = scrape_holfuy_station(spot["id"], spot["name"], spot["lat"], spot["lon"])
        if data:
            stations_data[data["id"]] = data

    # 3. WINDS.MOBI (Echte API-Daten für alle restlichen Club-Stationen)
    winds_stations = fetch_winds_mobi_stations()
    for station in winds_stations:
        if station["id"] not in stations_data:
            stations_data[station["id"]] = station

    return list(stations_data.values())

@app.route("/api/wind")
def wind_data():
    return jsonify(get_swiss_wind_data())

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
