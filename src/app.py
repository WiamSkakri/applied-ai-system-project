"""
VibeFinder — free-text song search over the local 100-song catalog.

Run from the project root:
    .venv/bin/streamlit run src/app.py
"""
import sys
from pathlib import Path

# Allow `streamlit run src/app.py` to resolve `src.*` imports regardless of cwd.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import streamlit as st

from src.recommender import load_songs
from src.retrieval import SONGS_CSV, load_or_build_index, retrieve


EXAMPLE_QUERIES = [
    "Songs for a rainy sunday morning",
    "Angry workout music",
    "Romantic and slow for date night",
    "Focus music for late-night coding",
]

# Real queries top out around 0.40-0.46; gibberish lands ~0.10-0.20.
# 0.25 gives a comfortable margin in both directions.
MIN_TOP_SIMILARITY = 0.25


@st.cache_resource
def _bootstrap():
    songs = load_songs(str(SONGS_CSV))
    embeddings = load_or_build_index(songs)
    return songs, embeddings


def _set_query(text: str) -> None:
    st.session_state["query_input"] = text


def main() -> None:
    st.set_page_config(page_title="VibeFinder", page_icon="🎵")
    songs, embeddings = _bootstrap()

    with st.sidebar:
        st.title("🎵 VibeFinder")
        st.caption("Free-text search over a 100-song catalog.")
        st.divider()

        st.markdown("**Try a query**")
        for q in EXAMPLE_QUERIES:
            st.button(q, on_click=_set_query, args=(q,), use_container_width=True)

        st.divider()
        k = st.slider("Number of results", min_value=3, max_value=15, value=5)

    st.markdown("### Describe what you want to hear")
    query = st.text_input(
        "query",
        key="query_input",
        placeholder="e.g. cozy songs for a rainy morning",
        label_visibility="collapsed",
    )

    if query.strip():
        results = retrieve(query, songs, embeddings, k=k)
        top_score = results[0][1] if results else 0.0
        st.divider()

        if top_score < MIN_TOP_SIMILARITY:
            st.info(
                "Couldn't find a good match — try describing the mood, "
                "energy, or vibe you want."
            )
        else:
            for i, (song, _score) in enumerate(results, start=1):
                st.markdown(f"**{i}. {song['title']}**  \n{song['artist']}")
    else:
        st.caption("Type a description above or pick an example from the sidebar.")


if __name__ == "__main__":
    main()
