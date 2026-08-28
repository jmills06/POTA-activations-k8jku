# K8JKU Michigan POTA Dashboard

A 1080x1920 portrait dashboard showing K8JKU's Parks on the Air activations
across Michigan. Built for a Dakboard screen, but it is just a static page --
open the URL in any browser.

**Live URL:** https://jmills06.github.io/POTA-activations-k8jku/

## Layout

| File | Purpose |
| --- | --- |
| `index.html` | The whole dashboard: map, stats, recent activations. No build step. |
| `data/pota_activations.json` | K8JKU's activation log, refreshed daily. |
| `data/Michigan_POTA_Parks.json` | All 371 Michigan POTA parks with coordinates, refreshed daily. |
| `.github/workflows/download-json.yml` | Pulls both JSON files from the source bucket at 05:00 UTC and commits them. |
| `.github/workflows/pages.yml` | Publishes the repo root to GitHub Pages on every push to `main`. |

The page fetches `data/*.json` from its own origin first and falls back to the
Google Storage originals, so it still works opened directly from disk.

## Map markers

| Marker | Meaning |
| --- | --- |
| Blue pulsing star | New park -- first-ever activation within the last 30 days |
| Orange pulsing dot | Fresh -- activated within the last 30 days |
| Red dot | Previously activated |
| Yellow dot | Michigan park not yet activated |

## One-time setup on GitHub

Pages has to be switched on once, in **Settings -> Pages -> Build and
deployment -> Source: GitHub Actions**. After that every push to `main`
(including the daily data commit) redeploys the site automatically.

## Dakboard

Add a **Web Page / iframe** block pointing at the live URL above, sized
1080x1920. The page reloads its own data every 30 minutes, so Dakboard does
not need a refresh interval of its own.

## Tuning

The knobs live at the top of the `<script>` block in `index.html`:

- `FRESH_DAYS` -- how long a park counts as fresh/new (default 30)
- `RECENT_COUNT` -- rows in the recent activations list (default 6)
- `REFRESH_MINUTES` -- data reload cadence (default 30)
- `MICHIGAN_CENTER` / `MICHIGAN_ZOOM` -- map framing; changing these needs a
  visual re-check that the UP and Isle Royale still fit

## Basemap note

CARTO's `basemaps.cartocdn.com` raster tiles now require an API key and are
served with an "API KEY REQUIRED" watermark rather than failing outright, so
they were removed. The page now uses Esri's keyless Light Gray Canvas and
falls back to OpenStreetMap if those tiles error out or never paint.
