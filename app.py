import base64
import html
import os
import pickle
from concurrent.futures import ThreadPoolExecutor
import numpy as np
import requests
import streamlit as st
from gemini_helper import movie_expert_reply

st.set_page_config(page_title="CineMatch", layout="wide")  # must be first

NO_POSTER = "https://placehold.co/300x450?text=No+Image"

# ---------- DATA (loaded once) ----------
@st.cache_resource
def load_data():
    with open("movies.pkl", "rb") as f:
        movies = pickle.load(f)
    with open("similarity.pkl", "rb") as f:
        similarity = pickle.load(f)
    title_to_idx = {}
    for i, t in enumerate(movies["title"]):
        title_to_idx.setdefault(t, i)
    return movies, similarity, title_to_idx


movies, similarity, title_to_idx = load_data()


# ---------- STYLE ----------
@st.cache_data
def background_css():  # encoded once, not on every rerun
    try:
        with open("bg.jpg", "rb") as f:
            enc = base64.b64encode(f.read()).decode()
    except FileNotFoundError:
        return ""
    return (".stApp{background-image:linear-gradient(rgba(20,20,20,.6),"
            f"rgba(20,20,20,.65)),url('data:image/jpeg;base64,{enc}');"
            "background-size:cover;background-position:center;"
            "background-attachment:fixed}")


CSS = """
.title{text-align:center;font-size:52px;font-weight:bold}
.subtitle{text-align:center;color:#ccc;margin-bottom:30px}
.movie-card{width:100%;background:rgba(255,255,255,.05);padding:10px;
  border-radius:15px;transition:.3s}
.movie-card:hover:not(:has(details[open])){transform:scale(1.03);
  box-shadow:0 10px 25px rgba(255,75,75,.5)}
.movie-title{text-align:center;font-size:14px;margin-top:8px;min-height:40px;
  overflow-wrap:anywhere}
.reason{font-size:12px;color:#ccc;text-align:center;margin-top:5px}

/* poster (clickable) */
summary.poster-box{display:block;list-style:none;cursor:pointer;width:100%;
  height:260px;overflow:hidden;border-radius:12px;position:relative}
summary.poster-box::-webkit-details-marker{display:none}
.poster-box>img{width:100%;height:100%;object-fit:cover}
.overlay{position:absolute;inset:0;background:rgba(0,0,0,.85);color:#fff;
  opacity:0;transition:.3s;padding:10px;font-size:12px;overflow:auto;
  box-sizing:border-box}
.poster-box:hover .overlay{opacity:1}

/* enlarged view: summary becomes the dark backdrop, .modal the card */
details[open]>summary.poster-box{position:fixed;inset:0;height:auto;
  border-radius:0;z-index:999994;background:rgba(0,0,0,.85);cursor:zoom-out}
details[open]>summary.poster-box>*{display:none}
.modal{display:none}
details[open] .modal{display:flex;flex-wrap:wrap;gap:20px;position:fixed;
  top:50%;left:50%;transform:translate(-50%,-50%);z-index:999995;
  width:min(720px,92vw);max-height:85vh;overflow:auto;background:#1b1b1f;
  color:#fff;border-radius:16px;padding:20px;box-sizing:border-box;
  box-shadow:0 20px 60px rgba(0,0,0,.7)}
.modal img{width:240px;max-width:100%;border-radius:12px;object-fit:cover}
.modal .info{flex:1;min-width:220px}
.modal h2{margin:0 0 6px}
.modal .hint{color:#888;font-size:12px}

/* floating chat button */
div[data-testid="stPopover"]{position:fixed;bottom:22px;right:22px;z-index:999999}
div[data-testid="stPopover"]>button{border-radius:30px;background:#e64b55;
  color:#fff;border:none;padding:12px 20px;font-weight:bold;
  box-shadow:0 4px 18px rgba(0,0,0,.35)}
div[data-testid="stPopover"]>button:hover{background:#c93642;color:#fff}
div[data-testid="stPopoverBody"]{width:min(380px,90vw)}
"""
st.markdown(f"<style>{background_css()}{CSS}</style>", unsafe_allow_html=True)


# ---------- TMDB ----------
@st.cache_data(ttl=3600, show_spinner=False)
def _fetch(name):
    r = requests.get("https://tmdb.lewagon.com/search/movie",
                     params={"query": name}, timeout=5)
    r.raise_for_status()
    results = r.json().get("results") or []
    if not results:
        return dict(poster=NO_POSTER, overview="No description available.",
                    rating=None, year="")
    m = results[0]
    path = m.get("poster_path")
    return dict(
        poster=f"https://image.tmdb.org/t/p/w500{path}" if path else NO_POSTER,
        overview=m.get("overview") or "No description available.",
        rating=m.get("vote_average"),
        year=(m.get("release_date") or "")[:4])


