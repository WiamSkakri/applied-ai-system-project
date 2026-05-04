"""
Evaluation harness for the RAG retrieval pipeline.

Runs a battery of free-text queries with property-based expectations
(genre / mood band, energy / acousticness average, low similarity for
gibberish, plus artist-context queries that benefit from the Wikipedia-
augmented blurbs). The script runs the suite twice — once with the
original audio-feature blurbs, once with Wikipedia-enhanced blurbs — and
prints both pass rates side by side so the impact of the RAG enhancement
is measurable.

Run from the project root:
    python -m scripts.evaluate

Exit code: 0 if the enhanced run hits the same or higher pass rate as the
original run, 1 otherwise.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import Callable

from src.recommender import load_songs
from src.retrieval import (
    SONGS_CSV,
    load_artist_metadata,
    load_or_build_enhanced_index,
    load_or_build_index,
    retrieve,
)

CheckResult = tuple[bool, str]
CheckFn = Callable[[list[tuple[dict, float]], float], CheckResult]


@dataclass
class EvalCase:
    query: str
    expect: str
    check: CheckFn
    section: str = "core"  # "core" or "artist-context"


def majority_field(field: str, values: set[str], top: int, min_count: int = 2) -> CheckFn:
    def _check(results, _top_score) -> CheckResult:
        sample = [r for r, _ in results[:top]]
        n = sum(1 for r in sample if r[field] in values)
        return n >= min_count, f"{n}/{top} top results have {field} in {sorted(values)}"
    return _check


def avg_field(field: str, op: str, threshold: float, top: int) -> CheckFn:
    def _check(results, _top_score) -> CheckResult:
        sample = [r for r, _ in results[:top]]
        avg = sum(r[field] for r in sample) / len(sample)
        passed = avg > threshold if op == ">" else avg < threshold
        return passed, f"avg {field} over top-{top} = {avg:.2f} (expected {op} {threshold})"
    return _check


def rejected_below(min_sim: float) -> CheckFn:
    def _check(_results, top_score) -> CheckResult:
        return top_score < min_sim, f"top similarity = {top_score:.3f} (expected < {min_sim})"
    return _check


def contains_artist(artists: set[str], top: int) -> CheckFn:
    """Pass if any of the top-K results is by one of the named artists."""
    def _check(results, _top_score) -> CheckResult:
        sample = [r["artist"] for r, _ in results[:top]]
        match = any(a in artists for a in sample)
        return match, f"top-{top} artists: {sample}"
    return _check


CASES: list[EvalCase] = [
    # --- Core retrieval tests (audio-feature blurbs are sufficient) ---
    EvalCase(
        query="songs for a rainy sunday morning",
        expect="majority of top-3 have mellow mood",
        check=majority_field("mood", {"chill", "melancholic", "sad", "relaxed"}, top=3),
    ),
    EvalCase(
        query="angry workout music to push through the last set",
        expect="majority of top-3 have intense or energetic mood",
        check=majority_field("mood", {"intense", "energetic"}, top=3),
    ),
    EvalCase(
        query="quiet acoustic music for studying",
        expect="top-3 average acousticness > 0.5",
        check=avg_field("acousticness", ">", 0.5, top=3),
    ),
    EvalCase(
        query="high energy dance party music",
        expect="top-3 average energy > 0.65",
        check=avg_field("energy", ">", 0.65, top=3),
    ),
    EvalCase(
        query="romantic and slow songs for a date night",
        expect="top-3 average energy < 0.55",
        check=avg_field("energy", "<", 0.55, top=3),
    ),
    EvalCase(
        query="heavy metal for headbanging",
        expect="majority of top-5 in heavy genres",
        check=majority_field("genre", {"metal", "rock", "punk"}, top=5),
    ),
    EvalCase(
        query="upbeat happy summer vibes",
        expect="majority of top-3 have happy mood",
        check=majority_field("mood", {"happy"}, top=3),
    ),
    EvalCase(
        query="electronic dance music with heavy synths",
        expect="majority of top-5 in electronic genres",
        check=majority_field("genre", {"edm", "house", "techno"}, top=5),
    ),
    EvalCase(
        query="sad jazz at 2am",
        expect="majority of top-5 have downbeat mood",
        check=majority_field("mood", {"sad", "melancholic", "moody"}, top=5),
    ),
    EvalCase(
        query="hfsgsgflsgfhsdf",
        expect="top similarity below the 0.25 rejection threshold",
        check=rejected_below(0.25),
    ),
    # --- Artist-context tests (require Wikipedia metadata to pass cleanly) ---
    EvalCase(
        query="Australian rock band",
        expect="AC/DC in top-5",
        check=contains_artist({"AC/DC"}, top=5),
        section="artist-context",
    ),
    EvalCase(
        query="legendary American rapper from the west coast",
        expect="2Pac in top-5",
        check=contains_artist({"2Pac"}, top=5),
        section="artist-context",
    ),
    EvalCase(
        query="British female soul singer",
        expect="Adele or Amy Winehouse in top-5",
        check=contains_artist({"Adele", "Amy Winehouse"}, top=5),
        section="artist-context",
    ),
    EvalCase(
        query="Indian music composer film score",
        expect="A.R. Rahman or Anirudh Ravichander in top-5",
        check=contains_artist({"A.R. Rahman", "Anirudh Ravichander"}, top=5),
        section="artist-context",
    ),
    EvalCase(
        query="Japanese rock band",
        expect="175R or SiM in top-5",
        check=contains_artist({"175R", "SiM"}, top=5),
        section="artist-context",
    ),
]


def run_cases(label: str, cases: list[EvalCase], songs, embeddings) -> tuple[int, list[bool]]:
    """Run all cases against a given embeddings array. Returns (passed_count, per_case_passed)."""
    print()
    print("=" * 78)
    print(f" {label}")
    print("=" * 78)

    per_case = []
    for i, case in enumerate(cases, start=1):
        results = retrieve(case.query, songs, embeddings, k=10)
        top_score = results[0][1] if results else 0.0
        ok, detail = case.check(results, top_score)
        per_case.append(ok)

        top_song = results[0][0] if results else None
        top_line = (
            f"{top_song['title']} — {top_song['artist']}"
            if top_song else "(no results)"
        )
        section_tag = f"[{case.section}]" if case.section != "core" else ""
        print()
        print(f"[{'PASS' if ok else 'FAIL'}] #{i:>2} {section_tag} \"{case.query}\"")
        print(f"        expect:  {case.expect}")
        print(f"        actual:  {detail}")
        print(f"        top hit: {top_line} (sim {top_score:.3f})")

    passed = sum(per_case)
    print()
    print(f"  Subtotal: {passed}/{len(cases)} passed")
    return passed, per_case


def main() -> int:
    songs = load_songs(str(SONGS_CSV))
    embeddings_orig = load_or_build_index(songs)

    artist_metadata = load_artist_metadata()
    if not artist_metadata:
        print("ERROR: data/artist_metadata.json missing — run scripts.fetch_artist_metadata first.", file=sys.stderr)
        return 1
    embeddings_enhanced = load_or_build_enhanced_index(songs, artist_metadata)

    pass_orig, per_orig = run_cases("ORIGINAL blurbs (audio features only)", CASES, songs, embeddings_orig)
    pass_enh, per_enh = run_cases("ENHANCED blurbs (audio features + Wikipedia artist context)", CASES, songs, embeddings_enhanced)

    # Side-by-side comparison
    print()
    print("=" * 78)
    print(" Side-by-side comparison")
    print("=" * 78)
    print(f"{'#':>3}  {'orig':<5} {'enh':<5}  {'section':<14} query")
    print("-" * 78)
    for i, case in enumerate(CASES, start=1):
        a = "PASS" if per_orig[i - 1] else "FAIL"
        b = "PASS" if per_enh[i - 1] else "FAIL"
        marker = " " if per_orig[i - 1] == per_enh[i - 1] else ("↑" if per_enh[i - 1] else "↓")
        print(f"{i:>3}  {a:<5} {b:<5}{marker} {case.section:<14} \"{case.query}\"")

    delta = pass_enh - pass_orig
    sign = "+" if delta >= 0 else ""
    print()
    print("=" * 78)
    print(f" Original: {pass_orig}/{len(CASES)} ({pass_orig/len(CASES)*100:.0f}%)")
    print(f" Enhanced: {pass_enh}/{len(CASES)} ({pass_enh/len(CASES)*100:.0f}%)  delta {sign}{delta}")
    print("=" * 78)
    print()

    return 0 if pass_enh >= pass_orig else 1


if __name__ == "__main__":
    sys.exit(main())
