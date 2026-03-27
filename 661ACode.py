import logging
import os
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
from flask import Flask, jsonify, render_template_string, url_for

from stib_client import StopConfig, StibClient

app = Flask(__name__)
LOGGER = logging.getLogger(__name__)

BRUSSELS = ZoneInfo("Europe/Brussels")
LINE_ID = "18"
STOPS = [
    StopConfig(
        label="in the direction of ALBERT",
        pointid="5830",
        destination="ALBERT",
        static_id="5830F",
    ),
    StopConfig(
        label="in the direction of VAN HAELEN",
        pointid="0711",
        destination="VAN HAELEN",
        static_id="0711F",
    ),
]
STOP_HEADINGS = {
    "5830": "To Work",
    "0711": "To Home",
}
STOP_NAMES = {
    "5830": "Bens",
    "0711": "Albert",
}
STOP_DIRECTIONS = {
    "5830": "Towards Albert",
    "0711": "Towards Van Haelen",
}
BACKGROUND_FILES = [
    "backgrounds/uccle-street.svg",
    "backgrounds/saint-gilles-rooftops.svg",
    "backgrounds/forest-tramline.svg",
]
WEATHER_URL = (
    "https://api.open-meteo.com/v1/forecast"
    "?latitude=50.8073&longitude=4.3368&current_weather=true"
)
WEATHER_LABELS = {
    0: "Sunny",
    1: "Mostly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Foggy",
    48: "Foggy",
    51: "Light drizzle",
    53: "Drizzle",
    55: "Heavy drizzle",
    56: "Freezing drizzle",
    57: "Freezing drizzle",
    61: "Light rain",
    63: "Rain",
    65: "Heavy rain",
    66: "Freezing rain",
    67: "Freezing rain",
    71: "Light snow",
    73: "Snow",
    75: "Heavy snow",
    77: "Snow grains",
    80: "Rain showers",
    81: "Rain showers",
    82: "Heavy showers",
    85: "Snow showers",
    86: "Snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm",
    99: "Thunderstorm",
}


def get_weather_snapshot() -> dict[str, str]:
    try:
        response = requests.get(WEATHER_URL, timeout=10)
        response.raise_for_status()
        payload = response.json()
        current = payload.get("current_weather") or {}
        temperature = current.get("temperature")
        weather_code = current.get("weathercode")
        if temperature is None:
            raise ValueError("Missing current weather temperature")
        return {
            "temperature": f"{round(float(temperature))} C",
            "description": WEATHER_LABELS.get(weather_code, "Current conditions"),
            "meta": "Live in Uccle",
        }
    except Exception:
        LOGGER.exception("Unable to load weather snapshot")
        return {
            "temperature": "--",
            "description": "Weather unavailable",
            "meta": "Weather service offline",
        }


def build_dashboard_context() -> dict[str, object]:
    client = StibClient()
    departures_by_stop, departures_error = client.get_departures_for_stops(LINE_ID, STOPS)
    traveller_notices, notices_error = client.get_traveller_notices(LINE_ID, STOPS)
    weather = get_weather_snapshot()

    all_departures = []
    for stop in STOPS:
        all_departures.append(
            {
                "heading": STOP_HEADINGS.get(stop.pointid, "Line 18"),
                "name": STOP_NAMES.get(stop.pointid, stop.pointid),
                "direction": STOP_DIRECTIONS.get(stop.pointid, stop.label.title()),
                "departures": departures_by_stop.get(stop.pointid, [])[:3],
            }
        )

    return {
        "all_departures": all_departures,
        "departures_error": departures_error,
        "traveller_notices": traveller_notices,
        "notices_error": notices_error,
        "background_urls": [url_for("static", filename=path) for path in BACKGROUND_FILES],
        "data_source": os.getenv("STIB_DATA_SOURCE", "belgian_mobility"),
        "updated_at": datetime.now(BRUSSELS).strftime("%H:%M:%S"),
        "weather": weather,
    }


@app.route("/healthz")
def healthz():
    return jsonify({"status": "ok", "service": "661aTransport"}), 200


