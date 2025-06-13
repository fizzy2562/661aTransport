from flask import Flask, render_template_string
import requests
import json
from datetime import datetime
import pytz

app = Flask(__name__)

API_KEY = "fd7111475c6a67de3fbec15188ce31cd17b12c8cb3b8da925929214d"

STOPS = [
    {'name': 'in the direction of VAN HAELEN', 'pointid': '5831'},
    {'name': 'in the direction of Albert', 'pointid': '5830'}
]

def get_departures(pointid):
    url = (
        'https://stibmivb.opendatasoft.com/api/explore/v2.1/catalog/datasets/'
        f'waiting-time-rt-production/records?where=lineid="18" AND pointid="{pointid}"'
        f'&limit=100&apikey={API_KEY}'
    )
    try:
        r = requests.get(url, timeout=10)
        results = r.json().get('results', [])
        departures = []
        for record in results:
            passingtimes = json.loads(record.get('passingtimes', '[]'))
            for passage in passingtimes:
                dest = passage.get('destination', {}).get('fr', "?")
                arr_time_iso = passage.get('expectedArrivalTime')
                if arr_time_iso and "T" in arr_time_iso:
                    arr_time = datetime.fromisoformat(arr_time_iso.replace("Z", "+00:00"))
                    brussels = pytz.timezone("Europe/Brussels")
                    arr_time = arr_time.astimezone(brussels)
                    now = datetime.now(brussels)
                    minutes = int((arr_time - now).total_seconds() // 60)
                    time_str = arr_time.strftime("%H:%M")
                else:
                    time_str = "?"
                    minutes = "?"
                departures.append({
                    'destination': dest,
                    'time': time_str,
                    'minutes': minutes
                })
        departures = sorted(departures, key=lambda x: (x['minutes'] if isinstance(x['minutes'], int) else 999))
        departures = [dep for dep in departures if isinstance(dep['minutes'], int) and dep['minutes'] >= 0]
        return departures
    except Exception as e:
        return [{'destination': '', 'time': f"Error: {e}", 'minutes': '?'}]

@app.route('/')
def dashboard():
    all_departures = []
    for stop in STOPS:
        departures = get_departures(stop['pointid'])[:3]
        all_departures.append({'name': stop['name'], 'departures': departures})
    html = """
<!DOCTYPE html>
<html>
<head>
    <title>Rue Joseph Bens - STIB Tram 18 – Real-Time Brussels Departures</title>
    <meta http-equiv="refresh" content="60" />
    <link href="https://fonts.googleapis.com/css?family=Montserrat:700,400&display=swap" rel="stylesheet">
    <style>
        html, body {
            height: 100%;
            margin: 0;
        }
        body {
            min-height: 100vh;
            margin: 0;
            padding: 0;
            font-family: 'Montserrat', 'Arial', sans-serif;
            background: #10151a;
            overflow-x: hidden;
        }
        .bg-img {
            position: fixed;
            left: 0; top: 0; width: 100vw; height: 100vh;
            z-index: 0;
            object-fit: cover;
            filter: blur(3px) brightness(0.8) grayscale(0.1);
        }
        .overlay {
            position: fixed;
            left: 0; top: 0; width: 100vw; height: 100vh;
            background: linear-gradient(130deg, rgba(0,51,115,0.5) 0%, rgba(235,235,186,0.25) 100%);
            z-index: 1;
        }
        .container {
            position: relative;
            z-index: 2;
            display: flex;
            flex-direction: column;
            align-items: center;
            min-height: 100vh;
            justify-content: flex-start;
        }
        .title {
            margin-top: 48px;
            font-size: 2.6em;
            color: #ffe259;
            text-shadow: 0 4px 24px #000b;
            text-align: center;
            letter-spacing: 1.5px;
            font-weight: 800;
        }
        .clock {
            font-size: 2.2em;
            margin: 20px 0 32px 0;
            color: #54ff97;
            font-family: 'Montserrat', monospace;
            text-align: center;
            letter-spacing: 2px;
            text-shadow: 0 4px 18px #00397344;
        }
        .main-flex-row {
            width: 100%;
            display: flex;
            flex-direction: row;
            align-items: flex-start;
            justify-content: center;
            gap: 42px;
            margin-top: 10px;
        }
        .stops-flex {
            display: flex;
            flex-wrap: wrap;
            gap: 48px;
            justify-content: center;
            width: 100%;
        }
        .stop-card {
            background: rgba(34, 37, 47, 0.97);
            border-radius: 24px;
            padding: 36px 38px 26px 38px;
            box-shadow: 0 12px 40px 2px #00397355, 0 1.5px 9px #0008;
            min-width: 340px;
            max-width: 390px;
            min-height: 260px;
            margin-bottom: 32px;
        }
        .stop-dir {
            margin-top: 0;
            margin-bottom: 28px;
            font-size: 1.45em;
            color: #fcd900;
            letter-spacing: 1.2px;
            text-align: center;
            font-weight: 700;
            text-shadow: 0 2px 12px #0008;
        }
        .departure {
            background: #fff2;
            margin-bottom: 18px;
            padding: 16px 20px;
            border-radius: 14px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            font-size: 1.17em;
        }
        .destination {
            color: #fff;
            font-weight: 600;
            margin-right: 20px;
            letter-spacing: 1px;
        }
        .minutes {
            font-size: 1.45em;
            font-weight: 900;
            color: #38e05a;
            margin-left: 16px;
            letter-spacing: 2px;
            text-shadow: 0 1.5px 8px #38e05a77;
        }
        .time {
            font-size: 1.08em;
            color: #ffe259;
            background: #003973dd;
            padding: 2px 13px 2px 13px;
            border-radius: 10px;
            margin-left: 17px;
            font-weight: 500;
        }
        .no-tram {
            color: #ff6f61;
            font-size: 1.1em;
            margin-top: 30px;
            text-align: center;
            font-weight: 700;
        }
        .weatherbox {
            align-self: flex-start;
            position: static;
            margin-top: 30px;
            background: rgba(30,30,30,0.72);
            color: #fff;
            border-radius: 18px;
            padding: 13px 30px 13px 22px;
            font-size: 1.12em;
            font-family: inherit;
            font-weight: 500;
            display: flex;
            align-items: center;
            box-shadow: 0 2px 15px #0006;
            z-index: 3;
        }
        .weathericon {
            width: 34px;
            height: 34px;
            margin-right: 13px;
            margin-left: -10px;
            filter: drop-shadow(0 2px 6px #00397322);
        }
        .atomium {
            display: block;
            margin: 34px auto 12px auto;
            opacity: 0.14;
            height: 90px;
            filter: drop-shadow(0 3px 8px #00397333);
            pointer-events: none;
        }
        .footer {
            margin: 32px 0 13px 0;
            color: #fff8;
            text-align: center;
            font-size: 1em;
            letter-spacing: 1px;
        }
        @media (max-width: 1200px) {
            .main-flex-row { flex-direction: column; align-items: center; gap: 12px;}
            .weatherbox { margin-top: 24px; margin-bottom: 12px;}
        }
        @media (max-width: 1000px) {
            .stops-flex { flex-direction: column; align-items: center;}
            .stop-card { width: 95%; max-width: 99vw; }
            .container { padding: 0 4vw;}
        }
    </style>
    <script>
    function updateClock() {
        var now = new Date();
        var h = String(now.getHours()).padStart(2, '0');
        var m = String(now.getMinutes()).padStart(2, '0');
        var s = String(now.getSeconds()).padStart(2, '0');
        document.getElementById('clock').innerText = h + ':' + m + ':' + s;
    }
    // WEATHER INTEGRATION FOR UCCLE, BRUSSELS
    const weatherIcons = {
        0: "☀️", 1: "🌤️", 2: "⛅", 3: "☁️",
        45: "🌫️", 48: "🌫️",
        51: "🌦️", 53: "🌦️", 55: "🌦️",
        56: "🌧️", 57: "🌧️",
        61: "🌧️", 63: "🌧️", 65: "🌧️",
        66: "🌧️", 67: "🌧️",
        71: "❄️", 73: "❄️", 75: "❄️", 77: "❄️",
        80: "🌦️", 81: "🌧️", 82: "🌧️",
        85: "🌨️", 86: "🌨️",
        95: "⛈️", 96: "⛈️", 99: "⛈️"
    };
    const weatherCodes = {
        0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
        45: "Fog", 48: "Fog",
        51: "Drizzle", 53: "Drizzle", 55: "Drizzle",
        56: "Freezing drizzle", 57: "Freezing drizzle",
        61: "Rain", 63: "Rain", 65: "Rain",
        66: "Freezing rain", 67: "Freezing rain",
        71: "Snow", 73: "Snow", 75: "Snow", 77: "Snow grains",
        80: "Rain showers", 81: "Rain showers", 82: "Rain showers",
        85: "Snow showers", 86: "Snow showers",
        95: "Thunderstorm", 96: "Thunderstorm", 99: "Thunderstorm"
    };
    const rainCodes = [51,53,55,56,57,61,63,65,66,67,80,81,82,95,96,99];
    const snowCodes = [71,73,75,77,85,86];

    function updateWeather() {
        fetch("https://api.open-meteo.com/v1/forecast?latitude=50.7987&longitude=4.3369&current_weather=true")
          .then(response => response.json())
          .then(data => {
              if (data && data.current_weather) {
                  const w = data.current_weather;
                  const temp = Math.round(w.temperature);
                  const code = w.weathercode;
                  const prec = w.precipitation;
                  let icon, desc;

                  if (prec > 0) {
                      if (snowCodes.includes(code)) {
                          icon = "❄️";
                          desc = "Snowing";
                      } else {
                          icon = "🌧️";
                          desc = "Raining";
                      }
                  } else {
                      if (rainCodes.includes(code) || snowCodes.includes(code)) {
                          icon = "☀️";  // DRY/SUNNY icon
                          desc = "Dry";
                      } else {
                          icon = weatherIcons[code] || "☀️";
                          desc = weatherCodes[code] || "Unknown";
                      }
                  }
                  document.getElementById("weathericon").textContent = icon;
                  document.getElementById("weathertemp").textContent = temp + "°C";
                  document.getElementById("weatherdesc").textContent = desc;
              }
          });
    }
    setInterval(updateWeather, 5 * 60 * 1000);
    window.onload = function() { updateWeather(); updateClock(); };
    </script>
</head>
<body>
    <img class="bg-img" src="https://images.unsplash.com/photo-1464983953574-0892a716854b?auto=format&fit=crop&w=1200&q=80" alt="Brussels background"/>
    <div class="overlay"></div>
    <div class="container">
        <div class="title">Rue Joseph Bens - STIB Tram 18 – Real-Time Brussels Departures</div>
        <div class="clock" id="clock"></div>
        <div class="main-flex-row">
            <div class="stops-flex">
                {% for stop in stops %}
                <div class="stop-card">
                    <div class="stop-dir">{{ stop.name }}</div>
                    {% if stop.departures %}
                        {% for dep in stop.departures %}
                        <div class="departure">
                            <span class="destination">→ {{ dep.destination }}</span>
                            <span class="minutes">{{ dep.minutes }} min</span>
                            <span class="time">{{ dep.time }}</span>
                        </div>
                        {% endfor %}
                    {% else %}
                        <div class="departure no-tram">No upcoming trams.</div>
                    {% endif %}
                </div>
                {% endfor %}
            </div>
            <div class="weatherbox">
                <span id="weathericon" class="weathericon">⏳</span>
                <span id="weathertemp" style="margin-right: 14px;">--°C</span>
                <span id="weatherdesc" style="opacity: 0.88;">Loading...</span>
                <span style="margin-left:12px;font-size:0.88em;opacity:0.6;">Uccle</span>
            </div>
        </div>
        <!-- Inline SVG Atomium: works even offline -->
        <svg class="atomium" viewBox="0 0 100 60"><circle cx="20" cy="50" r="8" fill="#e5e5be"/><circle cx="80" cy="50" r="8" fill="#e5e5be"/><circle cx="50" cy="10" r="9" fill="#ffe259"/><circle cx="50" cy="50" r="8" fill="#e5e5be"/><line x1="20" y1="50" x2="50" y2="10" stroke="#ffe259" stroke-width="3"/><line x1="80" y1="50" x2="50" y2="10" stroke="#ffe259" stroke-width="3"/><line x1="20" y1="50" x2="50" y2="50" stroke="#ffe259" stroke-width="3"/><line x1="50" y1="50" x2="80" y2="50" stroke="#ffe259" stroke-width="3"/></svg>
        <div class="footer">
            Made with ❤️ in Brussels &middot; {{ now }}
        </div>
    </div>
</body>
</html>
"""
    brussels = pytz.timezone("Europe/Brussels")
    return render_template_string(html, stops=all_departures, now=datetime.now(brussels).strftime('%H:%M:%S'))

if __name__ == '__main__':
   import os
port = int(os.environ.get("PORT", 5050))
app.run(host="0.0.0.0", port=port)
