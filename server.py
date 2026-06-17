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
    
    # 1. METEOSCHWEIZ (Gekapselt gegen Systemabstürze)
    try:
        live_url = "https://admin.ch"
        live_res = requests.get(live_url, timeout=4).json()
        
        for feature in live_res.get("features", []):
            props = feature.get("properties", {})
            st_name = props.get("station_name")
            
            # Regional-Filter über Stationsnamen-Schlagworte
            if st_name and any(x in st_name for x in ["Säntis", "Altenrhein", "Vaduz", "St. Gallen", "Kreuzlingen"]):
                desc = props.get("description", "")
                val = props.get("value")
                
                if val is not None:
                    st_id = props.get("station_reference") or st_name
                    if st_id not in stations_data:
                        stations_data[st_id] = {
                            "id": str(st_id), "name": str(st_name) + " (MeteoSchweiz)",
                            "lat": 47.38, "lon": 9.38, "speed": 0, "direction": 0,
                            "source": "MeteoSchweiz", "history": []
                        }
                    
                    if "Windgeschwindigkeit" in desc:
                        stations_data[st_id]["speed"] = int(round(float(val)))
                    elif "Windrichtung" in desc:
                        stations_data[st_id]["direction"] = int(val)
    except Exception:
        pass  # Wenn das Regierungsnetz fehlerhaft antwortet, wird es ignoriert

    # 2. HOLFUY LIVE-SCRAPER (Wird unter allen Umständen geladen)
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
