# 🎧 Model Card: Music Recommender Simulation

## 1. Model Name

**MoodMatch 2.0** (also referred to as VibeFinder in the Streamlit UI). Version 1.0 was the structured-profile content-based scorer from Modules 1–3; version 2.0 layers a free-text RAG retriever on top of the same catalog.

---

## 2. Intended Use

MoodMatch suggests songs from a 100-track catalog based on what a listener describes they want. The system supports two interaction modes:

- **Free-text mode (RAG, primary):** the user types a natural-language description like *"songs for a rainy sunday morning"* or *"angry workout music"*, and the system returns the 5 closest matches by semantic similarity. Available via the Streamlit UI (`streamlit run src/app.py`).
- **Structured-profile mode (baseline):** the user supplies a typed taste profile (`genre`, `mood`, `target_energy`, `likes_acoustic`) and the system applies hand-coded scoring rules. Available via the CLI (`python -m src.main`).

This is a classroom simulation, not a production system. It is not designed for real streaming platforms, real user data, or catalogs at production scale.

---

## 3. How the Model Works

### Original layer — structured-profile scoring

The recommender scores every song in the catalog against what the user told it they want, then returns the top five. Each song earns points in five categories:

- **Mood match** — exact-match bonus (3 points). The largest single signal.
- **Genre match** — exact-match bonus (1 point in the current weight-shift version, originally 2).
- **Energy fit** — proximity to the user's target energy (up to 4 points). On-target = full points; far-off ≈ zero.
- **Acousticness fit** — acoustic songs are rewarded for users who like acoustic; electric songs for those who don't (up to 1.5 points).
- **Valence fit** — positive moods (happy, energetic) reward high-valence songs; other moods reward low-valence ones (up to 1 point).

The weights were modified from the original as part of an experiment: energy was doubled (2.0 → 4.0) and genre was halved (2.0 → 1.0) to test how sensitive the rankings are to weight changes.

### RAG layer — free-text semantic retrieval

A free-text query is processed end-to-end:

1. **Blurb generation.** Each song is converted at index time into a one-sentence English description that includes mood, genre, and human-readable bands of every audio feature (e.g. *"a melancholic jazz song. It is calm (energy 0.14), downbeat and somber (valence 0.11), mid-tempo at 89 BPM, mostly acoustic, moderately danceable."*).
2. **Embedding.** Both the song blurbs and the user's query are encoded with `sentence-transformers/all-MiniLM-L6-v2` into 384-dimensional vectors.
3. **Retrieval.** Cosine similarity between the query vector and each song vector. The top K songs are returned.
4. **Confidence guardrail.** If the highest similarity score is below 0.25, the system returns a friendly rejection instead of results — this catches gibberish input and queries the catalog cannot serve.

The two layers operate independently on the same catalog. Either entry point yields rankings without touching the other.

---

## 4. Data

The catalog contains 100 real songs sampled from the public Hugging Face mirror of the Spotify Tracks Dataset (`maharshipandya/spotify-tracks-dataset`). Sampling is reproducible — driven by [`scripts/build_catalog.py`](scripts/build_catalog.py) with `seed=42` and a `popularity ≥ 20` filter to exclude the most obscure tracks.

**Genre coverage:** 20 genres, 5 songs each: pop, rock, jazz, classical, hip-hop, r-n-b, edm, country, folk, metal, indie, blues, soul, funk, reggae, punk, ambient, house, techno, acoustic.

**Audio features used:** Each song has 10 fields — id, title, artist, genre, mood, energy (0–1), tempo_bpm, valence (0–1), danceability (0–1), acousticness (0–1).

**Mood derivation.** Spotify's audio features include `energy`, `valence`, `danceability`, `acousticness`, and `tempo`, but **not** a `mood` label. The build script derives mood from valence and energy:

| Rule | Mood |
|---|---|
| valence ≥ 0.6 and energy ≥ 0.6 | `happy` |
| valence ≥ 0.6 and energy < 0.4 | `chill` |
| valence ≥ 0.6 (mid-energy) | `relaxed` |
| valence < 0.4 and energy ≥ 0.7 | `intense` |
| valence < 0.4 and energy < 0.4 | `melancholic` |
| valence < 0.4 (mid-energy) | `sad` |
| mid-valence and energy ≥ 0.7 | `energetic` |
| mid-valence and energy < 0.4 | `focused` |
| else | `moody` |

The resulting mood distribution is uneven: `happy` (22), `melancholic` (19), `sad` (14), `intense` (13), `moody` (11), `relaxed` (10), `energetic` (8), `chill` (2), `focused` (1). This is an honest reflection of how real Spotify tracks distribute across the valence/energy plane.

---

## 5. Strengths

The system handles two very different interaction styles cleanly. The **structured-profile mode** is fully transparent: every recommendation comes with a plain-language explanation listing exactly which signals contributed and by how much, which makes it easy to audit *why* a song was picked. The **RAG mode** handles vague, emotional, or context-rich queries that the structured mode cannot — *"songs for a rainy sunday morning"* has no field on the user profile, but semantic retrieval handles it without any additional scaffolding.

The RAG layer also gracefully handles **out-of-vocabulary cases.** A query for a mood that doesn't exist in the rule-derived label set (e.g. "nostalgic") would return zero results in mood-exact-match scoring, but in semantic retrieval it returns plausible matches (folk, acoustic, melancholic) because the embedder understands "nostalgic" without needing a label.

The **confidence guardrail** prevents the silent-failure mode that pure cosine retrieval has by default: instead of returning random near-neighbors for gibberish input, the system tells the user no good match was found.

---

## 6. Limitations and Bias