@app.route("/")
def dashboard():
    html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8" />
    <title>661A Transport App</title>
    <meta http-equiv="refresh" content="60" />
    <meta name="viewport" content="width=device-width,initial-scale=1" />
    <meta name="theme-color" content="#00B8E6" />
    <link rel="icon" href="{{ url_for('static', filename='favicon.svg') }}" type="image/svg+xml" />
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root {
            --cyan: #00b8e6;
            --teal: #1ad9be;
            --green: #00cc66;
            --bg: #f8f9fa;
            --surface: rgba(255, 255, 255, 0.95);
            --surface-strong: #ffffff;
            --surface-soft: #eef5f7;
            --text: #12202d;
            --muted: #5c6d79;
            --border: rgba(18, 32, 45, 0.10);
            --shadow: 0 18px 46px rgba(18, 48, 77, 0.10);
            --accent: linear-gradient(135deg, var(--cyan), var(--teal) 52%, var(--green));
        }

        * { box-sizing: border-box; }
        html, body { margin: 0; min-height: 100%; }
        body {
            font-family: "Inter", sans-serif;
            color: var(--text);
            background: var(--bg);
            overflow-x: hidden;
        }

        .bg-layer {
            position: fixed;
            inset: 0;
            width: 100%;
            height: 100%;
            object-fit: cover;
            opacity: 0;
            transition: opacity 1.4s ease;
            filter: saturate(1.02) contrast(1.02) brightness(1.08);
            z-index: 0;
        }

        .bg-layer.is-visible { opacity: 1; }

        .overlay {
            position: fixed;
            inset: 0;
            z-index: 1;
            background:
                radial-gradient(circle at 16% 12%, rgba(0, 184, 230, 0.14), transparent 28%),
                radial-gradient(circle at 84% 10%, rgba(0, 204, 102, 0.12), transparent 24%),
                linear-gradient(180deg, rgba(248, 249, 250, 0.74), rgba(248, 249, 250, 0.96));
        }

        .grain {
            position: fixed;
            inset: 0;
            z-index: 2;
            pointer-events: none;
            opacity: 0.04;
            background-image:
                linear-gradient(rgba(18,32,45,0.04) 1px, transparent 1px),
                linear-gradient(90deg, rgba(18,32,45,0.03) 1px, transparent 1px);
            background-size: 144px 144px;
        }

        .shell {
            position: relative;
            z-index: 3;
            min-height: 100vh;
            padding: 22px 18px 30px;
        }

        .topbar {
            max-width: 1200px;
            margin: 0 auto 18px;
            padding: 16px 22px;
            border: 1px solid rgba(18, 32, 45, 0.08);
            border-radius: 24px;
            background: rgba(255, 255, 255, 0.92);
            box-shadow: var(--shadow);
            backdrop-filter: blur(18px);
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 18px;
        }

        .brand-lockup {
            display: flex;
            align-items: center;
            gap: 14px;
        }

        .brand-mark {
            width: 46px;
            height: 46px;
            border-radius: 16px;
            background: var(--accent);
            box-shadow: 0 12px 28px rgba(0, 184, 230, 0.24);
            position: relative;
        }

        .brand-mark::after {
            content: "";
            position: absolute;
            inset: 9px;
            border-radius: 12px;
            background: rgba(255, 255, 255, 0.86);
            clip-path: polygon(0 100%, 0 36%, 38% 36%, 38% 0, 100% 0, 100% 62%, 62% 62%, 62% 100%);
        }

        .brand-name {
            font-size: 1.06rem;
            font-weight: 800;
            letter-spacing: -0.02em;
        }

        .brand-subtitle {
            margin-top: 3px;
            color: var(--muted);
            font-size: 0.9rem;
            font-weight: 500;
        }

        .route-badge {
            padding: 10px 14px;
            border-radius: 999px;
            background: rgba(0, 184, 230, 0.10);
            border: 1px solid rgba(0, 184, 230, 0.12);
            color: #007d9d;
            font-size: 0.84rem;
            font-weight: 700;
        }

        .hero {
            max-width: 1200px;
            margin: 0 auto 24px;
            padding: 32px 32px 24px;
            border: 1px solid var(--border);
            border-radius: 28px;
            background:
                linear-gradient(135deg, rgba(0, 184, 230, 0.10), rgba(26, 217, 190, 0.10) 42%, rgba(255,255,255,0.96) 42%),
                rgba(255,255,255,0.96);
            box-shadow: var(--shadow);
            backdrop-filter: blur(18px);
        }

        .hero-top {
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            gap: 20px;
            margin-bottom: 20px;
        }

        .eyebrow {
            display: inline-flex;
            align-items: center;
            gap: 10px;
            padding: 8px 14px;
            border-radius: 999px;
            background: rgba(0, 184, 230, 0.08);
            border: 1px solid rgba(0, 184, 230, 0.12);
            font-size: 0.78rem;
            text-transform: uppercase;
            letter-spacing: 0.16em;
            color: #007d9d;
        }

        .eyebrow-dot {
            width: 9px;
            height: 9px;
            border-radius: 50%;
            background: var(--green);
            box-shadow: 0 0 0 6px rgba(0, 204, 102, 0.12);
        }

        .title {
            margin: 16px 0 10px;
            font-size: clamp(2.4rem, 5.2vw, 4.3rem);
            line-height: 0.98;
            letter-spacing: -0.05em;
            font-weight: 800;
            max-width: 12ch;
        }

        .subtitle {
            max-width: 62ch;
            margin: 0;
            color: var(--muted);
            font-size: 1.02rem;
            line-height: 1.65;
        }

        .clock-wrap {
            min-width: 240px;
            padding: 18px 20px;
            border-radius: 20px;
            background: rgba(255, 255, 255, 0.78);
            border: 1px solid rgba(18, 32, 45, 0.08);
            text-align: right;
        }

        .clock-label {
            color: var(--muted);
            font-size: 0.75rem;
            letter-spacing: 0.16em;
            text-transform: uppercase;
        }

        .clock-value {
            margin-top: 10px;
            font-size: clamp(2.1rem, 4vw, 3rem);
            font-weight: 800;
            letter-spacing: 0.06em;
            color: var(--text);
        }

        .status-row {
            display: flex;
            flex-wrap: wrap;
            align-items: center;
            gap: 12px;
        }

        .status-pill {
            padding: 10px 14px;
            border-radius: 999px;
            background: rgba(255, 255, 255, 0.84);
            border: 1px solid rgba(18, 32, 45, 0.08);
            color: var(--muted);
            font-size: 0.92rem;
        }

        .status-pill strong {
            color: var(--text);
            font-weight: 800;
        }

        .dashboard-grid {
            max-width: 1200px;
            margin: 0 auto;
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 18px;
            align-items: stretch;
        }

        .panel {
            border: 1px solid var(--border);
            border-radius: 28px;
            background: var(--surface);
            box-shadow: var(--shadow);
            backdrop-filter: blur(18px);
            overflow: hidden;
            height: 100%;
        }

        .panel-inner { padding: 24px; }

        .panel-kicker {
            color: #0a8cad;
            font-size: 0.74rem;
            letter-spacing: 0.16em;
            text-transform: uppercase;
            margin-bottom: 10px;
            font-weight: 700;
        }

        .panel-title {
            margin: 0 0 6px;
            font-size: 1.7rem;
            line-height: 1.1;
            font-weight: 800;
        }

        .panel-copy {
            margin: 0;
            color: var(--muted);
            line-height: 1.6;
        }

        .stop-card .panel-title {
            font-size: 1.45rem;
            min-height: 3.1rem;
        }

        .departure-list {
            display: flex;
            flex-direction: column;
            gap: 12px;
            margin-top: 18px;
        }

        .departure {
            display: grid;
            grid-template-columns: 1fr auto auto;
            align-items: center;
            gap: 12px;
            padding: 14px 16px;
            border-radius: 18px;
            background: var(--surface-soft);
            border: 1px solid rgba(18, 32, 45, 0.06);
        }

        .departure-destination {
            font-weight: 800;
            letter-spacing: 0.04em;
        }

        .departure-minutes {
            min-width: 64px;
            padding: 8px 12px;
            border-radius: 999px;
            text-align: center;
            font-weight: 800;
            color: white;
            background: var(--accent);
        }

        .departure-time {
            min-width: 62px;
            text-align: right;
            color: #0387a8;
            font-weight: 700;
        }

        .empty-state {
            margin-top: 18px;
            padding: 16px 18px;
            border-radius: 18px;
            color: var(--muted);
            background: var(--surface-soft);
            border: 1px solid rgba(18, 32, 45, 0.06);
            line-height: 1.6;
        }

        .weather-panel {
            background:
                linear-gradient(180deg, rgba(0, 184, 230, 0.08), rgba(26, 217, 190, 0.12)),
                rgba(255, 255, 255, 0.98);
        }

        .weather-current {
            display: flex;
            flex-direction: column;
            gap: 12px;
            margin-top: 22px;
        }

        .weather-temp {
            font-size: clamp(3rem, 5vw, 4rem);
            font-weight: 800;
            line-height: 1;
        }

        .weather-desc {
            font-size: 1.08rem;
            color: var(--muted);
        }

        .weather-meta {
            display: inline-flex;
            align-items: center;
            gap: 10px;
            width: fit-content;
            padding: 10px 14px;
            border-radius: 999px;
            background: rgba(0, 184, 230, 0.08);
            border: 1px solid rgba(0, 184, 230, 0.10);
            color: #007d9d;
            font-weight: 700;
        }

        .notice-panel {
            grid-column: 1 / -1;
            background: var(--surface-strong);
        }

        .notice-header {
            display: flex;
            align-items: end;
            justify-content: space-between;
            gap: 18px;
            margin-bottom: 18px;
        }

        .notice-grid {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 14px;
        }

        .notice-card {
            min-height: 240px;
            display: flex;
            flex-direction: column;
            gap: 14px;
            padding: 20px;
            border-radius: 22px;
            background: linear-gradient(180deg, rgba(0, 184, 230, 0.03), rgba(26, 217, 190, 0.05));
            border: 1px solid rgba(18, 32, 45, 0.06);
        }

        .notice-top {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 14px;
        }

        .notice-badge {
            display: inline-flex;
            align-items: center;
            gap: 10px;
            padding: 8px 12px;
            border-radius: 999px;
            text-transform: uppercase;
            letter-spacing: 0.12em;
            font-size: 0.72rem;
            font-weight: 800;
        }

        .notice-badge.major {
            background: rgba(0, 184, 230, 0.14);
            color: #007d9d;
        }

        .notice-badge.important {
            background: rgba(26, 217, 190, 0.14);
            color: #018c79;
        }

        .notice-badge.advisory {
            background: rgba(0, 204, 102, 0.12);
            color: #13834a;
        }

        .notice-kind {
            color: var(--muted);
            font-size: 0.84rem;
            font-weight: 700;
        }

        .notice-text {
            margin: 0;
            font-size: 1.05rem;
            line-height: 1.75;
            color: var(--text);
            flex: 1;
        }

        .notice-date {
            margin: -2px 0 0;
            color: #007d9d;
            font-size: 0.86rem;
            font-weight: 700;
        }

        .notice-meta {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
        }

        .notice-chip {
            padding: 8px 10px;
            border-radius: 999px;
            background: rgba(0, 184, 230, 0.06);
            border: 1px solid rgba(0, 184, 230, 0.10);
            color: #0a8cad;
            font-size: 0.84rem;
            font-weight: 700;
        }

        @media (max-width: 1100px) {
            .topbar,
            .hero-top,
            .notice-header {
                flex-direction: column;
                align-items: flex-start;
            }

            .clock-wrap {
                width: 100%;
                text-align: left;
            }

            .dashboard-grid {
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }

            .notice-grid {
                grid-template-columns: 1fr;
            }
        }

        @media (max-width: 720px) {
            .shell {
                padding: 14px 14px 24px;
            }

            .topbar,
            .hero,
            .panel {
                border-radius: 22px;
            }

            .hero,
            .panel-inner {
                padding: 20px;
            }

            .dashboard-grid {
                grid-template-columns: 1fr;
            }

            .departure {
                grid-template-columns: 1fr auto;
            }

            .departure-time {
                grid-column: 1 / -1;
                text-align: left;
                padding-left: 2px;
            }
        }
    </style>
    <script>
        const backgroundUrls = {{ background_urls|tojson }};
        function updateClock() {
            const now = new Date();
            const h = String(now.getHours()).padStart(2, "0");
            const m = String(now.getMinutes()).padStart(2, "0");
            const s = String(now.getSeconds()).padStart(2, "0");
            document.getElementById("clock").textContent = h + ":" + m + ":" + s;
            document.getElementById("nextrefresh").textContent = (60 - now.getSeconds()) + "s";
        }

        function setupBackgroundRotation() {
            if (backgroundUrls.length < 2) {
                return;
            }

            const layers = [
                document.getElementById("bg-primary"),
                document.getElementById("bg-secondary")
            ];
            let active = 0;
            let nextIndex = 1;

            function rotateBackground() {
                const incomingIndex = 1 - active;
                const nextUrl = backgroundUrls[nextIndex];
                const preloaded = new Image();

                preloaded.onload = function () {
                    layers[incomingIndex].src = nextUrl;
                    layers[incomingIndex].classList.add("is-visible");
                    layers[active].classList.remove("is-visible");
                    active = incomingIndex;
                    nextIndex = (nextIndex + 1) % backgroundUrls.length;
                };

                preloaded.src = nextUrl;
            }

            setInterval(rotateBackground, 15000);
        }

        window.addEventListener("load", function () {
            updateClock();
            setupBackgroundRotation();
            setInterval(updateClock, 1000);
        });
    </script>
