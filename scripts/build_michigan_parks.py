#!/usr/bin/env python3
"""Build data/Michigan_POTA_Parks.json from data/us_ca_parks.json.

Keeps every active park whose locationDesc includes US-MI, so parks shared
with other states (like the North Country Trail) are included. The output
has the same fields and order the dashboard has always read.

The file is only replaced when the new list has at least MIN_PARKS parks
and is no more than MAX_SHRINK smaller than the committed one.

With --check, nothing is written: the script compares what it would build
with the committed file, prints the differences, and exits 1 if they differ.
The monthly check workflow uses this after downloading fresh park data.

Standard library only.
"""

import json
import os
import sys
import tempfile

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE = os.path.join(REPO_ROOT, "data", "us_ca_parks.json")
OUTPUT = os.path.join(REPO_ROOT, "data", "Michigan_POTA_Parks.json")

STATE = "US-MI"
MIN_PARKS = 300     # Michigan had 388 active parks in October 2026.
MAX_SHRINK = 0.10
FIELDS = ("reference", "name", "latitude", "longitude", "locationDesc")


def load_list(path):
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, ValueError) as e:
        sys.exit(f"Cannot read {path}: {e}")
    if not isinstance(data, list):
        sys.exit(f"{path} is not a list")
    return data


def build():
    parks = []
    for p in load_list(SOURCE):
        if not isinstance(p, dict) or not p.get("active"):
            continue
        states = [s.strip() for s in (p.get("locationDesc") or "").split(",")]
        if STATE in states:
            parks.append({k: p.get(k) for k in FIELDS})
    return sorted(parks, key=lambda p: p["reference"])


def describe_changes(old, new):
    old_by_ref = {p.get("reference"): p for p in old if isinstance(p, dict)}
    new_by_ref = {p["reference"]: p for p in new}
    lines = []
    for ref in sorted(new_by_ref.keys() - old_by_ref.keys()):
        lines.append(f"  added   {ref} {new_by_ref[ref]['name']}")
    for ref in sorted(old_by_ref.keys() - new_by_ref.keys()):
        lines.append(f"  removed {ref} {old_by_ref[ref].get('name')}")
    for ref in sorted(old_by_ref.keys() & new_by_ref.keys()):
        if old_by_ref[ref] != new_by_ref[ref]:
            lines.append(f"  changed {ref} {new_by_ref[ref]['name']}")
    return lines


def main():
    check_only = "--check" in sys.argv[1:]
    parks = build()
    existing = load_list(OUTPUT) if os.path.exists(OUTPUT) else []
    changes = describe_changes(existing, parks)

    if check_only:
        if changes:
            print(f"{OUTPUT} is out of date ({len(existing)} parks, should be {len(parks)}):")
            print("\n".join(changes))
            sys.exit(1)
        print(f"{OUTPUT} is up to date ({len(parks)} parks)")
        return

    floor = max(MIN_PARKS, int(len(existing) * (1 - MAX_SHRINK)))
    if len(parks) < floor:
        sys.exit(f"Refusing to write {len(parks)} parks; expected at least {floor}")
    if not changes:
        print(f"No changes ({len(parks)} parks)")
        return

    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(OUTPUT), suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(parks, f, indent=4, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp, OUTPUT)
    print(f"Wrote {len(parks)} parks to {OUTPUT}:")
    print("\n".join(changes))


if __name__ == "__main__":
    main()
