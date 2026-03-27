# 661aTransport

Live line 18 departures for the Bens and Albert corridor in Brussels.

## What changed

- Migrated the primary data source to Belgian Mobility `WaitingTimes`
- Added Belgian Mobility `TravellersInformation`
- Reduced the dashboard to two stop cards:
  - `5830` for BENS toward ALBERT
  - `0711` for ALBERT toward VAN HAELEN
- Added rotating local background artwork and a larger notice panel
- Added a `/healthz` endpoint and Render blueprint config

## Local run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python 661ACode.py
```

The app defaults to Belgian Mobility and can still fall back to the legacy STIB source with:

```bash
STIB_DATA_SOURCE=legacy python 661ACode.py
```

## Environment variables

- `BELGIAN_MOBILITY_BASE_URL`
- `BELGIAN_MOBILITY_SUBSCRIPTION_KEY`
- `BELGIAN_MOBILITY_SECONDARY_KEY`
- `STIB_DATA_SOURCE`
- `STIB_API_KEY`
- `PORT`

Do not commit live keys into the repository. Store them only in Render.

## Render

Current live service:

- Service ID: `srv-d17r682dbo4c73denor0`
- URL: `https://six61atransport.onrender.com`

Recommended runtime command:

```bash
gunicorn --bind 0.0.0.0:$PORT 661ACode:app
```
