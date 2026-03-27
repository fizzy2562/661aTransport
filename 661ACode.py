import logging
import os
from datetime import datetime
from zoneinfo import ZoneInfo

from flask import Flask, jsonify, render_template_string, url_for

from stib_client import StopConfig, StibClient

app = Flask(__name__)
LOGGER = logging.getLogger(__name__)

BRUSSELS = ZoneInfo("Europe/Brussels")
LINE_ID = "18"
LINE18_STOPS = [
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
HEROS_STOP = StopConfig(
    label="Towards Gare du Nord and Gare de Schaerbeek",
    pointid="5058",
    destination="GARE DU NORD",
    static_id="5058F",
)
MONITORED_NOTICE_LINES = ["1", "2", "5", "6", "18", "4", "10", "92"]
BACKGROUND_FILES = [
    "backgrounds/uccle-street.svg",
    "backgrounds/saint-gilles-rooftops.svg",
    "backgrounds/forest-tramline.svg",
]


def build_dashboard_context() -> dict[str, object]:
    client = StibClient()
    departures_by_stop, departures_error = client.get_departures_for_stops(LINE_ID, LINE18_STOPS)
    heros_line4, heros_line4_error = client.get_departures_for_stops("4", [HEROS_STOP])
    heros_line92, heros_line92_error = client.get_departures_for_stops("92", [HEROS_STOP])
    traveller_notices, notices_error = client.get_traveller_notices(
        MONITORED_NOTICE_LINES,
        LINE18_STOPS + [HEROS_STOP],
    )

    all_departures = [
        {
            "heading": "To Work",
            "name": "Bens",
            "direction": "Towards Albert",
            "display_mode": "single",
            "departures": departures_by_stop.get("5830", [])[:3],
            "error": departures_error,
        },
        {
            "heading": "To Home",
            "name": "Albert",
            "direction": "Towards Van Haelen",
            "display_mode": "single",
            "departures": departures_by_stop.get("0711", [])[:3],
            "error": departures_error,
        },
        {
            "heading": "Heros",
            "name": "Heros / Helden",
            "direction": "Lines 4 and 92 towards Gare du Nord and Gare de Schaerbeek",
            "display_mode": "grouped",
            "error": heros_line4_error or heros_line92_error,
            "line_groups": [
                {
                    "line_id": "4",
                    "label": "Gare du Nord",
                    "departures": heros_line4.get(HEROS_STOP.pointid, [])[:2],
                },
                {
                    "line_id": "92",
                    "label": "Gare de Schaerbeek",
                    "departures": heros_line92.get(HEROS_STOP.pointid, [])[:2],
                },
            ],
        },
    ]

    return {
        "all_departures": all_departures,
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

        .line-groups {
            display: flex;
            flex-direction: column;
            gap: 16px;
            margin-top: 22px;
        }

        .line-group {
            padding: 16px;
            border-radius: 20px;
            background: linear-gradient(180deg, rgba(0, 184, 230, 0.04), rgba(26, 217, 190, 0.06));
            border: 1px solid rgba(18, 32, 45, 0.06);
        }

        .line-group-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 12px;
            margin-bottom: 12px;
        }

        .line-pill {
            display: inline-flex;
            align-items: center;
            padding: 8px 12px;
            border-radius: 999px;
            background: var(--accent);
            color: white;
            font-size: 0.82rem;
            font-weight: 800;
            letter-spacing: 0.06em;
        }

        .line-group-title {
            color: #007d9d;
            font-size: 0.95rem;
            font-weight: 700;
            text-align: right;
        }

        .line-departures {
            display: flex;
            flex-direction: column;
            gap: 10px;
        }

        .line-departure {
            display: grid;
            grid-template-columns: auto auto;
            justify-content: space-between;
            align-items: center;
            gap: 12px;
            padding: 12px 14px;
            border-radius: 16px;
            background: rgba(255, 255, 255, 0.82);
            border: 1px solid rgba(18, 32, 45, 0.05);
        }

        .line-minutes {
            font-weight: 800;
            color: var(--text);
        }

        .line-time {
            color: var(--muted);
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

                    {% if stop.display_mode == "grouped" %}
                    <div class="line-groups">
                        {% for group in stop.line_groups %}
                        <section class="line-group">
                            <div class="line-group-header">
                                <div class="line-pill">Line {{ group.line_id }}</div>
                                <div class="line-group-title">{{ group.label }}</div>
                            </div>
                            {% if group.departures %}
                            <div class="line-departures">
                                {% for dep in group.departures %}
                                <div class="line-departure">
                                    <div class="line-minutes">{{ dep.minutes_until }} min</div>
                                    <div class="line-time">{{ dep.time_local }}</div>
                                </div>
                                {% endfor %}
                            </div>
                            {% elif stop.error %}
                            <div class="empty-state">{{ stop.error }}</div>
                            {% else %}
                            <div class="empty-state">No live departures are currently available for line {{ group.line_id }}.</div>
                            {% endif %}
                        </section>
                        {% endfor %}
                    </div>
                    {% elif stop.departures %}
                    <div class="departure-list">
                        {% for dep in stop.departures %}
                        <div class="departure">
                            <div class="departure-destination">{{ dep.destination }}</div>
                            <div class="departure-minutes">{{ dep.minutes_until }} min</div>
                            <div class="departure-time">{{ dep.time_local }}</div>
                        </div>
                        {% endfor %}
                    </div>
                    {% elif stop.error %}
                    <div class="empty-state">{{ stop.error }}</div>
                    {% else %}
                    <div class="empty-state">No upcoming trams are currently available for this stop.</div>
                    {% endif %}
                </div>
            </article>
            {% endfor %}

            <section class="panel notice-panel">
                <div class="panel-inner">
                    <div class="notice-header">
                        <div>
                            <div class="panel-kicker">Traveller information</div>
                            <h2 class="panel-title">Service updates</h2>
                            <p class="panel-copy">
                                Updates are limited to metro lines and trams 18, 4, 10, and 92, with notices for your monitored stops shown first.
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
