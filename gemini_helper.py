import json
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor
import requests
from google import genai
from google.genai import types

# Flash-Lite is the fastest and has the most generous free quota.
# Switch back with:  export GEMINI_MODEL=gemini-3.8-flash
MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
TIMEOUT_MS = 25000  # milliseconds: fail fast instead of hanging


def clean_json(text):
    """Strip ```json fences and any text around the JSON (this was missing)."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.IGNORECASE)
    match = re.search(r"(\{.*\}|\[.*\])", text, flags=re.DOTALL)
    return match.group(1) if match else text


def _config(max_tokens, json_mode):
    kwargs = dict(max_output_tokens=max_tokens, temperature=0.4)
    if json_mode:
        kwargs["response_mime_type"] = "application/json"
    try:
        # Gemini 3.x "thinks" by default; thinking tokens are slow and eat the
        # output budget. Keep it low for these simple tasks.
        return types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(thinking_level="low"), **kwargs)
    except Exception:  # older SDK without thinking_level
        return types.GenerateContentConfig(**kwargs)


def generate_text(prompt, api_key, max_tokens=400, json_mode=False):
    start = time.time()
    try:
        client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(
                timeout=TIMEOUT_MS,
                retry_options=types.HttpRetryOptions(attempts=1)),
        )
        response = client.models.generate_content(
            model=MODEL, contents=prompt, config=_config(max_tokens, json_mode))
        if not response.text:
            raise RuntimeError("Gemini returned an empty response.")
        return response.text.strip()
    except Exception as exc:
        raise RuntimeError(
            f"Gemini request failed ({type(exc).__name__}): {exc}") from exc
    finally:
        print(f"[gemini] {MODEL} took {time.time() - start:.1f}s", flush=True)


def suggest_seed_titles(user_query, api_key):
    prompt = f"""You are a movie recommendation assistant.
User request: {user_query}
Return a JSON array of up to 3 real movie titles that match the request.
If the user enters a movie title, include that movie.
Return only the JSON array."""
    result = generate_text(prompt, api_key, max_tokens=120, json_mode=True)
    try:
        titles = json.loads(clean_json(result))
    except json.JSONDecodeError as exc:
        raise RuntimeError("Gemini returned invalid movie-title JSON.") from exc
    if not isinstance(titles, list):
        raise RuntimeError("Gemini did not return a JSON list.")
    return [str(t).strip() for t in titles if str(t).strip()][:3]


def fetch_movie_details(movie_name):
    try:
        response = requests.get("https://tmdb.lewagon.com/search/movie",
                                params={"query": movie_name}, timeout=(3, 6))
        response.raise_for_status()
        results = response.json().get("results", [])
        if not results:
            return None, "No overview available.", None
        movie = results[0]
        path = movie.get("poster_path")
        poster = f"https://image.tmdb.org/t/p/w500{path}" if path else None
        return poster, movie.get("overview") or "No overview available.", \
            movie.get("vote_average")
    except (requests.RequestException, ValueError):
        return None, "Movie details are unavailable.", None


def fetch_many_details(movie_names):
    """Fetch all posters in parallel. Returns {title: (poster, overview, rating)}."""
    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(fetch_movie_details, movie_names))
    return dict(zip(movie_names, results))


def explain_recommendations(user_query, seed_titles, candidates, api_key):
    if not candidates:
        return {}
    prompt = f"""You are CineMatch, a movie recommendation assistant.
User request: {user_query}
Matched movies: {json.dumps(seed_titles, ensure_ascii=False)}
Recommended movies: {json.dumps(candidates, ensure_ascii=False)}
For each recommended movie, explain in 1-2 short sentences why it may suit the
request. Use only the supplied information. Return ONLY a JSON object where each
key is the exact recommended title and each value is the explanation."""
    result = generate_text(prompt, api_key, max_tokens=700, json_mode=True)
    try:
        explanations = json.loads(clean_json(result))
    except json.JSONDecodeError as exc:
        raise RuntimeError("Gemini returned invalid explanation JSON.") from exc
    if not isinstance(explanations, dict):
        raise RuntimeError("Gemini did not return a JSON object.")
    allowed = {m["title"] for m in candidates}
    return {t: e for t, e in explanations.items()
            if t in allowed and isinstance(e, str)}


def movie_expert_reply(user_message, api_key, history=None):
    history = history or []
    conversation = "\n".join(
        f'{i["role"]}: {i["content"][:400]}' for i in history[-4:]
        if i.get("role") in ("user", "assistant"))
    prompt = f"""You are CineMatch, a concise movie expert.
