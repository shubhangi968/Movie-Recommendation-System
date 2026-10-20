import pickle
import streamlit as st
import re
from difflib import get_close_matches
from gemini_helper import (
    suggest_seed_titles,
    fetch_movie_details,
    explain_recommendations
)

st.set_page_config(
    page_title="CineMatch AI Assistant",
    layout="wide"
)

st.title("CineMatch AI Assistant")
st.caption(
    "Describe what you want to watch. "
    "Gemini interprets your request and explains recommendations."
)

api_key = st.secrets.get("GEMINI_API_KEY", "")

@st.cache_resource
def load_data():
    with open("movies.pkl", "rb") as file:
        movies = pickle.load(file).reset_index(drop=True)

    with open("similarity.pkl", "rb") as file:
        similarity = pickle.load(file)

    return movies, similarity


try:
    movies, similarity = load_data()
except Exception as exc:
    st.error(f"Could not load movie data: {exc}")
    st.stop()


# Build a lookup from movie title to row index.
# Normalize titles to handle punctuation and spelling differences.
def normalize_title(title):
    title = str(title).lower().strip()
    title = re.sub(r"[^a-z0-9\s]", "", title)
    return " ".join(title.split())
title_lookup = {}

for i, title in enumerate(movies["title"].astype(str)):
    normalized = normalize_title(title)
    title_lookup.setdefault(normalized, i)

def match_title(title):
    cleaned = normalize_title(title)

    if not cleaned:
        return None

    # 1. Exact match after normalization
    if cleaned in title_lookup:
        return title_lookup[cleaned]

    # 2. Partial match, only if unambiguous
    matches = [
        (name, idx)
        for name, idx in title_lookup.items()
        if cleaned in name or name in cleaned
    ]

    if len(matches) == 1:
        return matches[0][1]

    # 3. Fuzzy match for minor differences
    close = get_close_matches(
        cleaned,
        list(title_lookup.keys()),
        n=1,
        cutoff=0.75
    )

    if close:
        return title_lookup[close[0]]

    return None


def recommend_from_seeds(seed_indices, k=5):
    import numpy as np

    scores = np.mean(
        [similarity[i] for i in seed_indices],
        axis=0
    )

    ranked = sorted(
        enumerate(scores),
        key=lambda item: item[1],
        reverse=True
    )

    return [
        idx for idx, _ in ranked
        if idx not in seed_indices
    ][:k]

query = st.text_input(
    "What do you want to watch?",
    placeholder="A mind-bending thriller, or Inception"
)

if st.button("Ask AI", type="primary"):
    if not query.strip():
        st.warning("Enter a movie title or describe your preferences.")
        st.stop()

    if not api_key:
        st.error(
            "Add GEMINI_API_KEY to .streamlit/secrets.toml."
        )
        st.stop()

    try:
        with st.spinner("Understanding your request..."):
            direct_idx = match_title(query)

            if direct_idx is not None:
                seed_indices = [direct_idx]
            else:
                guesses = suggest_seed_titles(query, api_key)

                seed_indices = []
                for guess in guesses:
                    idx = match_title(guess)

                    if idx is not None and idx not in seed_indices:
                        seed_indices.append(idx)

                seed_indices = seed_indices[:3]

        if not seed_indices:
            st.warning(
                "No matching movies found in your dataset. "
                "Try a specific movie title or a clearer description."
            )
            st.stop()

        seed_titles = [
            str(movies.iloc[i]["title"])
            for i in seed_indices
        ]

        recommended_indices = recommend_from_seeds(seed_indices)

        details = {}

        with st.spinner("Getting movie details..."):
            for idx in recommended_indices:
                title = str(movies.iloc[idx]["title"])
                details[title] = fetch_movie_details(title)

        candidates = [
            {
                "title": title,
                "overview": overview[:500],
                "rating": rating
            }
            for title, (_, overview, rating) in details.items()
        ]

        with st.spinner("Generating AI explanations..."):
            explanations = explain_recommendations(
                query,
                seed_titles,
                candidates,
                api_key
            )

        st.success("Based on: " + ", ".join(seed_titles))

        if not details:
            st.info("No recommendations were found.")
        else:
            columns = st.columns(len(details))

            for column, (title, data) in zip(
                columns, details.items()
            ):
                poster, overview, rating = data

                with column:
                    if poster:
                        st.image(
                            poster,
                            use_container_width=True
                        )

                    st.markdown(f"**{title}**")

                    if isinstance(rating, (int, float)):
                        st.caption(f"Rating: {rating:.1f}/10")

                    st.write(
                        explanations.get(
                            title,
                            "No AI explanation was returned."
                        )
                    )

                    with st.expander("Movie overview"):
                        st.write(overview)

    except Exception as exc:
        st.error(f"AI Assistant failed: {exc}")
        st.caption(
            "Check your API key, model availability, API limits, "
            "internet connection, and local pickle files."
        )
