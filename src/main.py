"""
Command line runner for the Music Recommender Simulation.

Usage:
  python3 src/main.py            # runs all 6 stress-test profiles
  python3 src/main.py default    # runs only the default pop/happy profile
  python3 src/main.py stress     # runs all 6 stress-test profiles
"""

import sys
from recommender import load_songs, recommend_songs


PROFILES = [
    {
        "label": "High-Energy Pop",
        "genre": "pop",
        "mood": "happy",
        "target_energy": 0.85,
        "likes_acoustic": False,
    },
    {
        "label": "Chill Lofi",
        "genre": "lofi",
        "mood": "chill",
        "target_energy": 0.35,
        "likes_acoustic": True,
    },
    {
        "label": "Deep Intense Rock",
        "genre": "rock",
        "mood": "intense",
        "target_energy": 0.92,
        "likes_acoustic": False,
    },
    # --- Adversarial / edge case profiles ---
    {
        "label": "Conflicting: Sad + High Energy",
        "genre": "r&b",
        "mood": "sad",
        "target_energy": 0.9,   # high energy but sad mood — pulls in opposite directions
        "likes_acoustic": False,
    },
    {
        "label": "Ghost Genre (no catalog match)",
        "genre": "bossa nova",  # not in catalog at all — genre bonus never fires
        "mood": "relaxed",
        "target_energy": 0.4,
        "likes_acoustic": True,
    },
    {
        "label": "Extreme Acoustic Seeker",
        "genre": "classical",
        "mood": "melancholic",
        "target_energy": 0.2,
        "likes_acoustic": True,
    },
]


def print_recommendations(label: str, recommendations: list) -> None:
    print("\n" + "=" * 55)
    print(f"  🎵 {label}")
    print("=" * 55)
    for i, (song, score, explanation) in enumerate(recommendations, start=1):
        print(f"\n#{i}  {song['title']} by {song['artist']}")
        print(f"    Genre: {song['genre']}  |  Mood: {song['mood']}  |  Score: {score:.2f} / 10.5")
        for reason in explanation.split("; "):
            print(f"    ✓ {reason}")
    print()


DEFAULT_PROFILE = {
    "label": "Default: High-Energy Pop",
    "genre": "pop",
    "mood": "happy",
    "target_energy": 0.8,
    "likes_acoustic": False,
}


def main() -> None:
    songs = load_songs("data/songs.csv")

    mode = sys.argv[1] if len(sys.argv) > 1 else "stress"

    if mode == "default":
        profile = DEFAULT_PROFILE.copy()
        label = profile.pop("label")
        recommendations = recommend_songs(profile, songs, k=5)
        print_recommendations(label, recommendations)
    else:
        for profile in PROFILES:
            label = profile.pop("label")
            recommendations = recommend_songs(profile, songs, k=5)
            print_recommendations(label, recommendations)
            profile["label"] = label  # restore for reuse


if __name__ == "__main__":
    main()