def fetch_movie_details(name):  # failures are not cached, so they can retry
    try:
        return _fetch(name)
    except (requests.RequestException, ValueError):
        return dict(poster=NO_POSTER, rating=None, year="",
                    overview="Movie details are temporarily unavailable.")


# ---------- RECOMMEND ----------
def recommend(title):
    i = title_to_idx[title]
    row = np.asarray(similarity[i])
    top = np.argpartition(-row, 6)[:6]            # fast top-6, no full sort
    top = [j for j in top[np.argsort(-row[top])] if j != i][:5]
    names = movies["title"].iloc[top].tolist()
    with ThreadPoolExecutor(max_workers=5) as ex:
        details = list(ex.map(fetch_movie_details, names))
    own = set(str(movies.iloc[i]["tags"]).split())
    out = []
    for j, name, d in zip(top, names, details):
        common = list(own & set(str(movies.iloc[j]["tags"]).split()))[:5]
        out.append({**d, "title": name,
                    "reason": ", ".join(common) or "Similar movie features"})
    return out


def esc(text):
    return html.escape(" ".join(str(text).split()))  # one line: keeps HTML intact


def card_html(m):
    rating = f"{m['rating']:.1f}" if isinstance(m["rating"], (int, float)) else "N/A"
    title, poster = esc(m["title"]), html.escape(m["poster"])
    year = f" ({esc(m['year'])})" if m["year"] else ""
    return (
        '<div class="movie-card"><details>'
        f'<summary class="poster-box"><img src="{poster}" loading="lazy">'
        f'<div class="overlay"><h4>⭐ {rating}</h4>'
        f'<p>{esc(m["overview"][:120])}...</p><small>Click to enlarge</small></div></summary>'
        f'<div class="modal"><img src="{poster}"><div class="info">'
        f'<h2>{title}{year}</h2><p>⭐ {rating}</p><p>{esc(m["overview"])}</p>'
        f'<p><b>Because of:</b> {esc(m["reason"])}</p>'
        '<p class="hint">Click outside to close</p></div></div></details>'
        f'<div class="movie-title">{title}</div>'
        f'<p class="reason">Because of: {esc(m["reason"])}</p></div>')


# ---------- MAIN PAGE ----------
st.markdown('<div class="title">🎬 CineMatch</div>'
            '<div class="subtitle">Discover movies you’ll love 🍿</div>',
            unsafe_allow_html=True)

search = st.text_input("🔍 Search for a movie")
selected = None
if search:
    matches = movies.loc[movies["title"].str.contains(
        search, case=False, na=False, regex=False), "title"].tolist()
    if matches:
        selected = st.selectbox("Select movie", matches)
    else:
        st.warning("No movie found")

if st.button("✨ Recommend"):
    if selected:
        with st.spinner("Finding movies you'll love..."):
            st.session_state.recs = recommend(selected)
    else:
        st.warning("Please select a movie first.")

# Results live in session_state so they survive chat messages and reruns.
if st.session_state.get("recs"):
    st.subheader("✨ Top Picks For You")
    for col, m in zip(st.columns(5), st.session_state.recs):
        col.markdown(card_html(m), unsafe_allow_html=True)


# ---------- FLOATING AI CHAT ----------
def get_api_key():
    try:
        return st.secrets["GEMINI_API_KEY"]
    except Exception:
        return os.getenv("GEMINI_API_KEY", "")


GREETING = ("Hi! I'm CineMatch Movie Expert 🍿 I can compare films, explain "
            "endings, and give spoiler-free reviews.")
history = st.session_state.setdefault(
    "cine_chat_history", [{"role": "assistant", "content": GREETING}])


@st.fragment  # chat reruns only itself, not the whole page
def chat():
    with st.popover("💬 AI Assist"):
        st.markdown("### 🎬 CineMatch AI")
        box = st.container()
        with st.form("cine_ai_chat_form", clear_on_submit=True):
            msg = st.text_input("Your message",
                                placeholder="Ask anything about a movie...")
            sent = st.form_submit_button("Send")
        if sent and msg.strip():
            history.append({"role": "user", "content": msg.strip()})
            key = get_api_key()
            if not key:
                answer = "Gemini API key not found. Add GEMINI_API_KEY to secrets."
            else:
                try:
                    with st.spinner("Thinking..."):
                        answer = movie_expert_reply(msg.strip(), key, history[:-1])
                except Exception as e:
                    answer = f"AI error: {type(e).__name__}: {e}"
            history.append({"role": "assistant", "content": answer})
        with box:
            for m in history:
                with st.chat_message(m["role"]):
                    st.markdown(m["content"])


chat()