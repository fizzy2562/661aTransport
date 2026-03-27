import os
from datetime import datetime
from zoneinfo import ZoneInfo

from flask import Flask, jsonify, render_template_string, url_for

from stib_client import StopConfig, StibClient

app = Flask(__name__)

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
BACKGROUND_FILES = [
    "backgrounds/uccle-street.svg",
    "backgrounds/saint-gilles-rooftops.svg",
    "backgrounds/forest-tramline.svg",
]


def build_dashboard_context() -> dict[str, object]:
    client = StibClient()
    departures_by_stop, departures_error = client.get_departures_for_stops(LINE_ID, STOPS)
    traveller_notices, notices_error = client.get_traveller_notices(LINE_ID, STOPS)

    all_departures = []
    for stop in STOPS:
        all_departures.append(
            {
                "name": stop.label,
                "pointid": stop.pointid,
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
    <title>Line 18 Departures for Bens and Albert</title>
    <meta http-equiv="refresh" content="60" />
    <meta name="viewport" content="width=device-width,initial-scale=1" />
    <meta name="theme-color" content="#3c4a44" />
    <link rel="icon" href="{{ url_for('static', filename='favicon.svg') }}" type="image/svg+xml" />
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Fraunces:wght@600;700&family=Manrope:wght@400;500;700;800&display=swap" rel="stylesheet">
    <style>
        :root {
            --clay: #8d614f;
            --olive: #41534c;
            --ink: #1f2522;
            --sand: #eadac1;
            --cream: #f8f2e8;
            --amber: #d39a4d;
            --mist: rgba(248, 242, 232, 0.16);
            --panel: rgba(30, 36, 34, 0.74);
            --panel-strong: rgba(22, 28, 26, 0.86);
            --border: rgba(248, 242, 232, 0.18);
            --shadow: 0 22px 60px rgba(15, 17, 16, 0.24);
        }

        * { box-sizing: border-box; }
        html, body { margin: 0; min-height: 100%; }
        body {
            font-family: "Manrope", sans-serif;
            color: var(--cream);
            background: #17201d;
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
            filter: saturate(0.96) contrast(1.02) brightness(0.74);
            z-index: 0;
        }

        .bg-layer.is-visible { opacity: 1; }

        .overlay {
            position: fixed;
            inset: 0;
            z-index: 1;
            background:
                radial-gradient(circle at 20% 18%, rgba(234, 218, 193, 0.20), transparent 36%),
                radial-gradient(circle at 82% 16%, rgba(141, 97, 79, 0.20), transparent 28%),
                linear-gradient(180deg, rgba(22, 26, 25, 0.22), rgba(19, 24, 22, 0.78));
        }

        .grain {
            position: fixed;
            inset: 0;
            z-index: 2;
            pointer-events: none;
            opacity: 0.1;
            background-image:
                linear-gradient(rgba(255,255,255,0.06) 1px, transparent 1px),
                linear-gradient(90deg, rgba(255,255,255,0.04) 1px, transparent 1px);
            background-size: 120px 120px;
        }

        .shell {
            position: relative;
            z-index: 3;
            min-height: 100vh;
            padding: 28px 18px 30px;
        }

        .hero {
            max-width: 1200px;
            margin: 0 auto 24px;
            padding: 30px 30px 22px;
            border: 1px solid var(--border);
            border-radius: 28px;
            background: rgba(22, 28, 26, 0.54);
            box-shadow: var(--shadow);
            backdrop-filter: blur(14px);
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
            background: rgba(234, 218, 193, 0.10);
            border: 1px solid rgba(234, 218, 193, 0.18);
            font-size: 0.78rem;
            text-transform: uppercase;
            letter-spacing: 0.16em;
            color: var(--sand);
        }

        .eyebrow-dot {
            width: 9px;
            height: 9px;
            border-radius: 50%;
            background: var(--amber);
            box-shadow: 0 0 0 6px rgba(211, 154, 77, 0.15);
        }

        .title {
            margin: 16px 0 10px;
            font-family: "Fraunces", serif;
            font-size: clamp(2.5rem, 6vw, 4.8rem);
            line-height: 0.95;
            letter-spacing: -0.04em;
            max-width: 10ch;
        }

        .subtitle {
            max-width: 62ch;
            margin: 0;
            color: rgba(248, 242, 232, 0.82);
            font-size: 1.02rem;
            line-height: 1.7;
        }

        .clock-wrap {
            min-width: 240px;
            padding: 18px 20px;
            border-radius: 20px;
            background: rgba(248, 242, 232, 0.10);
            border: 1px solid rgba(248, 242, 232, 0.18);
            text-align: right;
        }

        .clock-label {
            color: rgba(248, 242, 232, 0.68);
            font-size: 0.75rem;
            letter-spacing: 0.16em;
            text-transform: uppercase;
        }

        .clock-value {
            margin-top: 10px;
            font-size: clamp(2.1rem, 4vw, 3rem);
            font-weight: 800;
            letter-spacing: 0.06em;
            color: var(--cream);
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
            background: rgba(248, 242, 232, 0.10);
            border: 1px solid rgba(248, 242, 232, 0.14);
            color: rgba(248, 242, 232, 0.9);
            font-size: 0.92rem;
        }

        .status-pill strong {
            color: var(--sand);
            font-weight: 800;
        }

        .dashboard-grid {
            max-width: 1200px;
            margin: 0 auto;
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 18px;
            align-items: start;
        }

        .panel {
            border: 1px solid var(--border);
            border-radius: 28px;
            background: var(--panel);
            box-shadow: var(--shadow);
            backdrop-filter: blur(16px);
            overflow: hidden;
        }

        .panel-inner { padding: 24px; }

        .panel-kicker {
            color: rgba(234, 218, 193, 0.75);
            font-size: 0.74rem;
            letter-spacing: 0.16em;
            text-transform: uppercase;
            margin-bottom: 10px;
        }

        .panel-title {
            margin: 0 0 6px;
            font-family: "Fraunces", serif;
            font-size: 1.7rem;
            line-height: 1.1;
        }

        .panel-copy {
            margin: 0;
            color: rgba(248, 242, 232, 0.75);
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
            background: rgba(248, 242, 232, 0.10);
            border: 1px solid rgba(248, 242, 232, 0.08);
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
            color: var(--ink);
            background: linear-gradient(135deg, var(--sand), #f0c783);
        }

        .departure-time {
            min-width: 62px;
            text-align: right;
            color: var(--sand);
            font-weight: 700;
        }

        .empty-state {
            margin-top: 18px;
            padding: 16px 18px;
            border-radius: 18px;
            color: rgba(248, 242, 232, 0.78);
            background: rgba(248, 242, 232, 0.08);
            border: 1px solid rgba(248, 242, 232, 0.08);
            line-height: 1.6;
        }

        .weather-panel {
            background:
                linear-gradient(180deg, rgba(61, 73, 67, 0.94), rgba(29, 34, 32, 0.92)),
                rgba(29, 34, 32, 0.92);
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
            color: rgba(248, 242, 232, 0.75);
        }

        .weather-meta {
            display: inline-flex;
            align-items: center;
            gap: 10px;
            width: fit-content;
            padding: 10px 14px;
            border-radius: 999px;
            background: rgba(248, 242, 232, 0.10);
            border: 1px solid rgba(248, 242, 232, 0.08);
        }

        .notice-panel {
            grid-column: 1 / -1;
            background: var(--panel-strong);
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
            min-height: 220px;
            display: flex;
            flex-direction: column;
            gap: 14px;
            padding: 20px;
            border-radius: 22px;
            background: rgba(248, 242, 232, 0.08);
            border: 1px solid rgba(248, 242, 232, 0.10);
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
            background: rgba(211, 154, 77, 0.18);
            color: #ffd6a0;
        }

        .notice-badge.important {
            background: rgba(141, 97, 79, 0.22);
            color: #f5c6b4;
        }

        .notice-badge.advisory {
            background: rgba(65, 83, 76, 0.28);
            color: #cee0d4;
        }

        .notice-kind {
            color: rgba(248, 242, 232, 0.72);
            font-size: 0.84rem;
            font-weight: 700;
        }

        .notice-text {
            margin: 0;
            font-size: 1.05rem;
            line-height: 1.75;
            color: var(--cream);
            flex: 1;
        }

        .notice-meta {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
        }

        .notice-chip {
            padding: 8px 10px;
            border-radius: 999px;
            background: rgba(248, 242, 232, 0.08);
            border: 1px solid rgba(248, 242, 232, 0.08);
            color: rgba(248, 242, 232, 0.78);
            font-size: 0.84rem;
        }

        .footer {
            max-width: 1200px;
            margin: 18px auto 0;
            padding: 0 8px;
            color: rgba(248, 242, 232, 0.68);
            font-size: 0.92rem;
            line-height: 1.7;
        }

        @media (max-width: 1100px) {
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
        const weatherIcons = {
            0: "Sun",
            1: "Clear",
            2: "Clouds",
            3: "Overcast",
            45: "Fog",
            48: "Fog",
            51: "Drizzle",
            53: "Drizzle",
            55: "Drizzle",
            56: "Sleet",
            57: "Sleet",
            61: "Rain",
            63: "Rain",
            65: "Rain",
            66: "Rain",
            67: "Rain",
            71: "Snow",
            73: "Snow",
            75: "Snow",
            77: "Snow",
            80: "Showers",
            81: "Showers",
            82: "Showers",
            85: "Snow",
            86: "Snow",
            95: "Storm",
            96: "Storm",
            99: "Storm"
        };

        function updateClock() {
            const now = new Date();
            const h = String(now.getHours()).padStart(2, "0");
            const m = String(now.getMinutes()).padStart(2, "0");
            const s = String(now.getSeconds()).padStart(2, "0");
            document.getElementById("clock").textContent = h + ":" + m + ":" + s;
            document.getElementById("nextrefresh").textContent = (60 - now.getSeconds()) + "s";
        }

        function updateWeather() {
            fetch("https://api.open-meteo.com/v1/forecast?latitude=50.8073&longitude=4.3368&current_weather=true")
                .then((response) => response.json())
                .then((data) => {
                    if (!data || !data.current_weather) {
                        return;
                    }
                    const weather = data.current_weather;
                    document.getElementById("weather-temp").textContent = Math.round(weather.temperature) + " C";
                    document.getElementById("weather-desc").textContent = weatherIcons[weather.weathercode] || "Conditions";
                })
                .catch(() => {
                    document.getElementById("weather-desc").textContent = "Weather unavailable";
                });
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
            updateWeather();
            setupBackgroundRotation();
            setInterval(updateClock, 1000);
            setInterval(updateWeather, 300000);
        });
    </script>
</head>
<body>
    <img id="bg-primary" class="bg-layer is-visible" src="{{ background_urls[0] }}" alt="Brussels streetscape background" />
    <img id="bg-secondary" class="bg-layer" src="{{ background_urls[1] if background_urls|length > 1 else background_urls[0] }}" alt="" aria-hidden="true" />
    <div class="overlay"></div>
    <div class="grain"></div>

    <main class="shell">
        <section class="hero">
            <div class="hero-top">
                <div>
                    <div class="eyebrow">
                        <span class="eyebrow-dot"></span>
                        Brussels Tram 18
                    </div>
                    <h1 class="title">Bens and Albert departures, shaped for the street.</h1>
                    <p class="subtitle">
                        Real-time departures for the line 18 corridor between Bens and Albert, with broader STIB traveller notices shown underneath for easier reading when service changes matter.
                    </p>
                </div>
                <div class="clock-wrap">
                    <div class="clock-label">Local Brussels time</div>
                    <div id="clock" class="clock-value">{{ updated_at }}</div>
                </div>
            </div>

            <div class="status-row">
                <div class="status-pill">Auto refresh in <strong id="nextrefresh">60s</strong></div>
                <div class="status-pill">Source <strong>{{ data_source.replace('_', ' ') }}</strong></div>
                <div class="status-pill">Updated at <strong>{{ updated_at }}</strong></div>
            </div>
        </section>

        <section class="dashboard-grid">
            {% for stop in all_departures %}
            <article class="panel stop-card">
                <div class="panel-inner">
                    <div class="panel-kicker">Stop {{ stop.pointid }}</div>
                    <h2 class="panel-title">{{ stop.name }}</h2>
                    <p class="panel-copy">Showing the next three departures currently available from the Belgian Mobility STIB feed.</p>

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
                        <div class="weather-meta">Open-Meteo live</div>
                        <div id="weather-temp" class="weather-temp">-- C</div>
                        <div id="weather-desc" class="weather-desc">Loading conditions...</div>
                    </div>
                </div>
            </aside>

            <section class="panel notice-panel">
                <div class="panel-inner">
                    <div class="notice-header">
                        <div>
                            <div class="panel-kicker">Traveller information</div>
                            <h2 class="panel-title">Readable disruption notices</h2>
                            <p class="panel-copy">
                                Notices tied to your journey appear first. When there are none for line 18, the box falls back to the most important current STIB alerts so the space still remains useful.
                            </p>
                        </div>
                        <div class="status-pill">Max 3 notices</div>
                    </div>

                    {% if traveller_notices %}
                    <div class="notice-grid">
                        {% for notice in traveller_notices %}
                        <article class="notice-card">
                            <div class="notice-top">
                                <div class="notice-badge {{ notice.priority_tone }}">{{ notice.priority_label }}</div>
                                <div class="notice-kind">{{ notice.relevance_label }}</div>
                            </div>
                            <p class="notice-text">{{ notice.text }}</p>
                            <div class="notice-meta">
                                <div class="notice-chip">Type {{ notice.type }}</div>
                                <div class="notice-chip">Priority {{ notice.priority }}</div>
                                <div class="notice-chip">
                                    {% if notice.lines %}
                                        Lines {{ notice.lines|join(', ') }}
                                    {% else %}
                                        Network-wide notice
                                    {% endif %}
                                </div>
                            </div>
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

        <footer class="footer">
            Data from Belgian Mobility and STIB-MIVB. Built for the current Render service and refreshed every 60 seconds. The legacy Opendatasoft path remains available only as a rollback source.
        </footer>
    </main>
</body>
</html>
"""
    return render_template_string(html, **build_dashboard_context())


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
