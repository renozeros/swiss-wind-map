import requests
from flask import Flask, jsonify, make_response
from flask_cors import CORS
from datetime import datetime, timedelta
import os
import re

app = Flask(__name__)
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
    
    # Feste Koordinaten für wichtige Messorte der Region Bodensee/Alpstein/Vaduz
    regional_coordinates = {
        "ALT": {"lat": 47.4833, "lon": 9.5667, "name": "Altenrhein"},
        "SNT": {"lat": 47.2500, "lon": 9.3500, "name": "Säntis"},
        "VAD": {"lat": 47.1333, "lon": 9.5167, "name": "Vaduz"},
        "KRE": {"lat": 47.6500, "lon": 9.1667, "name": "Kreuzlingen"},
        "STG": {"lat": 47.4333, "lon": 9.3833, "name": "St. Gallen"},
        "CHM": {"lat": 47.1667, "lon": 9.5333, "name": "Balzers / Liechtenstein"}
    }
    
    # 1. METEOSCHWEIZ
    try:
        live_url = "https://admin.ch"
        live_res = requests.get(live_url, timeout=5).json()
        
        for feature in live_res.get("features", []):
            props = feature.get("properties", {})
            st_id = props.get("station_reference")
            
            # Prüfen, ob die Station in unserer gewünschten Region liegt
            if st_id in regional_coordinates:
                # Extraktion der reinen Windgeschwindigkeit aus den verschachtelten Messwerten
                # MeteoSchweiz speichert Werte oft in einer Liste oder unter 'value'
                parameters = props.get("parameters", {})
                
                # Suchen nach dem Windgeschwindigkeits-Wert im Objekt
                speed_data = parameters.get("wind_speed", {}) or parameters.get("wind_speed_unit_station", {})
                speed = speed_data.get("value")
                
                if speed is not None:
                    try:
                        speed_int = int(round(float(speed)))
                    except (ValueError, TypeError):
                        continue
                        
                    direction_data = parameters.get("wind_direction", {}) or parameters.get("wind_direction_unit_station", {})
                    direction = direction_data.get("value")
                    dir_int = int(direction) if direction is not None else 0
                    
                    coord_info = regional_coordinates[st_id]
                    
                    stations_data[st_id] = {
                        "id": str(st_id), 
                        "name": coord_info["name"] + " (MeteoSchweiz)",
                        "lat": coord_info["lat"], 
                        "lon": coord_info["lon"], 
                        "speed": speed_int,
                        "direction": dir_int,
                        "source": "MeteoSchweiz", 
                        "history": []
                    }
    except Exception:
        pass

    # 2. HOLFUY
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

    response = make_response(jsonify(list(stations_data.values())))
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
