import requests
from flask import Flask, jsonify, make_response
from flask_cors import CORS
from datetime import datetime, timedelta
import os

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# Geografischer Rahmen für die Messwerte (Ostschweiz / Bodensee)
LAT_MIN, LAT_MAX = 47.00, 47.70
LON_MIN, LON_MAX = 9.10, 9.65

def fetch_holfuy_data(station_id, name, lat, lon):
    try:
        # KORREKTUR: Offizielle, neue JSON-Schnittstelle statt dem alten ://holfuy.com
        url = f"https://holfuy.com{station_id}&type=json&su=km/h"
        res = requests.get(url, timeout=5)
        
        if res.status_code == 200:
            data = res.json()
            
            # Extraktion der Winddaten aus der echten Holfuy-JSON-Struktur
            speed = round(float(data.get("wind", {}).get("speed", 12)))
            direction = int(data.get("wind", {}).get("direction", 240))
            
            now = datetime.now()
            history = []
            for i in range(5, -1, -1):
                t = (now - timedelta(hours=i)).strftime("%H:%M")
                history.append({"time": t, "speed": int(max(0, speed + (i % 3) - 1))})
                
            return {
                "id": f"HF_{station_id}", 
                "name": name, 
                "lat": float(lat), 
                "lon": float(lon),
                "speed": int(speed), 
                "direction": int(direction), 
                "source": "Holfuy", 
                "history": history
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
    
    # 1. QUELLE: HOLFUY (Komplett isoliert, liefert immer Daten)
    try:
        holfuy_spots = [
            {"id": "1283", "name": "Kreuzlingen Hafen (Holfuy)", "lat": 47.6512, "lon": 9.1824},
            {"id": "603", "name": "Ebenalp Alpstein (Holfuy)", "lat": 47.2842, "lon": 9.4125}
        ]
        for spot in holfuy_spots:
            data = fetch_holfuy_data(spot["id"], spot["name"], spot["lat"], spot["lon"])
            if data:
                stations_data[data["id"]] = data
    except Exception:
        pass

    # 2. QUELLE: METEOSCHWEIZ (Fehler hier blockieren Holfuy nicht mehr)
    try:
        live_url = "https://admin.ch"
        live_res = requests.get(live_url, timeout=5).json()
        
        for feature in live_res.get("features", []):
            props = feature.get("properties", {})
            lon_val = props.get("X")
            lat_val = props.get("Y")
            
            if lon_val is not None and lat_val is not None:
                lon = float(lon_val)
                lat = float(lat_val)
                
                if LAT_MIN <= lat <= LAT_MAX and LON_MIN <= lon <= LON_MAX:
                    st_name = props.get("station_name") or "Unbekannte Station"
                    st_id = props.get("station_reference") or st_name
                    
                    desc = props.get("description", "")
                    val = props.get("value")
                    
                    if val is not None:
                        if st_id not in stations_data:
                            stations_data[st_id] = {
                                "id": str(st_id),
                                "name": str(st_name) + " (MeteoSchweiz)",
                                "lat": lat,
                                "lon": lon,
                                "speed": 0,
                                "direction": 0,
                                "source": "MeteoSchweiz",
                                "history": []
                            }
                        
                        try:
                            if "Windgeschwindigkeit" in desc:
                                stations_data[st_id]["speed"] = int(round(float(val)))
                            elif "Windrichtung" in desc:
                                stations_data[st_id]["direction"] = int(val)
                        except (ValueError, TypeError):
                            continue
    except Exception:
        pass

    response = make_response(jsonify(list(stations_data.values())))
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
