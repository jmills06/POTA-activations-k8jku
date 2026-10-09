# K8JKU Michigan POTA Dashboard

A 1080x1920 portrait dashboard showing K8JKU's Parks on the Air activations
across Michigan. Built for a Dakboard screen, but it is just a static page --
open the URL in any browser.

**Live URL:** https://jmills06.github.io/POTA-activations-k8jku/

The path is case-sensitive: use `POTA` in capitals, as in the repo name.

## Layout

| File | Purpose |
| --- | --- |
| `index.html` | The whole dashboard: map, stats, recent activations. No build step. |
| `data/pota_activations.json` | K8JKU's activation log, refreshed daily. |
| `data/Michigan_POTA_Parks.json` | Every active Michigan POTA park with coordinates (388 as of October 2026), including parks shared with other states. Rebuilt daily from `us_ca_parks.json` by `scripts/build_michigan_parks.py`. |
| `data/activated_parks.json` | Name, coordinates, location and park type for every park K8JKU has activated (any state or country). Built by `scripts/build_activated_parks.py`. |
| `data/us_ca_parks.json` | Every US and Canada POTA park (reference, name, coordinates, grid, location, active flag), one park per line. The source for the Michigan file, and kept for other projects. Built by `scripts/build_us_ca_parks.py`. |
| `scripts/build_us_ca_parks.py` | Downloads POTA's full park list (`pota.app/all_parks_ext.csv`, falling back to `api.pota.app/park/all`) and keeps `US-` and `CA-` parks. The committed file is only replaced if both countries are present and neither shrinks by more than 10%. |
| `scripts/build_michigan_parks.py` | Filters `us_ca_parks.json` down to active `US-MI` parks in the dashboard's format. Refuses to write a list more than 10% shorter than the committed one. `--check` compares instead of writing. |
| `scripts/build_activated_parks.py` | Looks up new references from the activation log via `api.pota.app/park/<ref>`; existing entries are kept, failed lookups retry next run. |
| `.github/workflows/download-json.yml` | At 05:00 UTC pulls the activation log from the source bucket, builds `activated_parks.json`, `us_ca_parks.json` and `Michigan_POTA_Parks.json`, and commits them. |
| `.github/workflows/monthly-michigan-check.yml` | On the 1st of each month downloads POTA's live park list and fails if `Michigan_POTA_Parks.json` no longer matches it, listing the differences in the run summary. GitHub emails you when it fails. |
| `.github/workflows/pages.yml` | Publishes the repo root to GitHub Pages on every push to `main` and after each successful daily download. |

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
redeploys the site automatically. The daily data commit is pushed by the
workflow's own token, which GitHub does not let trigger other workflows, so
`pages.yml` also runs on `workflow_run` when the Daily JSON Downloader
finishes successfully.

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