**Mood-matching dominance (structured mode).** Mood carries 3.0 points out of a maximum 10.5 (~29%), which consistently overrides other preferences. A user who wants high-energy *sad* music will always receive a slow, low-energy sad song at the top — the energy mismatch can't overcome the mood bonus. The 6-profile stress test in `python -m src.main` makes this visible.

**Mood derivation is reductive (RAG mode).** The valence/energy rule produces only 9 mood labels, and the distribution skews heavily toward `happy`, `melancholic`, and `sad`. Underrepresented labels like `chill` (2 songs) and `focused` (1 song) make those user profiles practically unsearchable through the mood-exact-match rule. Lyrical/cultural moods like `nostalgic`, `romantic`, or `confident` cannot be derived from audio features at all.

**Popularity filter biases toward English/Western charts.** The build script's `popularity ≥ 20` cutoff over-represents the languages and artists Spotify's algorithm has already amplified, under-serving regional music.

**The embedder is general-purpose, not music-specific.** `all-MiniLM-L6-v2` was trained on web text, not music descriptions. It treats the word *"music"* as a strong matching signal regardless of catalog contents — a query for *"polka music for accordion fans"* scores 0.404 (above the 0.25 threshold) even though the catalog has zero polka. The threshold catches gibberish, not the *"valid English query for music we don't have"* failure mode.

**Two audio features remain unused in the structured scorer.** Tempo (BPM) and danceability are loaded but never scored, meaning a runner wanting 150 BPM and someone studying wanting 70 BPM are currently indistinguishable in structured mode if their other fields match. (Both fields *are* used in the RAG blurbs, so RAG mode does discriminate on tempo to some extent.)

---

## 7. Evaluation

The system was evaluated two ways.

**Manual evaluation (structured mode, 6 profiles):** Six user profiles were tested across two scoring runs — a baseline (genre: 2.0, energy: 2.0) and a weight-shift experiment (energy: 4.0, genre: 1.0). The most surprising result was that the #1 recommendation did not change for any profile between the two runs. Despite significantly changing the weights, the mood bonus was still large enough to lock in the top result, revealing that mood was the true controlling factor in the ranking.

**Automated evaluation (RAG mode, 10 property-based assertions):** [`scripts/evaluate.py`](scripts/evaluate.py) defines 10 free-text queries with property-based expectations (genre or mood band, average energy/acousticness, similarity threshold for gibberish). The current pass rate is **9/10 (90%)**.

The single failure (`"upbeat happy summer vibes"`) is itself instructive: the top retrieved song is *In the Summertime* by Mungo Jerry — semantically a perfect summer-themed result — but its mood was rule-derived to `relaxed` rather than `happy`. The retrieval did the right thing; the mood-derivation rule mislabeled the song. This failure is direct evidence of the *"mood derivation is reductive"* limitation in section 6.

The other 9 cases pass with healthy margin: top-3 average acousticness 0.93 for an "acoustic studying" query, top-3 average energy 0.90 for a "dance party" query, gibberish similarity 0.163 (well below the 0.25 threshold), and so on. Run the harness with `python -m scripts.evaluate`.

---

## 8. Future Work

Three changes would most improve this system.

1. **Use a music-domain embedder, not a general-text one.** Models trained on music descriptions or audio (CLAP, MULE, or even a fine-tuned MiniLM) would understand *"polka"*, *"shoegaze"*, *"slowcore"*, etc. — words the current embedder treats as generic noise.
2. **Add an LLM-generated playlist intro.** With an optional Anthropic API key, the app could generate a short personalized paragraph framing the playlist that references the user's exact words. The infrastructure (sidebar key input, graceful fallback) was scoped during design but not implemented.
3. **Expand the catalog and use richer mood labeling.** A larger catalog (1,000+ songs) plus an LLM-generated mood label per song (instead of the rule-based valence/energy map) would fix both the underrepresented-mood problem and the lyrical-mood problem at once.

---

## 9. Personal Reflection

**Biggest learning moment:** The weight-shift experiment was the clearest lesson. I doubled the energy weight and expected the top recommendations to change — they didn't. Every profile returned the same #1 song as before. That forced me to actually trace through the math and realize that mood (3.0 pts) was so much larger than anything else that no reasonable adjustment to other weights could unseat it. The learning wasn't about the algorithm itself; it was about how dominant signals can hide beneath the surface of a system that looks balanced on paper.

**Using AI tools:** AI tools were most useful for quickly explaining *why* a specific result happened — connecting the scoring weights to a concrete output in plain language. The place I had to double-check was the valence bucketing logic: the AI correctly described what the code does (treats "intense" as a negative-valence mood), but I had to verify manually that this was actually a flaw and not an intentional design choice by reading the original code carefully. AI tools describe behavior accurately; judging whether that behavior is *correct* still requires human reasoning about intent.

**How a simple algorithm can still "feel" like a recommendation:** The Ghost Genre profile (bossa nova) was the most surprising moment here. The system had never heard of bossa nova, gave zero genre points, and still returned Coffee Shop Stories (jazz/relaxed) at #1 — a song that genuinely sounds like something a bossa nova fan might enjoy. It felt like a thoughtful recommendation, but it was just math falling into place: low energy + high acousticness + relaxed mood happened to describe jazz as well as bossa nova. That moment made it obvious why users trust recommender systems even when the underlying logic is shallow — the output can feel intelligent even when the process isn't.

**What I'd try next:** The single most impactful extension would be adding tempo (BPM) as a scored feature. It's already in the dataset and completely ignored. A runner wanting 150 BPM and a person studying wanting 70 BPM are currently indistinguishable to the system. After that, I'd experiment with "soft" mood matching using a similarity scale — so that "chill" and "relaxed" score partial credit against each other instead of zero — which would immediately improve results for the Ghost Genre and conflicting-preference profiles.
