# 661aTransport

Live Brussels tram departures and monitored STIB service updates.

## Current app

- Belgian Mobility `WaitingTimes` for:
  - `5830` Bens toward Albert
  - `0711` Albert toward Van Haelen
  - `5058` Heros / Helden with grouped departures for line `4` and line `92`
- Belgian Mobility `TravellersInformation`, limited to:
  - metro lines `1`, `2`, `5`, `6`
  - tram lines `18`, `4`, `10`, `92`
- Duplicate and low-priority advisories filtered before rendering
- `/healthz` endpoint for health checks

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

Do not commit live keys into the repository.

## Vercel

This app now supports Vercel's Flask runtime through [app.py](/tmp/661aTransport-review/app.py). Static assets are duplicated under `public/static/**` for Vercel CDN delivery.

Typical setup:

```bash
vercel
vercel env add BELGIAN_MOBILITY_BASE_URL production
vercel env add BELGIAN_MOBILITY_SUBSCRIPTION_KEY production
vercel env add BELGIAN_MOBILITY_SECONDARY_KEY production
vercel env add STIB_DATA_SOURCE production
vercel --prod
```

Recommended values:

- `BELGIAN_MOBILITY_BASE_URL=https://api-management-discovery-production.azure-api.net/api/datasets/stibmivb`
- `STIB_DATA_SOURCE=belgian_mobility`

Use `vercel dev` for local Vercel-style development once the virtualenv is installed.

## Render

The existing Render service is still:

- Service ID: `srv-d17r682dbo4c73denor0`
- URL: `https://six61atransport.onrender.com`

Recommended runtime command:

```bash
gunicorn --bind 0.0.0.0:$PORT 661ACode:app
```
