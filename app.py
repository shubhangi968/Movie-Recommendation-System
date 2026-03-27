import os
import pickle
import streamlit as st
import re
from PIL import Image
import base64
from io import BytesIO

# ---------------- PAGE CONFIG ----------------
st.set_page_config(page_title="CineMatch", layout="wide")

# ---------------- FUNCTIONS ----------------
def fetch_poster(movie_name):
    filename = movie_name.lower()
    filename = re.sub(r"[^a-z0-9 ]", "", filename)   # remove special chars
    filename = filename.replace(" ", "_") + ".jpg"

    path = os.path.join("posters",filename)

    print("Checking:", path)  # 👈 ADD THIS

    if os.path.exists(path):
        return Image.open(path)   
        if not os.path.exists(path):
            print("❌ NOT FOUND:", path)
    else:
        return "https://via.placeholder.com/300x450.png?text=No+Image"

def set_background(image_url):
    st.markdown(
        f"""
        <style>
        [data-testid="stAppViewContainer"] {{
            background:
                linear-gradient(rgba(0,0,0,0.75), rgba(0,0,0,0.95)),
                url("{image_url}");
            background-size: cover;
            background-position: center;
            background-attachment: fixed;
        }}

        [data-testid="stHeader"] {{
            background: rgba(0,0,0,0);
        }}

        .stApp {{
            background: transparent;
            color: white;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )

# ---------------- LOAD DATA ----------------
movies = pickle.load(open('movies.pkl', 'rb'))
similarity = pickle.load(open('similarity.pkl', 'rb'))
print(movies.columns)

# ---------------- RECOMMEND FUNCTION ----------------
def recommend(movie):
    movie_index = movies[movies['title'] == movie].index[0]
    distances = similarity[movie_index]

    movies_list = sorted(
        list(enumerate(distances)),
        reverse=True,
        key=lambda x: x[1]
    )[1:6]

    names = []
    posters = []

    for i in movies_list:
        names.append(movies.iloc[i[0]].title)
        posters.append(fetch_poster(movies.iloc[i[0]].title))

    return names, posters

# ---------------- DEFAULT BACKGROUND ----------------
if "selected_movie" not in st.session_state:
    default_bg = "https://images.unsplash.com/photo-1524985069026-dd778a71c7b4"
    set_background(default_bg)

# ---------------- CSS ----------------
st.markdown("""
<style>

/* Title */
.title {
    text-align: center;
    font-size: 52px;
    font-weight: bold;
    margin-bottom: 5px;
}

/* Subtitle */
.subtitle {
    text-align: center;
    font-size: 18px; 
    color: #cccccc;
    margin-bottom: 30px;
}

/* Glass card */
.glass {
    background: rgba(255, 255, 255, 0.08);
    border-radius: 20px;
    padding: 30px;
    backdrop-filter: blur(14px);
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
}

/* Button */
.stButton>button {
    background: linear-gradient(90deg, #ff416c, #ff4b2b);
    color: white;
    font-size: 18px;
    border-radius: 12px;
    padding: 10px 25px;
    transition: 0.3s;
}
.stButton>button:hover {
    transform: scale(1.08);
}

/* Movie Card */
.movie-card {
    width: 100%;
    height: 360px;   /*  SAME HEIGHT FOR ALL */
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    align-items: center;
    background: rgba(255,255,255,0.05);
    padding: 10px;
    border-radius: 15px;
    transition: 0.3s;
}
            
.movie-card:hover {
    transform: scale(1.08);
    box-shadow: 0px 10px 25px rgba(255,75,75,0.5);
}
            
/* Poster container */
.poster-box {
    width: 100%;
    height: 100px;   /*  FIXED IMAGE AREA */
    overflow: hidden;
    border-radius: 12px;
}

/* Image */
.poster-box img {
    width: 100%;
    height: 100%;
    object-fit: cover;   /*  KEY FIX */
}

/* Title */
.movie-title {
    text-align: center;
    font-size: 14px;
    margin-top: 8px;
    height: 40px;   /*  FIX TITLE HEIGHT */
    overflow: hidden;
}

            
</style>
""", unsafe_allow_html=True)

# ---------------- HEADER ----------------
st.markdown('<div class="title">🎬 CineMatch</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Discover movies you’ll love 🍿</div>', unsafe_allow_html=True)


# ---------------- SEARCH ----------------
search = st.text_input("🔍 Search for a movie")

filtered_movies = []
selected_movie = None

if search:
    filtered_movies = [
        m for m in movies['title'].values
        if search.lower() in m.lower()
    ]

    if filtered_movies:
        selected_movie = st.selectbox("Select movie", filtered_movies)
        st.session_state["selected_movie"] = selected_movie
    else:
        st.warning("No movie found")

# ---------------- DYNAMIC BACKGROUND ----------------
if "selected_movie" in st.session_state:
    movie_name = st.session_state["selected_movie"]
    movie_id = movies[movies['title'] == movie_name].iloc[0].id
    bg = fetch_poster(movie_name)
    if bg:
        st.image(bg)  # show image instead of background

# ---------------- RECOMMEND ----------------
st.markdown("""
<div class="glass" style="text-align:center; margin-bottom: 20px;">
    <h2>🍿 Find Your Next Favorite Movie</h2>
    <p>Search, explore, and get recommendations instantly</p>
</div>
""", unsafe_allow_html=True)

if st.button("✨ Recommend"):
    if selected_movie:
        names, posters = recommend(selected_movie)

        st.subheader("✨ Top Picks For You")

        cols = st.columns(5)

        for i in range(5):
            with cols[i]:
                if posters[i] is None:
                    img_html = "https://via.placeholder.com/300x450.png?text=No+Image"

                elif isinstance(posters[i],str):
                    # If it's already a path or URL
                    img_html = posters[i]
                else:
                    buffered = BytesIO()
                    posters[i].save(buffered,format="JPEG")
                    img_str = base64.b64encode(buffered.getvalue()).decode()
                    img_html = f"data:image'jpeg;base64,{img_str}" 
                
                st.markdown(f"""
                <div class="movie-card">
                    <div class="poster-box">
                        <img src="{img_html}">
                    </div>
                    <div class="movie-title">{names[i]}</div>
                </div>
                """, unsafe_allow_html=True)

                # If clicked → zoom effect
                

    else:
        st.warning("Please select a movie first")

st.markdown('</div>', unsafe_allow_html=True)