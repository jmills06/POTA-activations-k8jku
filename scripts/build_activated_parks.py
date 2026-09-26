#!/usr/bin/env python3
"""Build data/activated_parks.json: coordinates for every activated park.

Reads the unique references from data/pota_activations.json and looks up
each one that is not already in data/activated_parks.json via
https://api.pota.app/park/<reference>. Existing entries are kept, so only
new parks are fetched. A failed lookup is skipped (and retried on the next
run); the output is only replaced when the new list is valid and at least
as large as the old one.

Standard library only.
"""

import json
import os
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ACTIVATIONS = os.path.join(REPO_ROOT, "data", "pota_activations.json")
OUTPUT = os.path.join(REPO_ROOT, "data", "activated_parks.json")

API_URL = os.environ.get("POTA_API_URL", "https://api.pota.app/park/")
PAUSE_SECONDS = 0.5
RETRIES = 3
TIMEOUT_SECONDS = 20
FIELDS = ("reference", "name", "latitude", "longitude", "locationDesc", "parktypeDesc")


def load_json(path, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return default


def fetch_park(reference):
    """Return a park record, or None if every attempt failed."""
    url = API_URL + urllib.parse.quote(reference)
    req = urllib.request.Request(url, headers={"User-Agent": "pota-activations-dashboard"})
    for attempt in range(1, RETRIES + 1):
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
                data = json.load(resp)
            lat = float(data["latitude"])
            lon = float(data["longitude"])
            return {
                "reference": reference,
                "name": data.get("name"),
                "latitude": lat,
                "longitude": lon,
                "locationDesc": data.get("locationDesc"),
                "parktypeDesc": data.get("parktypeDesc"),
            }
        except (urllib.error.URLError, OSError, ValueError, KeyError, TypeError) as e:
            print(f"  {reference}: attempt {attempt}/{RETRIES} failed: {e}", file=sys.stderr)
            if attempt < RETRIES:
                time.sleep(PAUSE_SECONDS * 2 ** attempt)
    return None


def main():
    activations = load_json(ACTIVATIONS)
    if not isinstance(activations, list):
        sys.exit(f"{ACTIVATIONS} is missing or not a list; leaving output untouched")

    existing = load_json(OUTPUT, default=[])
    if not isinstance(existing, list):
        sys.exit(f"{OUTPUT} is not a list; refusing to overwrite it")
    parks = {p["reference"]: p for p in existing if isinstance(p, dict) and p.get("reference")}

    references = sorted({a["reference"] for a in activations if isinstance(a, dict) and a.get("reference")})
    missing = [r for r in references if r not in parks]
    print(f"{len(references)} activated parks, {len(parks)} already known, {len(missing)} to look up")

    failed = []
    for i, reference in enumerate(missing):
        if i:
            time.sleep(PAUSE_SECONDS)
        park = fetch_park(reference)
        if park:
            parks[reference] = park
            print(f"  {reference}: {park['name']}")
        else:
            failed.append(reference)

    result = [{k: parks[r].get(k) for k in FIELDS} for r in sorted(parks)]
    if not result:
        print("No park data to write; leaving output untouched", file=sys.stderr)
        return
    if len(result) < len(existing):
        sys.exit(f"Refusing to write {len(result)} parks over {len(existing)} existing entries")

    # Write to a temp file in the same directory, then atomically replace.
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(OUTPUT), suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=4)
        f.write("\n")
    os.replace(tmp, OUTPUT)

    print(f"Wrote {len(result)} parks to {OUTPUT}")
    if failed:
        print(f"{len(failed)} lookups failed (will retry next run): {', '.join(failed)}", file=sys.stderr)


if __name__ == "__main__":
    main()