Help users compare movies, explain endings, give spoiler-free reviews and content warnings, discuss themes.
Rules: friendly and direct, headings for comparisons; never
invent facts, ratings or awards; recommend movies if asked; if key
details are missing, ask one short question, give detail answers.

Recent conversation:
{conversation}

Latest message: {user_message}

Reply directly."""
    return generate_text(prompt, api_key, max_tokens=500)

SYSTEM_PROMPT = """You are CineMatch AI, a friendly, intelligent, and knowledgeable movie expert built into CineMatch, a movie discovery and recommendation application: warm, natural and conversational.
YOUR MISSION
Help users discover movies they will love, make confident viewing decisions, understand films, and enjoy talking about cinema. Give accurate, relevant, personalized, and natural answers.
CORE RULES
1. Answer the user's actual question directly before adding extra information.
2. Be conversational, warm, clear, and concise. Avoid generic introductions, repetitive wording, and unnecessary long lists.
3. Personalize recommendations using the user's stated mood, favorite movies, genres, language, preferred era, runtime, and other preferences. Use conversation history when relevant.
4. When asked for a recommendation, normally suggest 1–3 movies, explain briefly why each fits, and identify the strongest match. If the user asks for one movie, give one.
5. For each recommendation, provide the title and release year when known, a brief spoiler-free premise, genre, and why it suits the user's request. Include ratings or runtime only when reliable data is available.
6. Never invent movie titles, release dates, cast members, directors, plot details, quotes, awards, ratings, streaming availability, or other facts. If uncertain, say so clearly or omit the detail.
7. Prefer movie titles and metadata verified by the application's movie dataset or trusted movie API. Never claim that you checked a source if you did not.
8. Respect language and regional preferences. Do not assume the user wants Hollywood movies; consider Indian, international, animated, and independent cinema when appropriate.
9. Avoid recommending a movie the user has already rejected or said they have watched, unless they ask about it.
10. If the request is broad, make a sensible recommendation rather than asking lots of questions. Ask one brief follow-up only when a missing preference materially affects the result.
11. If the user explicitly asks for an ending explanation or spoilers, answer directly and label the response as containing spoilers.
12. Distinguish confirmed story events from interpretations and theories.
MOVIE RECOMMENDATIONS
- Match the requested mood, genre, themes, tone, and content preferences rather than relying only on popularity.
- Explain what makes each recommendation a good fit.
- When asked for hidden gems, prioritize less mainstream choices when reliable information supports that characterization.
- For 'Surprise me', choose a suitable real movie and provide a short reason.
- For 'what should I watch tonight?', offer a strong choice and a couple of alternatives only if useful.
- For similar-movie requests, identify the relevant similarity, such as atmosphere, storytelling, themes, or genre. Do not imply two movies are identical.

MOVIE COMPARISONS
Compare the requested films using relevant criteria such as story, pacing, performances, visuals, tone, complexity, and audience fit. Give a clear recommendation based on the user's priorities, while acknowledging that taste is subjective.

QUALITY CHECK BEFORE RESPONDING
Check that you answered the question, matched the user's preferences, avoided unwanted spoilers, did not invent facts, and gave a clear next step or recommendation when appropriate."""

def _chat_config(system):
    kwargs = dict(system_instruction=system, temperature=0.7, max_output_tokens=1200)
    try:
        return types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(thinking_level="low"), **kwargs)
    except Exception:
        return types.GenerateContentConfig(**kwargs)
 
 
def stream_movie_expert(history, api_key, screen_context=""):
    """Yields the reply token by token. history = [{'role','content'}, ...]."""
    turns = [m for m in history
             if m.get("content") and not m["content"].startswith("AI error")][-12:]
    while turns and turns[0]["role"] != "user":  # Gemini wants the user to start
        turns.pop(0)
    contents = [
        types.Content(role="user" if m["role"] == "user" else "model",
                      parts=[types.Part(text=m["content"][:2000])])
        for m in turns]
    system = SYSTEM_PROMPT
    if screen_context:
        system += f"\nMovies currently shown on the user's screen: {screen_context}."
 
    client = genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(
            timeout=60000, retry_options=types.HttpRetryOptions(attempts=1)))
    start, got = time.time(), False
    for chunk in client.models.generate_content_stream(
            model=MODEL, contents=contents, config=_chat_config(system)):
        if chunk.text:
            if not got:
                print(f"[gemini] first token after {time.time() - start:.1f}s", flush=True)
            got = True
            yield chunk.text
    if not got:
        raise RuntimeError("Gemini returned an empty response.")