"""
Fetch a 1-2 sentence Wikipedia summary for each unique artist in the catalog.

Output: data/artist_metadata.json (mapping artist name -> summary string).
Missing or ambiguous artists get an empty string and are logged.

Run:
    python -m scripts.fetch_artist_metadata
"""
from __future__ import annotations

import csv
import json
import sys
import time
from pathlib import Path
from urllib.parse import quote

import requests

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SONGS_CSV = PROJECT_ROOT / "data" / "songs.csv"
OUT_PATH = PROJECT_ROOT / "data" / "artist_metadata.json"
WIKI_API = "https://en.wikipedia.org/api/rest_v1/page/summary/{name}"
USER_AGENT = "MoodMatch-classroom-project/2.0 (educational)"
DELAY_SECONDS = 1.0  # be polite to Wikipedia; bursts get silently throttled


def fetch_summary(artist: str) -> str:
    """Return the first 1-2 sentences of an artist's Wikipedia summary, or ''."""
    url = WIKI_API.format(name=quote(artist, safe=""))
    try:
        r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=10)
    except requests.RequestException as e:
        print(f"  ! network error for '{artist}': {e}", file=sys.stderr)
        return ""

    if r.status_code == 429:
        print(f"  ! rate-limited on '{artist}', backing off 30s", file=sys.stderr)
        time.sleep(30)
        return fetch_summary(artist)
    if r.status_code != 200:
        return ""

    data = r.json()
    # Skip disambiguation pages — we'd be guessing which person they mean.
    if data.get("type") == "disambiguation":
        return ""
    extract = (data.get("extract") or "").strip()
    if not extract:
        return ""
    # Keep the first ~280 chars (roughly 1-2 sentences) to keep blurbs compact.
    return extract[:280].rsplit(".", 1)[0] + "." if "." in extract[:280] else extract[:280]


def unique_artists(csv_path: Path) -> list[str]:
    with open(csv_path, encoding="utf-8") as f:
        return sorted({row["artist"] for row in csv.DictReader(f)})


def main() -> None:
    artists = unique_artists(SONGS_CSV)
    print(f"Fetching Wikipedia summaries for {len(artists)} artists...", file=sys.stderr)

    metadata: dict[str, str] = {}
    found = 0
    for i, artist in enumerate(artists, start=1):
        summary = fetch_summary(artist)
        metadata[artist] = summary
        marker = "✓" if summary else "—"
        print(f"  [{i:>2}/{len(artists)}] {marker} {artist}", file=sys.stderr)
        if summary:
            found += 1
        time.sleep(DELAY_SECONDS)

    OUT_PATH.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
    print(file=sys.stderr)
    print(f"Wrote {OUT_PATH.relative_to(PROJECT_ROOT)} ({found}/{len(artists)} artists matched).", file=sys.stderr)


if __name__ == "__main__":
    main()
