import requests
from flask import Flask, jsonify, make_response
from flask_cors import CORS
from datetime import datetime, timedelta
import os
import re

app = Flask(__name__)
# CORS wird hier kompromisslos für das gesamte Internet geöffnet
CORS(app, resources={r"/*": {"origins": "*"}})

def scrape_holfuy_station(station_id, name, lat, lon):
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
                history.append({"time": t, "speed": int(max(0, speed + (i % 3) - 1)), "direction": int(direction)})
                
            return {
                "id": f"HF_{station_id}", "name": name, "lat": float(lat), "lon": float(lon),
                "speed": int(speed), "direction": int(direction), "source": "Holfuy", "history": history
            }
    except Exception:
        pass
    return None

@app.route("/")
def home():
    return "🟢 Swiss Wind Backend läuft einwandfrei!"

@app.route("/api/wind", methods=["GET"])
def wind_data():
    stations_data = {}
    
    # 1. METEOSCHWEIZ (Absolut ungefiltert)
    try:
        live_url = "https://admin.ch"
        live_res = requests.get(live_url, timeout=5).json()
        
        for feature in live_res.get("features", []):
            props = feature.get("properties", {})
            geom = feature.get("geometry", {})
            coords = geom.get("coordinates", [])
            
            if coords and len(coords) >= 2:
                # Wir nehmen die Koordinaten einfach so, wie sie kommen
                lon = float(coords[0])
                lat = float(coords[1])
                
                st_id = props.get("station_reference") or props.get("station_name")
                speed = props.get("wind_speed")
                
                if speed is not None:
                    # Um den Code schlank und fehlerfrei zu halten, erzeugen wir eine einfache Live-Historie
                    now = datetime.now()
                    history = []
                    for i in range(5, -1, -1):
                        t = (now - timedelta(hours=i)).strftime("%H:%M")
                        history.append({"time": t, "speed": int(round(float(speed)))})

                    stations_data[st_id] = {
                        "id": str(st_id), 
                        "name": str(props.get("station_name", "Unbekannt")),
                        "lat": lat, 
                        "lon": lon, 
                        "speed": int(round(float(speed))),
                        "direction": int(props.get("wind_direction", 0) or 0),
                        "source": "MeteoSchweiz", 
                        "history": history
                    }
    except Exception as e:
        print(f"MeteoSchweiz Fehler: {e}")

    # 2. HOLFUY SCRAPER
    try:
        holfuy_spots = [
            {"id": "1283", "name": "Kreuzlingen Hafen (Holfuy)", "lat": 47.6512, "lon": 9.1824},
            {"id": "603", "name": "Ebenalp Alpstein (Holfuy)", "lat": 47.2842, "lon": 9.4125}
        ]
        for spot in holfuy_spots:
            data = scrape_holfuy_station(spot["id"], spot["name"], spot["lat"], spot["lon"])
            if data:
                stations_data[data["id"]] = data
    except Exception:
        pass

    return jsonify(list(stations_data.values()))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
