from flask import Flask, render_template_string
import requests
import json
from datetime import datetime
import pytz
import os

app = Flask(__name__)

API_KEY = os.environ.get("STIB_API_KEY")

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

    # You can use any high-res Uccle church photo with public sharing rights
    background_url = "https://www.lesoir.be/sites/default/files/dpistyles_v2/ls_16_9_864w/2016/12/08/node_72437/2500625/public/2016/12/08/B9710464946Z.1_20161208135534_000+GKV84J8SS.2-0.jpg?itok=aoKFKfRq1541614168"
    brussels = pytz.timezone("Europe/Brussels")
    html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <title>Rue Joseph Bens - STIB Tram 18 – Real-Time Brussels Departures</title>
    <meta http-equiv="refresh" content="60" />
    <meta name="viewport" content="width=device-width,initial-scale=1" />
    <link href="https://fonts.googleapis.com/css?family=Montserrat:700,400&display=swap" rel="stylesheet">
    <style>
        html, body { height: 100%; margin: 0; padding: 0; }
        body {
            min-height: 100vh;
            margin: 0;
            font-family: 'Montserrat', 'Arial', sans-serif;
            background: #111217;
            overflow-x: hidden;
        }
        .bg-img {
            position: fixed;
            left: 0; top: 0; width: 100vw; height: 100vh;
            z-index: 0;
            object-fit: cover;
            filter: blur(2.5px) brightness(0.73) grayscale(0.06);
        }
        .overlay {
            position: fixed;
            left: 0; top: 0; width: 100vw; height: 100vh;
            background: linear-gradient(120deg, rgba(0,51,115,0.30) 0%, rgba(240,230,190,0.10) 100%);
            z-index: 1;
        }
        .container {
            position: relative;
            z-index: 2;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 0 0 15px 0;
            width: 100vw;
        }
        .clock-main {
            font-size: 3em;
            color: #e7e7e7;
            font-family: 'Montserrat', monospace;
            font-weight: 900;
            text-align: center;
            text-shadow: 0 6px 34px #00397329, 0 1px 0 #000b;
            margin-top: 48px;
            margin-bottom: 7px;
            letter-spacing: 2.2px;
            width: 100%;
            user-select: none;
        }
        .title {
            font-size: 2.07em;
            color: #ffe259;
            text-shadow: 0 4px 20px #000a;
            text-align: center;
            letter-spacing: 1.5px;
            font-weight: 800;
            margin: 0 0 10px 0;
            width: 100%;
        }
        .refresh-row {
            margin-top: 7px;
            margin-bottom: 14px;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .refresh-icon {
            animation: spin 1.5s linear infinite;
            display: inline-block;
            vertical-align: middle;
            margin-right: 7px;
            font-size: 1.3em;
            color: #38e05a;
        }
        @keyframes spin {
            0% { transform: rotate(0deg);}
            100% { transform: rotate(360deg);}
        }
        .main-grid {
            display: flex;
            flex-direction: row;
            justify-content: center;
            align-items: flex-start;
            gap: 42px;
            width: 100%;
            margin-top: 22px;
            margin-bottom: 10px;
        }
        @media (max-width:1100px) {
            .main-grid { flex-direction: column; align-items: center; gap:14px;}
        }
        .stop-card, .weather-card {
            background: rgba(34, 37, 47, 0.97);
            border-radius: 24px;
            padding: 33px 34px 27px 34px;
            box-shadow: 0 12px 40px 2px #00397327, 0 1.5px 9px #0007;
            min-width: 320px;
            max-width: 390px;
            min-height: 200px;
            margin-bottom: 16px;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: flex-start;
        }
        .stop-dir {
            margin-bottom: 18px;
            font-size: 1.32em;
            color: #fcd900;
            letter-spacing: 1.1px;
            text-align: center;
            font-weight: 800;
            text-shadow: 0 2px 11px #0007;
        }
        .departure {
            background: #fff2;
            margin-bottom: 14px;
            padding: 14px 16px;
            border-radius: 13px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            font-size: 1.15em;
            min-width: 240px;
        }
        .destination {
            color: #fff;
            font-weight: 700;
            margin-right: 14px;
            letter-spacing: 1px;
        }
        .minutes {
            font-size: 1.5em;
            font-weight: 900;
            color: #38e05a;
            margin-left: 10px;
            letter-spacing: 2px;
            text-shadow: 0 1.5px 8px #38e05a67;
        }
        .time {
            font-size: 1.01em;
            color: #ffe259;
            background: #003973d0;
            padding: 2px 13px;
            border-radius: 10px;
            margin-left: 13px;
            font-weight: 500;
        }
        .no-tram {
            color: #ff6f61;
            font-size: 1.13em;
            margin-top: 30px;
            text-align: center;
            font-weight: 700;
            letter-spacing: 1px;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .no-tram-icon {
            font-size: 1.3em;
            margin-right: 6px;
        }
        .weather-card {
            padding: 38px 30px 38px 30px;
            min-height: 210px;
            min-width: 280px;
            max-width: 360px;
            align-items: center;
            justify-content: center;
        }
        .weatherbar-content {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            gap: 19px;
        }
        .weathericon {
            font-size: 2.8em;
            margin-bottom: 7px;
            margin-right: 0;
        }
        .weathertemp {
            font-size: 2.3em;
            font-weight: bold;
            color: #ffe259;
        }
        .weatherdesc {
            font-size: 1.18em;
            font-weight: 700;
            color: #eee;
        }
        .weather-location {
            margin-top: 11px;
            font-size: 1.1em;
            color: #ccc;
            opacity: 0.72;
        }
        .footer {
            margin: 36px 0 12px 0;
            color: #fff8;
            text-align: center;
            font-size: 1em;
            letter-spacing: 1px;
        }
        .atomium {
            display: block;
            margin: 34px auto 12px auto;
            opacity: 0.13;
            height: 70px;
            filter: drop-shadow(0 3px 8px #00397322);
            pointer-events: none;
        }
    </style>
    <script>
    function updateClock() {
        var now = new Date();
        var h = String(now.getHours()).padStart(2, '0');
        var m = String(now.getMinutes()).padStart(2, '0');
        var s = String(now.getSeconds()).padStart(2, '0');
        document.getElementById('clock').innerText = h + ':' + m + ':' + s;
        var sec = 60 - now.getSeconds();
        document.getElementById('nextrefresh').innerText = sec + "s";
    }
    setInterval(updateClock, 1000);

    // Weather
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
                          icon = "☀️";
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
    <img class="bg-img" src="{{ background_url }}" alt="Uccle Church Background"/>
    <div class="overlay"></div>
    <div class="container">
        <div class="clock-main" id="clock"></div>
        <div class="title">Rue Joseph Bens – STIB Tram 18 Departures</div>
        <div class="refresh-row">
            <span class="refresh-icon">⟳</span>
            <span style="color:#eee;">Auto refresh in <span id="nextrefresh">60s</span></span>
        </div>
        <div class="main-grid">
            <div class="stop-card">
                <div class="stop-dir">{{ all_departures[0].name }}</div>
                {% if all_departures[0].departures %}
                    {% for dep in all_departures[0].departures %}
                    <div class="departure">
                        <span class="destination">→ {{ dep.destination }}</span>
                        <span class="minutes">{{ dep.minutes }} min</span>
                        <span class="time">{{ dep.time }}</span>
                    </div>
                    {% endfor %}
                {% else %}
                    <div class="departure no-tram"><span class="no-tram-icon">🚫</span>No upcoming trams.</div>
                {% endif %}
            </div>
            <div class="stop-card">
                <div class="stop-dir">{{ all_departures[1].name }}</div>
                {% if all_departures[1].departures %}
                    {% for dep in all_departures[1].departures %}
                    <div class="departure">
                        <span class="destination">→ {{ dep.destination }}</span>
                        <span class="minutes">{{ dep.minutes }} min</span>
                        <span class="time">{{ dep.time }}</span>
                    </div>
                    {% endfor %}
                {% else %}
                    <div class="departure no-tram"><span class="no-tram-icon">🚫</span>No upcoming trams.</div>
                {% endif %}
            </div>
            <div class="weather-card">
                <div class="weatherbar-content">
                    <span id="weathericon" class="weathericon">⏳</span>
                    <span id="weathertemp" class="weathertemp">--°C</span>
                    <span id="weatherdesc" class="weatherdesc">Loading...</span>
                    <span class="weather-location">Uccle</span>
                </div>
            </div>
        </div>
        <svg class="atomium" viewBox="0 0 100 60"><circle cx="20" cy="50" r="8" fill="#e5e5be"/><circle cx="80" cy="50" r="8" fill="#e5e5be"/><circle cx="50" cy="10" r="9" fill="#ffe259"/><circle cx="50" cy="50" r="8" fill="#e5e5be"/><line x1="20" y1="50" x2="50" y2="10" stroke="#ffe259" stroke-width="3"/><line x1="80" y1="50" x2="50" y2="10" stroke="#ffe259" stroke-width="3"/><line x1="20" y1="50" x2="50" y2="50" stroke="#ffe259" stroke-width="3"/><line x1="50" y1="50" x2="80" y2="50" stroke="#ffe259" stroke-width="3"/></svg>
        <div class="footer">
    Made with ❤️ in Brussels &nbsp;|&nbsp; 
    <a href="https://www.consultantcloud.io" target="_blank" style="text-decoration:none;vertical-align:middle;">
        <img src="https://www.consultantcloud.io/assets/landing-page-theme/img/logo.png"
             alt="ConsultantCloud"
             style="height:1.2em;vertical-align:middle;margin-right:7px;border-radius:5px;box-shadow:0 2px 8px #00397333;">
    </a>
    <span style="font-weight:600;letter-spacing:1px;font-size:1.04em;">
        made by ConsultantCloud
    </span>
    <span style="color:#888;font-size:0.97em;margin-left:9px;">{{ now }}</span>
</div>
    </div>
</body>
</html>
"""
    return render_template_string(
        html,
        all_departures=all_departures,
        now=datetime.now(brussels).strftime('%H:%M:%S'),
        background_url=background_url
    )
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
