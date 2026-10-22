# 🎬 CineMatch – Movie Recommendation System

CineMatch is a content-based movie recommendation system that suggests similar movies using machine learning techniques based on genres, keywords, and metadata.

## 🚀 Features

- 🔍 Search for any movie
- 🎯 Get top 5 similar movie recommendations
- ⭐ Ratings and overview
- 🌌 Cinematic background design
- 🤖 AI Assistance

---

## 🧠 Tech Stack

- Python
- Streamlit
- Machine Learning (Cosine Similarity)
- TMDB API (via proxy)
- Pandas, Pickle
- API Integration 

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


👩‍💻 Author

Shubhangi Agrawal

