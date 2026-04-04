# 🎧 Model Card: Music Recommender Simulation

## 1. Model Name

**MoodMatch 1.0**

---

## 2. Intended Use

MoodMatch is designed to suggest songs from a small catalog that fit a listener's current mood, preferred genre, and energy level. It assumes the user can describe what they want in simple terms — like "I want chill lofi music with low energy" — and returns a ranked list of the five best matches. This is a classroom simulation, not a production system. It is not designed for real streaming platforms, real user data, or catalogs larger than a few dozen songs.

---

## 3. How the Model Works

The recommender scores every song in the catalog against what the user told it they want, then returns the top five scores. Each song gets points in five categories:

- **Mood match** — if the song's mood matches the user's requested mood, it gets the biggest bonus (3 points). This is treated as the most important signal.
- **Genre match** — if the song's genre matches, it gets a smaller bonus (1 point in the current weight-shift version, originally 2).
- **Energy fit** — the closer the song's energy level is to the user's target, the more points it earns (up to 4 points). A song exactly on target gets the full amount; one far away gets close to zero.
- **Acousticness fit** — acoustic songs are rewarded for users who like acoustic music; electric songs are rewarded for those who don't (up to 1.5 points).
- **Valence fit** — valence measures how "positive" a song sounds. Happy or romantic moods get rewarded for high-valence songs; sad or melancholic moods get rewarded for low-valence ones (up to 1 point).

The weights were modified from the original as part of an experiment: energy was doubled and genre was halved to test how sensitive the rankings are to weight changes.

---

## 4. Data

The catalog contains 18 songs stored in a CSV file. Each song has 10 attributes: a unique ID, title, artist name, genre, mood, energy (0–1), tempo in BPM, valence (0–1), danceability (0–1), and acousticness (0–1). The 18 songs span 15 different genres including pop, lofi, rock, r&b, jazz, classical, metal, folk, edm, hip-hop, country, k-pop, indie pop, synthwave, and ambient. Most genres have only one song. Moods covered include happy, chill, intense, sad, relaxed, focused, nostalgic, romantic, moody, energetic, melancholic, angry, and confident. Notably, two features in the dataset — tempo and danceability — are never used by the scoring algorithm, which is a gap between the data available and the data actually used.

---

## 5. Strengths

The system works best when a user's preferences are internally consistent — for example, someone who wants chill lofi music at low energy. In those cases, all five scoring signals point in the same direction and the top result is clearly the right pick. The scoring is also fully transparent: every recommendation comes with a plain-language explanation of exactly which signals contributed and by how much. This makes it easy to audit why a song was recommended. The system also handles edge cases gracefully — when a genre isn't in the catalog at all, it doesn't crash; it just scores on the remaining signals and returns something reasonable.

---

## 6. Limitations and Bias

The system has a strong mood-matching bias: mood carries 3.0 out of a maximum 10.5 points (roughly 29%), which means it consistently overrides other preferences. For example, a user who wants high-energy sad music will always receive a slow, low-energy sad song at the top of their list — the energy mismatch is simply too small a penalty to overcome the mood bonus. The catalog is also highly genre-sparse, with 18 songs spread across 15 different genres, so most users receive genre bonus points at most once or twice in their top 5, effectively turning the system into a mood-and-energy ranker for anyone outside of lofi or pop. Two audio features present in the dataset — tempo (BPM) and danceability — are loaded but completely ignored during scoring, meaning a user who specifically wants fast-tempo dance music cannot be distinguished from one who wants slow acoustic music if their mood and energy targets are similar. Finally, the valence scoring logic incorrectly treats moods like "intense" and "focused" as negative-valence moods, so the system rewards those users with sad-sounding songs even though intensity and focus are emotionally neutral-to-positive experiences.

---

## 7. Evaluation

Six user profiles were tested across two runs: a baseline run using the original weights (genre: 2.0, energy: 2.0), and a weight-shift experiment that doubled energy importance to 4.0 and halved genre importance to 1.0. The six profiles were: High-Energy Pop (pop/happy), Chill Lofi (lofi/chill), Deep Intense Rock (rock/intense), Conflicting Sad+High Energy (r&b/sad with high energy target), Ghost Genre (bossa nova — not in the catalog), and Extreme Acoustic Seeker (classical/melancholic). For each profile, the top 5 ranked songs were reviewed to see whether the results matched the stated preference intuitively, and whether the same songs appeared across profiles in ways that suggested a filter bubble. The most surprising result was that the #1 recommendation did not change for any profile between the baseline and the weight-shift experiment — despite significantly changing the weights, the mood bonus was still large enough to lock in the top result. This revealed that mood is the true controlling factor in the ranking, not energy or genre. The Ghost Genre profile was also revealing: with no catalog songs in "bossa nova," the system silently fell back to mood and energy scoring only, returning jazz and lofi songs — which happened to feel reasonable by accident, not by design.

---

## 8. Future Work

Three changes would most improve this system. First, include tempo and danceability in the scoring — a runner looking for 150 BPM workout music and someone wanting slow 70 BPM study music currently get the same results if their mood and energy match, which makes no sense. Second, expand the catalog significantly — with only one song per genre in most cases, the genre signal is nearly useless for most users; a catalog of at least 100 songs would give the genre and mood signals real room to differentiate. Third, reduce the mood weight or introduce soft matching — instead of a binary "mood matches or it doesn't," a similarity map (e.g., "chill" is close to "relaxed" but far from "angry") would let the system handle users whose exact mood isn't represented in the catalog without silently ignoring the preference.

---

## 9. Personal Reflection

**Biggest learning moment:** The weight-shift experiment was the clearest lesson. I doubled the energy weight and expected the top recommendations to change — they didn't. Every profile returned the same #1 song as before. That forced me to actually trace through the math and realize that mood (3.0 pts) was so much larger than anything else that no reasonable adjustment to other weights could unseat it. The learning wasn't about the algorithm itself; it was about how dominant signals can hide beneath the surface of a system that looks balanced on paper.

**Using AI tools:** AI tools were most useful for quickly explaining *why* a specific result happened — connecting the scoring weights to a concrete output in plain language. The place I had to double-check was the valence bucketing logic: the AI correctly described what the code does (treats "intense" as a negative-valence mood), but I had to verify manually that this was actually a flaw and not an intentional design choice by reading the original code carefully. AI tools describe behavior accurately; judging whether that behavior is *correct* still requires human reasoning about intent.

**How a simple algorithm can still "feel" like a recommendation:** The Ghost Genre profile (bossa nova) was the most surprising moment here. The system had never heard of bossa nova, gave zero genre points, and still returned Coffee Shop Stories (jazz/relaxed) at #1 — a song that genuinely sounds like something a bossa nova fan might enjoy. It felt like a thoughtful recommendation, but it was just math falling into place: low energy + high acousticness + relaxed mood happened to describe jazz as well as bossa nova. That moment made it obvious why users trust recommender systems even when the underlying logic is shallow — the output can feel intelligent even when the process isn't.

**What I'd try next:** The single most impactful extension would be adding tempo (BPM) as a scored feature. It's already in the dataset and completely ignored. A runner wanting 150 BPM and a person studying wanting 70 BPM are currently indistinguishable to the system. After that, I'd experiment with "soft" mood matching using a similarity scale — so that "chill" and "relaxed" score partial credit against each other instead of zero — which would immediately improve results for the Ghost Genre and conflicting-preference profiles.
