import requests
from flask import Flask, jsonify
from flask_cors import CORS
from datetime import datetime, timedelta
import os

app = Flask(__name__)
CORS(app)

LAT_MIN, LAT_MAX = 47.00, 47.70
LON_MIN, LON_MAX = 9.10, 9.65

def get_swiss_wind_data():
    stations_data = {}
    try:
        live_url = "https://admin.ch"
        live_res = requests.get(live_url, timeout=10).json()
        
        hist_url = "https://admin.ch"
        hist_res = requests.get(hist_url, timeout=10).json()
        
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
            if not geom.get("coordinates"):
                continue
            lon, lat = geom["coordinates"][0], geom["coordinates"][1]
            
            if LAT_MIN <= lat <= LAT_MAX and LON_MIN <= lon <= LON_MAX:
                st_id = props.get("station_reference") or props.get("station_name")
                speed = props.get("wind_speed")
                if speed is not None:
                    history = history_map.get(st_id, [])
                    history = sorted(history, key=lambda x: x["time"])
                    stations_data[st_id] = {
                        "id": st_id,
                        "name": props.get("station_name", "Unbekannt"),
                        "lat": lat,
                        "lon": lon,
                        "speed": round(float(speed)),
                        "direction": props.get("wind_direction", 0) or 0,
                        "source": "MeteoSchweiz",
                        "history": history
                    }
                    
        mock_spots = [
            {
                "id": "HF_KREUZ", "name": "Kreuzlingen Hafen (Holfuy)", "lat": 47.6512, "lon": 9.1824, "speed": 14, "direction": 240, "source": "Holfuy",
                "history": [{"time": "10:00", "speed": 10}, {"time": "11:00", "speed": 12}, {"time": "12:00", "speed": 15}, {"time": "13:00", "speed": 14}]
            },
            {
                "id": "WM_EBEN", "name": "Ebenalp (Winds.mobi)", "lat": 47.2842, "lon": 9.4125, "speed": 28, "direction": 190, "source": "Winds.mobi",
                "history": [{"time": "10:00", "speed": 20}, {"time": "11:00", "speed": 22}, {"time": "12:00", "speed": 25}, {"time": "13:00", "speed": 28}]
            },
            {
                "id": "HF_VADUZ", "name": "Vaduz Rhein (Holfuy)", "lat": 47.1415, "lon": 9.5215, "speed": 8, "direction": 340, "source": "Holfuy",
                "history": [{"time": "10:00", "speed": 5}, {"time": "11:00", "speed": 7}, {"time": "12:00", "speed": 9}, {"time": "13:00", "speed": 8}]
            }
        ]
        for spot in mock_spots:
            if LAT_MIN <= spot["lat"] <= LAT_MAX and LON_MIN <= spot["lon"] <= LON_MAX:
                if spot["id"] not in stations_data:
                    stations_data[spot["id"]] = spot
    except Exception as e:
        print(e)
    return list(stations_data.values())

@app.route("/api/wind")
def wind_data():
    return jsonify(get_swiss_wind_data())

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
