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
        self.songs = songs

    def recommend(self, user: UserProfile, k: int = 5) -> List[Song]:
        # TODO: Implement recommendation logic
        return self.songs[:k]

    def explain_recommendation(self, user: UserProfile, song: Song) -> str:
        # TODO: Implement explanation logic
        return "Explanation placeholder"

def load_songs(csv_path: str) -> List[Dict]:
    """
    Loads songs from a CSV file.
    Required by src/main.py
    """
    # TODO: Implement CSV loading logic
    print(f"Loading songs from {csv_path}...")
    return []

def score_song(user_prefs: Dict, song: Dict) -> Tuple[float, List[str]]:
    """
    Scores a single song against user preferences.
    Required by recommend_songs() and src/main.py
    """
    score = 0.0
    reasons = []

    # +3.0 mood match (primary signal — the experience the user wants)
    if song.get("mood") == user_prefs.get("mood"):
        score += 3.0
        reasons.append(f"mood matches '{song['mood']}'")

    # +2.0 genre match (secondary signal — stylistic preference)
    if song.get("genre") == user_prefs.get("genre"):
        score += 2.0
        reasons.append(f"genre matches '{song['genre']}'")

    # +0.0–2.0 energy proximity (closer to target = higher score)
    target_energy = user_prefs.get("target_energy", user_prefs.get("energy", 0.5))
    energy_proximity = 1.0 - abs(song.get("energy", 0.5) - target_energy)
    score += energy_proximity * 2.0
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
    """
    Functional implementation of the recommendation logic.
    Required by src/main.py
    """
    scored = []
    for song in songs:
        score, reasons = score_song(user_prefs, song)
        scored.append((song, score, "; ".join(reasons)))

    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:k]