</head>
<body>
    <img id="bg-primary" class="bg-layer is-visible" src="{{ background_urls[0] }}" alt="Brussels streetscape background" />
    <img id="bg-secondary" class="bg-layer" src="{{ background_urls[1] if background_urls|length > 1 else background_urls[0] }}" alt="" aria-hidden="true" />
    <div class="overlay"></div>
    <div class="grain"></div>

    <main class="shell">
        <header class="topbar">
            <div class="brand-lockup">
                <div class="brand-mark" aria-hidden="true"></div>
                <div>
                    <div class="brand-name">ConsultantCloud</div>
                    <div class="brand-subtitle">661A Transport App</div>
                </div>
            </div>
            <div class="route-badge">Brussels Tram 18</div>
        </header>

        <section class="hero">
            <div class="hero-top">
                <div>
                    <div class="eyebrow">
                        <span class="eyebrow-dot"></span>
                        Live commuter view
                    </div>
                    <h1 class="title">661A Transport App</h1>
                    <p class="subtitle">
                        Live line 18 departures between Bens and Albert, with clear service updates underneath.
                    </p>
                </div>
                <div class="clock-wrap">
                    <div class="clock-label">Local Brussels time</div>
                    <div id="clock" class="clock-value">{{ updated_at }}</div>
                </div>
            </div>

            <div class="status-row">
                <div class="status-pill">Auto refresh in <strong id="nextrefresh">60s</strong></div>
                <div class="status-pill">Source <strong>{{ data_source|replace('_', ' ')|title }}</strong></div>
                <div class="status-pill">Updated at <strong>{{ updated_at }}</strong></div>
            </div>
        </section>

        <section class="dashboard-grid">
            {% for stop in all_departures %}
            <article class="panel stop-card">
                <div class="panel-inner">
                    <div class="panel-kicker">{{ stop.heading }}</div>
                    <h2 class="panel-title">{{ stop.name }}</h2>
                    <p class="panel-copy">{{ stop.direction }}</p>

                    {% if stop.departures %}
                    <div class="departure-list">
                        {% for dep in stop.departures %}
                        <div class="departure">
                            <div class="departure-destination">{{ dep.destination }}</div>
                            <div class="departure-minutes">{{ dep.minutes_until }} min</div>
                            <div class="departure-time">{{ dep.time_local }}</div>
                        </div>
                        {% endfor %}
                    </div>
                    {% elif departures_error %}
                    <div class="empty-state">{{ departures_error }}</div>
                    {% else %}
                    <div class="empty-state">No upcoming trams are currently available for this stop.</div>
                    {% endif %}
                </div>
            </article>
            {% endfor %}

            <aside class="panel weather-panel">
                <div class="panel-inner">
                    <div class="panel-kicker">Micro forecast</div>
                    <h2 class="panel-title">Uccle conditions</h2>
                    <p class="panel-copy">Current weather near the tram corridor.</p>
                    <div class="weather-current">
                        <div class="weather-meta">{{ weather.meta }}</div>
                        <div id="weather-temp" class="weather-temp">{{ weather.temperature }}</div>
                        <div id="weather-desc" class="weather-desc">{{ weather.description }}</div>
                    </div>
                </div>
            </aside>

            <section class="panel notice-panel">
                <div class="panel-inner">
                    <div class="notice-header">
                        <div>
                            <div class="panel-kicker">Traveller information</div>
                            <h2 class="panel-title">Service updates</h2>
                            <p class="panel-copy">
                                Updates affecting your route appear first. If none are active, this panel shows the most important current STIB alerts.
                            </p>
                        </div>
                        <div class="status-pill">Up to 6 updates</div>
                    </div>

                    {% if traveller_notices %}
                    <div class="notice-grid">
                        {% for notice in traveller_notices %}
                        <article class="notice-card">
                            <div class="notice-top">
                                <div class="notice-badge {{ notice.priority_tone }}">{{ notice.priority_label }}</div>
                                <div class="notice-kind">{{ notice.scope_label }}</div>
                            </div>
                            <p class="notice-text">{{ notice.text }}</p>
                            {% if notice.linked_date %}
                            <p class="notice-date">Effective from {{ notice.linked_date }}</p>
                            {% endif %}
                            {% if notice.lines %}
                            <div class="notice-meta">
                                <div class="notice-chip">
                                    {% if notice.lines|length == 1 %}
                                        Line {{ notice.lines[0] }}
                                    {% else %}
                                        Lines {{ notice.lines|join(', ') }}
                                    {% endif %}
                                </div>
                            </div>
                            {% endif %}
                        </article>
                        {% endfor %}
                    </div>
                    {% elif notices_error %}
                    <div class="empty-state">{{ notices_error }}</div>
                    {% else %}
                    <div class="empty-state">There are no active traveller notices to display right now.</div>
                    {% endif %}
                </div>
            </section>
        </section>
    </main>
</body>
</html>
"""
    return render_template_string(html, **build_dashboard_context())


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
