#!/usr/bin/env python3
"""Build data/us_ca_parks.json: every POTA park in the US and Canada.

Downloads POTA's full park list and keeps references starting with US- or
CA-. Sources are tried in order until one gives usable data:

  1. https://pota.app/all_parks_ext.csv  (POTA's published park export)
  2. https://api.pota.app/park/all       (the list next.pota.app loads)

Inactive parks are kept, with "active" set to false, so other projects can
choose whether to show them.

The committed file is only replaced when the new data passes checks: both
countries present, every park has coordinates, and neither country shrinks
by more than MAX_SHRINK compared with the file already in the repo. A bad
download leaves the existing file untouched.

Standard library only.
"""

import csv
import io
import json
import os
import sys
import tempfile
import time
import urllib.error
import urllib.request

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT = os.path.join(REPO_ROOT, "data", "us_ca_parks.json")

CSV_URL = os.environ.get("POTA_PARKS_CSV_URL", "https://pota.app/all_parks_ext.csv")
JSON_URL = os.environ.get("POTA_PARKS_JSON_URL", "https://api.pota.app/park/all")
PREFIXES = ("US-", "CA-")
MIN_PER_PREFIX = 1000  # Sanity floor for a first run with no existing file.
MAX_SHRINK = 0.10      # Refuse a run that drops more than 10% of a country.
RETRIES = 3
TIMEOUT_SECONDS = 120
FIELDS = ("reference", "name", "latitude", "longitude", "grid", "locationDesc", "active")


def download(url):
    req = urllib.request.Request(url, headers={"User-Agent": "pota-activations-dashboard"})
    for attempt in range(1, RETRIES + 1):
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
                return resp.read().decode("utf-8-sig")
        except (urllib.error.URLError, OSError) as e:
            print(f"  {url}: attempt {attempt}/{RETRIES} failed: {e}", file=sys.stderr)
            if attempt < RETRIES:
                time.sleep(5 * attempt)
    return None


def first(row, *keys):
    for key in keys:
        if key in row and row[key] not in (None, ""):
            return row[key]
    return None


def to_bool(value):
    if value is None:
        return True  # Sources that only list active parks omit the flag.
    return str(value).strip().lower() in ("1", "true", "yes", "y")


def normalize(row):
    """Return a park dict, or None if the row is not a usable US/CA park."""
    reference = first(row, "reference", "ref")
    if not reference or not str(reference).startswith(PREFIXES):
        return None
    try:
        lat = float(first(row, "latitude", "lat"))
        lon = float(first(row, "longitude", "lon", "lng"))
    except (TypeError, ValueError):
        return None
    return {
        "reference": str(reference),
        "name": first(row, "name"),
        "latitude": lat,
        "longitude": lon,
        "grid": first(row, "grid", "grid6", "grid4"),
        "locationDesc": first(row, "locationDesc", "location"),
        "active": to_bool(first(row, "active")),
    }


def rows_from_csv(text):
    return list(csv.DictReader(io.StringIO(text)))


def rows_from_json(text):
    data = json.loads(text)
    if isinstance(data, dict):
        # Accept {"parks": [...]} or GeoJSON {"features": [...]}.
        if isinstance(data.get("parks"), list):
            data = data["parks"]
        elif isinstance(data.get("features"), list):
            rows = []
            for f in data["features"]:
                props = dict(f.get("properties") or {})
                coords = (f.get("geometry") or {}).get("coordinates") or []
                if len(coords) >= 2:
                    props.setdefault("longitude", coords[0])
                    props.setdefault("latitude", coords[1])
                rows.append(props)
            data = rows
    if not isinstance(data, list):
        raise ValueError("unexpected JSON layout")
    return [r for r in data if isinstance(r, dict)]


def count_by_prefix(parks):
    return {p: sum(1 for x in parks if x["reference"].startswith(p)) for p in PREFIXES}


def load_existing():
    try:
        with open(OUTPUT, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (FileNotFoundError, ValueError):
        return []


def problems_with(parks, existing):
    counts = count_by_prefix(parks)
    old = count_by_prefix([p for p in existing if isinstance(p, dict) and p.get("reference")])
    issues = []
    for prefix in PREFIXES:
        floor = max(MIN_PER_PREFIX, int(old[prefix] * (1 - MAX_SHRINK)))
        if counts[prefix] < floor:
            issues.append(f"{prefix} has {counts[prefix]} parks, expected at least {floor}")
    return counts, issues


def build():
    existing = load_existing()
    sources = ((CSV_URL, rows_from_csv), (JSON_URL, rows_from_json))
    for url, parse in sources:
        print(f"Trying {url}")
        text = download(url)
        if text is None:
            continue
        try:
            rows = parse(text)
        except (ValueError, csv.Error) as e:
            print(f"  could not parse: {e}", file=sys.stderr)
            continue
        parks = {}
        for row in rows:
            park = normalize(row)
            if park:
                parks[park["reference"]] = park
        result = [parks[r] for r in sorted(parks)]
        counts, issues = problems_with(result, existing)
        print(f"  {len(rows)} rows, kept {counts}")
        if issues:
            print("  rejected: " + "; ".join(issues), file=sys.stderr)
            continue
        return result
    return None


def write(parks):
    # One park per line keeps the file compact and the daily git diff readable.
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(OUTPUT), suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write("[\n")
        for i, park in enumerate(parks):
            line = json.dumps({k: park.get(k) for k in FIELDS}, ensure_ascii=False)
            f.write(line + (",\n" if i < len(parks) - 1 else "\n"))
        f.write("]\n")
    os.replace(tmp, OUTPUT)


def main():
    parks = build()
    if parks is None:
        sys.exit("No source gave usable park data; leaving output untouched")
    write(parks)
    print(f"Wrote {len(parks)} parks to {OUTPUT}")


if __name__ == "__main__":
    main()
