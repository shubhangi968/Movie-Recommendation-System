import pickle
import streamlit as st
import requests
import base64

#  PAGE CONFIG 
st.set_page_config(page_title="CineMatch", layout="wide")
def set_background():
    with open("bg.jpg", "rb") as f:
        data = f.read()
    encoded = base64.b64encode(data).decode()

    st.markdown(
        f"""
        <style>
        .stApp {{
            background-image: 
                linear-gradient(rgba(20,20,20,0.6), rgba(20,20,20,0.65)),
                url("data:image/jpg;base64,{encoded}");
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
            background-attachment: fixed;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )
set_background()

#  TMDB FUNCTION 
def fetch_movie_details(movie_name):
    url = f"https://tmdb.lewagon.com/search/movie?query={movie_name}"
    data = requests.get(url).json()

    if data["results"]:
        movie = data["results"][0]

        poster_path = movie.get("poster_path")
        overview = movie.get("overview")
        rating = movie.get("vote_average")
        
        if poster_path:
            poster_url = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else None
        else:
            poster_url = "https://via.placeholder.com/300x450?text=No+Image"
        return poster_url, overview, rating

    return "https://via.placeholder.com/300x450?text=No+Image", "No description available", "N/A"
    print (poster_path)

    
        
#  LOAD DATA 
movies = pickle.load(open('movies.pkl', 'rb'))
similarity = pickle.load(open('similarity.pkl', 'rb'))

#  RECOMMEND FUNCTION 
def recommend(movie):
    movie_index = movies[movies['title'] == movie].index[0]
    distances = similarity[movie_index]

    movies_list = sorted(
        list(enumerate(distances)),
        reverse=True,
        key=lambda x: x[1]
    )[1:6]

    names, posters, overviews, ratings = [], [], [], []

    for i in movies_list:
        movie_name = movies.iloc[i[0]].title

        poster, overview, rating = fetch_movie_details(movie_name)

        names.append(movie_name)
        posters.append(poster)
        overviews.append(overview)
        ratings.append(rating)

    return names, posters, overviews, ratings

#  CSS 
st.markdown("""
<style>
.title {
    text-align: center;
    font-size: 52px;
    font-weight: bold;
}

.subtitle {
    text-align: center;
    color: #cccccc;
    margin-bottom: 30px;
}

.movie-card {
    width: 100%;
    height: 360px;
    background: rgba(255,255,255,0.05);
    padding: 10px;
    border-radius: 15px;
    transition: 0.3s;
}
.movie-card:hover {
    transform: scale(1.08);
    box-shadow: 0px 10px 25px rgba(255,75,75,0.5);
}

.poster-box {
    width: 100%;
    height: 260px;
    overflow: hidden;
    border-radius: 12px;
    position: relative;
}

.poster-box img {
    width: 100%;
    height: 100%;
    object-fit: cover;
}

.overlay {
    position: absolute;
    bottom: 0;
    width: 100%;
    height: 100%;
    background: rgba(0,0,0,0.85);
    color: white;
    opacity: 0;
    transition: 0.3s;
    padding: 10px;
    font-size: 12px;
    overflow: hidden;
}

.poster-box:hover .overlay {
    opacity: 1;
}

.movie-title {
    text-align: center;
    font-size: 14px;
    margin-top: 8px;
    height: 40px;
    overflow: hidden;
}
</style>
""", unsafe_allow_html=True)

#  HEADER 
st.markdown('<div class="title">🎬 CineMatch</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Discover movies you’ll love 🍿</div>', unsafe_allow_html=True)

#  SEARCH 
search = st.text_input("🔍 Search for a movie")

selected_movie = None

if search:
    filtered = [m for m in movies['title'].values if search.lower() in m.lower()]

    if filtered:
        selected_movie = st.selectbox("Select movie", filtered)
    else:
        st.warning("No movie found")

#  RECOMMEND 
if st.button("✨ Recommend"):
    if selected_movie:
        names, posters, overviews, ratings = recommend(selected_movie)

        st.subheader("✨ Top Picks For You")
        cols = st.columns(5)

        for i in range(5):
            with cols[i]:
                img = posters[i] if posters[i] else "https://via.placeholder.com/300x450"

                st.markdown(f"""
                <div class="movie-card">
                    <div class="poster-box">
                        <img src="{img}">
                        <div class="overlay">
                            <h4>⭐ {ratings[i]}</h4>
                            <p>{overviews[i][:120]}...</p>
                        </div>
                    </div>
                    <div class="movie-title">{names[i]}</div>
                </div>
                """, unsafe_allow_html=True)

    else:
        st.warning("Please select a movie first")