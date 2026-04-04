from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

@dataclass
class Song:
    """
    Represents a song and its attributes.
    Required by tests/test_recommender.py
    """
    id: int
    title: str
    artist: str
    genre: str
    mood: str
    energy: float
    tempo_bpm: float
    valence: float
    danceability: float
    acousticness: float

@dataclass
class UserProfile:
    """
    Represents a user's taste preferences.
    Required by tests/test_recommender.py
    """
    favorite_genre: str
    favorite_mood: str
    target_energy: float
    likes_acoustic: bool

class Recommender:
    """
    OOP implementation of the recommendation logic.
    Required by tests/test_recommender.py
    """
    def __init__(self, songs: List[Song]):
        """Store the catalog of songs available for recommendation."""
        self.songs = songs

    def recommend(self, user: UserProfile, k: int = 5) -> List[Song]:
        """Return the top-k songs best matching the user's taste profile."""
        # TODO: Implement recommendation logic
        return self.songs[:k]

    def explain_recommendation(self, user: UserProfile, song: Song) -> str:
        """Return a plain-language explanation of why a song was recommended."""
        # TODO: Implement explanation logic
        return "Explanation placeholder"

def load_songs(csv_path: str) -> List[Dict]:
    """Read songs.csv and return a list of dicts with numeric fields cast to float/int."""
    import csv

    float_fields = {"energy", "valence", "danceability", "acousticness", "tempo_bpm"}
    int_fields = {"id"}

    songs = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            for field in float_fields:
                if field in row:
                    row[field] = float(row[field])
            for field in int_fields:
                if field in row:
                    row[field] = int(row[field])
            songs.append(dict(row))

    print(f"Loaded songs: {len(songs)}")
    return songs

def score_song(user_prefs: Dict, song: Dict) -> Tuple[float, List[str]]:
    """Score one song against user preferences; returns (total_score, list of reasons)."""
    score = 0.0
    reasons = []

    # +3.0 mood match (primary signal — the experience the user wants)
    if song.get("mood") == user_prefs.get("mood"):
        score += 3.0
        reasons.append(f"mood matches '{song['mood']}'")

    # +1.0 genre match (halved from 2.0 — weight shift experiment)
    if song.get("genre") == user_prefs.get("genre"):
        score += 1.0
        reasons.append(f"genre matches '{song['genre']}'")

    # +0.0–4.0 energy proximity (doubled from 2.0 — weight shift experiment)
    target_energy = user_prefs.get("target_energy", user_prefs.get("energy", 0.5))
    energy_proximity = 1.0 - abs(song.get("energy", 0.5) - target_energy)
    score += energy_proximity * 4.0
    reasons.append(f"energy fit: {energy_proximity:.2f}")

    # +0.0–1.5 acousticness fit
    acousticness = song.get("acousticness", 0.5)
    if user_prefs.get("likes_acoustic", False):
        acousticness_score = acousticness
    else:
        acousticness_score = 1.0 - acousticness
    score += acousticness_score * 1.5
    reasons.append(f"acousticness fit: {acousticness_score:.2f}")

    # +0.0–1.0 valence fit (confirms emotional tone numerically)
    valence = song.get("valence", 0.5)
    positive_moods = {"happy", "energetic", "romantic", "confident"}
    if user_prefs.get("mood") in positive_moods:
        valence_score = valence
    else:
        valence_score = 1.0 - valence
    score += valence_score * 1.0
    reasons.append(f"valence fit: {valence_score:.2f}")

    return score, reasons

def recommend_songs(user_prefs: Dict, songs: List[Dict], k: int = 5) -> List[Tuple[Dict, float, str]]:
    """Score all songs, sort by score descending, and return the top-k results."""
    scored = []
    for song in songs:
        score, reasons = score_song(user_prefs, song)
        scored.append((song, score, "; ".join(reasons)))

    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:k]
