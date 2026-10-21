# 🎬 CineMatch – Movie Recommendation System

CineMatch is a content-based movie recommendation system that suggests similar movies using machine learning techniques based on genres, keywords, and metadata.
---
🌐 **Live Demo:** [Click here to view](https://movie-recommendation-system-4z7xzevpr6fje2njtfghvp.streamlit.app)

## 🚀 Features

- 🔍 Search for any movie
- 🎯 Get top 5 similar movie recommendations
- 🖼️ Real-time posters using TMDB API
- ⭐ Ratings and overview on hover
- 🎨 Modern UI with smooth animations
- 🌌 Cinematic background design

---

## 🧠 Tech Stack

- Python
- Streamlit
- Machine Learning (Cosine Similarity)
- TMDB API (via proxy)
- Pandas, Pickle

---

## ⚙️ How It Works

1. Movie dataset is processed and converted into tags
2. Cosine similarity is used to find similar movies
3. User selects a movie
4. Top 5 similar movies are recommended
5. TMDB API fetches posters, ratings, and overview

---

## 📂 Project Structure

Movie recommendation system/
│── app.py
│── movies.pkl
│── similarity.pkl 
│── requirements.txt
│── gemini.helpers.py
│── README.md



## ▶️ Run Locally

```bash
cd Movie-Recommendation-System
pip install -r requirements.txt
streamlit run app.py


---


💡 Future Improvements

🎬 Add movie trailers
📈 Show trending movies
❤️ Add user favorites/watchlist
🔎 Improve recommendation accuracy

👩‍💻 Author

Shubhangi Agrawal
