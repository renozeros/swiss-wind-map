<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Ostschweiz Live Wind Hub</title>
    <style>
        body { margin: 0; padding: 20px; font-family: 'Segoe UI', Arial, sans-serif; background: #f4f6f9; color: #333; }
        .container { max-width: 800px; margin: 0 auto; background: white; padding: 20px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); }
        h1 { margin-top: 0; color: #007bff; font-size: 24px; }
        .status-badge { display: inline-block; padding: 6px 12px; border-radius: 20px; font-weight: bold; font-size: 14px; margin-bottom: 20px; background: #ffeeba; color: #856404; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; }
        th { background: #007bff; color: white; padding: 12px; text-align: left; }
        td { padding: 12px; border-bottom: 1px solid #dee2e6; }
        tr:nth-child(even) { background: #f8f9fa; }
        .speed-text { font-weight: bold; color: #dc3545; }
        .source-tag { font-size: 11px; padding: 3px 6px; background: #e9ecef; border-radius: 4px; color: #495057; }
    </style>
</head>
<body>

    <div class="container">
        <h1>Live-Windmesswerte: Bodensee - Alpstein - Vaduz</h1>
        <div id="status" class="status-badge">Verbinde zum Wind-Server...</div>
        <div id="table-container"></div>
    </div>

    <script>
        async function loadWindData() {
            const statusEl = document.getElementById("status");
            const containerEl = document.getElementById("table-container");

            try {
                const response = await fetch("https://swiss-wind-backend.onrender.com/api/wind");
                
                if (!response.ok) {
                    throw new Error("HTTP-Fehler " + response.status);
                }

                const stations = await response.json();

                if (stations && stations.length > 0) {
                    let html = "<table>";
                    html += "<tr><th>Station / Messort</th><th>Windstärke</th><th>Richtung</th><th>Netzwerk</th></tr>";

                    stations.forEach(station => {
                        const name = station.name ? station.name : "Unbekannt";
                        const speed = station.speed !== undefined ? station.speed : 0;
                        const direction = station.direction !== undefined ? station.direction : 0;
                        const source = station.source ? station.source : "MeteoSchweiz";

                        html += "<tr>";
                        html += "<td><b>" + name + "</b></td>";
                        html += "<td><span class='speed-text'>" + speed + " km/h</span></td>";
                        html += "<td>" + direction + "°</td>";
                        html += "<td><span class='source-tag'>" + source + "</span></td>";
                        html += "</tr>";
                    });

                    html += "<table>";
                    containerEl.innerHTML = html;
                    
                    statusEl.style.background = "#d4edda";
                    statusEl.style.color = "#155724";
                    statusEl.innerHTML = "🟢 Live: " + stations.length + " Stationen aktiv";
                } else {
                    statusEl.innerHTML = "🔴 Keine Stationen in dieser Region gefunden.";
                }
            } catch (error) {
                statusEl.style.background = "#f8d7da";
                statusEl.style.color = "#721c24";
                statusEl.innerHTML = "🔴 Fehler beim Laden der Daten.";
                console.error(error);
            }
        }

        loadWindData();
        setInterval(loadWindData, 60000);
    </script>
</body>
</html>
