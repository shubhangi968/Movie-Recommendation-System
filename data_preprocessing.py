import pandas as pd
import ast
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import pickle

# ---------------- STEP 1: LOAD DATA ----------------
movies = pd.read_csv('movies_metadata.csv', low_memory=False)
credits = pd.read_csv('credits.csv')
keywords = pd.read_csv('keywords.csv')

# 🔥 reduce dataset size (VERY IMPORTANT for deployment)
movies = movies.head(2000)

# ---------------- STEP 2: CLEAN DATA ----------------
movies = movies[['id', 'title', 'genres']]

# remove non-numeric ids
movies = movies[movies['id'].str.isnumeric()]
movies['id'] = movies['id'].astype(int)

# select required columns
credits = credits[['id', 'cast', 'crew']]
keywords = keywords[['id', 'keywords']]

# ---------------- STEP 3: MERGE ----------------
movies = movies.merge(credits, on='id')
movies = movies.merge(keywords, on='id')

# ---------------- STEP 4: CONVERT STRING → LIST ----------------
def convert(obj):
    try:
        return [i['name'] for i in ast.literal_eval(obj)]
    except:
        return []

movies['genres'] = movies['genres'].apply(convert)
movies['keywords'] = movies['keywords'].apply(convert)

# ---------------- STEP 5: CAST (TOP 3) ----------------
def convert_cast(obj):
    try:
        L = []
        counter = 0
        for i in ast.literal_eval(obj):
            if counter < 3:
                L.append(i['name'])
                counter += 1
            else:
                break
        return L
    except:
        return []

movies['cast'] = movies['cast'].apply(convert_cast)

# ---------------- STEP 6: DIRECTOR ----------------
def fetch_director(obj):
    try:
        for i in ast.literal_eval(obj):
            if i['job'] == 'Director':
                return [i['name']]
        return []
    except:
        return []

movies['crew'] = movies['crew'].apply(fetch_director)

# ---------------- STEP 7: REMOVE SPACES ----------------
def collapse(L):
    return [i.replace(" ", "") for i in L]

movies['genres'] = movies['genres'].apply(collapse)
movies['keywords'] = movies['keywords'].apply(collapse)
movies['cast'] = movies['cast'].apply(collapse)
movies['crew'] = movies['crew'].apply(collapse)

# ---------------- STEP 8: CREATE TAGS ----------------
movies['tags'] = (
    movies['genres'] +
    movies['keywords'] +
    movies['cast'] +
    movies['crew']
)

movies['tags'] = movies['tags'].apply(lambda x: " ".join(x))

# ---------------- STEP 9: FINAL DATAFRAME ----------------
new_df = movies[['id', 'title', 'tags']]

# ---------------- STEP 10: VECTORIZATION ----------------
tfidf = TfidfVectorizer(max_features=5000, stop_words='english')
vectors = tfidf.fit_transform(new_df['tags']).toarray()

# ---------------- STEP 11: SIMILARITY ----------------
similarity = cosine_similarity(vectors)

# ---------------- STEP 12: SAVE FILES ----------------
pickle.dump(new_df, open('movies.pkl', 'wb'))
pickle.dump(similarity, open('similarity.pkl', 'wb'))

print("✅ Everything processed and saved successfully!")