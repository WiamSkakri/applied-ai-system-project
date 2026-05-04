"""
Build data/songs.csv from the public Hugging Face mirror of the Spotify Tracks Dataset.

Usage:
    python -m scripts.build_catalog

Source: https://huggingface.co/datasets/maharshipandya/spotify-tracks-dataset
"""
import csv
import random
from pathlib import Path

from datasets import load_dataset

# Curated genre list (mapped to dataset's track_genre values).
# Five songs per genre = 100 total.
TARGET_GENRES = [
    "pop", "rock", "jazz", "classical", "hip-hop",
    "r-n-b", "edm", "country", "folk", "metal",
    "indie", "blues", "soul", "funk", "reggae",
    "punk", "ambient", "house", "techno", "acoustic",
]
PER_GENRE = 5
SEED = 42
MIN_POPULARITY = 20  # filters out the most obscure/unlabeled tracks


def derive_mood(valence: float, energy: float) -> str:
    """
    Map Spotify's continuous valence/energy axes to a discrete mood label.
    Documented in model_card.md. Not perfect — moods like 'nostalgic' or
    'romantic' need lyrical context that audio features can't capture.
    """
    if valence >= 0.6 and energy >= 0.6:
        return "happy"
    if valence >= 0.6 and energy < 0.4:
        return "chill"
    if valence >= 0.6:
        return "relaxed"
    if valence < 0.4 and energy >= 0.7:
        return "intense"
    if valence < 0.4 and energy < 0.4:
        return "melancholic"
    if valence < 0.4:
        return "sad"
    if energy >= 0.7:
        return "energetic"
    if energy < 0.4:
        return "focused"
    return "moody"


def main() -> None:
    print("Loading Spotify Tracks Dataset from Hugging Face...")
    ds = load_dataset("maharshipandya/spotify-tracks-dataset", split="train")
    print(f"  {len(ds):,} rows loaded")

    rng = random.Random(SEED)
    rows = []
    seen = set()  # de-dup on (title, artist)
    next_id = 1

    for genre in TARGET_GENRES:
        candidates = ds.filter(
            lambda r: r["track_genre"] == genre and r["popularity"] >= MIN_POPULARITY,
            desc=None,
        )
        if len(candidates) == 0:
            print(f"  ! genre '{genre}' had no matches, skipping")
            continue

        indices = list(range(len(candidates)))
        rng.shuffle(indices)

        picked = 0
        for idx in indices:
            if picked >= PER_GENRE:
                break
            song = candidates[idx]
            artist = (song["artists"] or "Unknown").split(";")[0].strip()
            title = (song["track_name"] or "").strip()
            if not title:
                continue
            key = (title.lower(), artist.lower())
            if key in seen:
                continue
            seen.add(key)

            rows.append({
                "id": next_id,
                "title": title,
                "artist": artist,
                "genre": genre,
                "mood": derive_mood(song["valence"], song["energy"]),
                "energy": round(song["energy"], 2),
                "tempo_bpm": int(round(song["tempo"])),
                "valence": round(song["valence"], 2),
                "danceability": round(song["danceability"], 2),
                "acousticness": round(song["acousticness"], 2),
            })
            next_id += 1
            picked += 1
        print(f"  + {genre}: {picked} songs")

    out_path = Path(__file__).resolve().parent.parent / "data" / "songs.csv"
    fieldnames = [
        "id", "title", "artist", "genre", "mood",
        "energy", "tempo_bpm", "valence", "danceability", "acousticness",
    ]
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nWrote {len(rows)} songs to {out_path}")


if __name__ == "__main__":
    main()
