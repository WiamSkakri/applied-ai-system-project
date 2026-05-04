"""
Semantic retrieval over the song catalog.

Pipeline:
  song row  -->  text blurb  -->  embedding (sentence-transformers)
  user query -->  embedding  -->  cosine similarity vs. song embeddings
                              -->  top-k songs

The embedder model is `all-MiniLM-L6-v2` (~80MB, 384-dim). Embeddings are
cached on disk so subsequent runs are instant.

CLI smoke test:
    python -m src.retrieval "songs for a rainy sunday morning"
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Iterable

import numpy as np
from sentence_transformers import SentenceTransformer

from src.recommender import load_songs

MODEL_NAME = "all-MiniLM-L6-v2"
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SONGS_CSV = PROJECT_ROOT / "data" / "songs.csv"
EMBEDDINGS_PATH = PROJECT_ROOT / "data" / "embeddings.npy"
BLURBS_PATH = PROJECT_ROOT / "data" / "blurbs.txt"
ARTIST_METADATA_PATH = PROJECT_ROOT / "data" / "artist_metadata.json"
EMBEDDINGS_ENHANCED_PATH = PROJECT_ROOT / "data" / "embeddings_enhanced.npy"
BLURBS_ENHANCED_PATH = PROJECT_ROOT / "data" / "blurbs_enhanced.txt"


def _band(value: float, low: str, mid: str, high: str, *, lo_thresh=0.4, hi_thresh=0.7) -> str:
    if value < lo_thresh:
        return low
    if value >= hi_thresh:
        return high
    return mid


def make_blurb(song: dict) -> str:
    """Convert a song row into a natural-language description for embedding."""
    energy_word = _band(song["energy"], "calm", "moderately energetic", "very energetic")
    valence_word = _band(song["valence"], "downbeat and somber", "neutral", "upbeat and positive")
    dance_word = _band(song["danceability"], "not very danceable", "moderately danceable", "highly danceable")
    acoustic_word = _band(song["acousticness"], "electric/produced", "mixed acoustic and electric", "mostly acoustic")
    tempo_word = _band(song["tempo_bpm"], "slow", "mid-tempo", "fast", lo_thresh=85, hi_thresh=130)

    return (
        f"{song['title']} by {song['artist']} — "
        f"a {song['mood']} {song['genre']} song. "
        f"It is {energy_word} (energy {song['energy']:.2f}), "
        f"{valence_word} (valence {song['valence']:.2f}), "
        f"{tempo_word} at {song['tempo_bpm']} BPM, "
        f"{acoustic_word}, {dance_word}."
    )


def make_enhanced_blurb(song: dict, artist_summary: str) -> str:
    """Blurb augmented with a Wikipedia artist summary. Falls back to plain blurb if no summary."""
    base = make_blurb(song)
    if not artist_summary:
        return base
    return base + f" About the artist: {artist_summary}"


_model_cache: SentenceTransformer | None = None


def get_model() -> SentenceTransformer:
    global _model_cache
    if _model_cache is None:
        print(f"Loading embedding model '{MODEL_NAME}'...", file=sys.stderr)
        _model_cache = SentenceTransformer(MODEL_NAME)
    return _model_cache


def embed_texts(texts: Iterable[str]) -> np.ndarray:
    """Return L2-normalized embeddings so cosine similarity = dot product."""
    model = get_model()
    vectors = model.encode(list(texts), convert_to_numpy=True, show_progress_bar=False)
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return vectors / norms


def build_index(songs: list[dict]) -> np.ndarray:
    """Embed all songs and write the cache + a parallel blurbs file for inspection."""
    blurbs = [make_blurb(s) for s in songs]
    embeddings = embed_texts(blurbs)

    np.save(EMBEDDINGS_PATH, embeddings)
    BLURBS_PATH.write_text("\n".join(blurbs), encoding="utf-8")
    print(f"Built index: {len(songs)} songs -> {EMBEDDINGS_PATH.name}", file=sys.stderr)
    return embeddings


def load_or_build_index(songs: list[dict]) -> np.ndarray:
    if EMBEDDINGS_PATH.exists():
        cached = np.load(EMBEDDINGS_PATH)
        if len(cached) == len(songs):
            return cached
        print("Cache size mismatch, rebuilding index...", file=sys.stderr)
    return build_index(songs)


def build_enhanced_index(songs: list[dict], artist_metadata: dict[str, str]) -> np.ndarray:
    """Build an index where each blurb is augmented with the artist's Wikipedia summary."""
    blurbs = [make_enhanced_blurb(s, artist_metadata.get(s["artist"], "")) for s in songs]
    embeddings = embed_texts(blurbs)
    np.save(EMBEDDINGS_ENHANCED_PATH, embeddings)
    BLURBS_ENHANCED_PATH.write_text("\n".join(blurbs), encoding="utf-8")
    augmented = sum(1 for s in songs if artist_metadata.get(s["artist"]))
    print(
        f"Built enhanced index: {len(songs)} songs ({augmented} with artist context) "
        f"-> {EMBEDDINGS_ENHANCED_PATH.name}",
        file=sys.stderr,
    )
    return embeddings


def load_or_build_enhanced_index(songs: list[dict], artist_metadata: dict[str, str]) -> np.ndarray:
    if EMBEDDINGS_ENHANCED_PATH.exists():
        cached = np.load(EMBEDDINGS_ENHANCED_PATH)
        if len(cached) == len(songs):
            return cached
        print("Enhanced cache size mismatch, rebuilding index...", file=sys.stderr)
    return build_enhanced_index(songs, artist_metadata)


def load_artist_metadata() -> dict[str, str]:
    """Load Wikipedia artist summaries (built by scripts/fetch_artist_metadata.py)."""
    if not ARTIST_METADATA_PATH.exists():
        return {}
    import json
    return json.loads(ARTIST_METADATA_PATH.read_text(encoding="utf-8"))


def retrieve(
    query: str,
    songs: list[dict],
    embeddings: np.ndarray,
    k: int = 10,
) -> list[tuple[dict, float]]:
    """Return top-k (song, similarity) pairs for the free-text query."""
    query_vec = embed_texts([query])[0]
    similarities = embeddings @ query_vec  # both are L2-normalized, so this is cosine sim
    top_idx = np.argsort(-similarities)[:k]
    return [(songs[i], float(similarities[i])) for i in top_idx]


def main() -> None:
    if len(sys.argv) < 2:
        print('Usage: python -m src.retrieval "your free-text query"', file=sys.stderr)
        sys.exit(1)
    query = " ".join(sys.argv[1:])

    songs = load_songs(str(SONGS_CSV))
    embeddings = load_or_build_index(songs)
    results = retrieve(query, songs, embeddings, k=10)

    print(f'\nQuery: "{query}"\n')
    print(f"{'#':>2}  {'sim':>5}  {'mood':<12} {'genre':<10} title — artist")
    print("-" * 80)
    for i, (song, score) in enumerate(results, start=1):
        title = song["title"][:40]
        artist = song["artist"][:25]
        print(
            f"{i:>2}  {score:>5.3f}  "
            f"{song['mood']:<12} {song['genre']:<10} "
            f"{title} — {artist}"
        )


if __name__ == "__main__":
    main()
