import streamlit as st
import requests
import sqlite3
import xml.etree.ElementTree as ET
from datetime import datetime
import re

EPG_URL = "https://epg.ovh/pl.xml"

# Bezpieczne pobranie klucza z secrets
try:
    TMDB_API_KEY = st.secrets["tmdb"]["api_key"]
except KeyError:
    st.error("❌ Klucz TMDb nie został ustawiony w secrets! Dodaj go w Manage App → Secrets.")
    st.stop()

CACHE_DB = "tmdb_cache.db"

############################
# DB CACHE
############################

def init_db():
    conn = sqlite3.connect(CACHE_DB)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS movies (
            title TEXT PRIMARY KEY,
            rating REAL,
            poster TEXT,
            imdb_id TEXT
        )
    """)
    conn.commit()
    conn.close()


def get_cached_movie(title):
    conn = sqlite3.connect(CACHE_DB)
    c = conn.cursor()
    c.execute("SELECT rating, poster, imdb_id FROM movies WHERE title=?", (title,))
    row = c.fetchone()
    conn.close()

    if row:
        return {
            "rating": row[0],
            "poster": row[1],
            "imdb_id": row[2]
        }
    return None


def cache_movie(title, rating, poster, imdb_id):
    conn = sqlite3.connect(CACHE_DB)
    c = conn.cursor()
    c.execute(
        "INSERT OR REPLACE INTO movies VALUES (?, ?, ?, ?)",
        (title, rating, poster, imdb_id)
    )
    conn.commit()
    conn.close()

############################
# CLEAN TITLE
############################

def clean_title(title):
    title = re.sub(r"\(.*?\)", "", title)
    title = re.sub(r"HD|Premiera|TV|\d{4}", "", title, flags=re.IGNORECASE)
    return title.strip()

############################
# TMDB
############################

def search_tmdb(title):
    cached = get_cached_movie(title.lower())
    if cached:
        return cached

    url = "https://api.themoviedb.org/3/search/movie"
    params = {
        "api_key": TMDB_API_KEY,
        "query": title,
        "language": "pl-PL"
    }

    try:
        r = requests.get(url, params=params)
        r.raise_for_status()
    except requests.RequestException:
        return None

    data = r.json()
    if not data.get("results"):
        return None

    movie = data["results"][0]
    rating = movie.get("vote_average", 0)
    poster_path = movie.get("poster_path")

    poster = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else None

    imdb_id = None
    movie_id = movie.get("id")
    if movie_id:
        try:
            ext = requests.get(
                f"https://api.themoviedb.org/3/movie/{movie_id}/external_ids",
                params={"api_key": TMDB_API_KEY}
            ).json()
            imdb_id = ext.get("imdb_id")
        except requests.RequestException:
            imdb_id = None

    cache_movie(title.lower(), rating, poster, imdb_id)

    return {
        "rating": rating,
        "poster": poster,
        "imdb_id": imdb_id
    }

############################
# EPG PARSER
############################

def parse_time(t):
    return datetime.strptime(t[:14], "%Y%m%d%H%M%S")


def load_movies_from_epg(start_hour=18):
    try:
        r = requests.get(EPG_URL)
        r.raise_for_status()
    except requests.RequestException:
        st.error("❌ Nie udało się pobrać EPG")
        return []

    root = ET.fromstring(r.content)

    today = datetime.now().date()
    evening = datetime.now().replace(hour=start_hour, minute=0, second=0)

    movies = []

    for programme in root.findall("programme"):
        title_elem = programme.find("title")
        category = programme.find("category")

        if title_elem is None:
            continue

        if category is None or "film" not in category.text.lower():
            continue

        start = parse_time(programme.attrib["start"])
        if start.date() != today or start < evening:
            continue

        channel = programme.attrib.get("channel")
        title = clean_title(title_elem.text)

        tmdb = search_tmdb(title)
        if not tmdb:
            continue

        movies.append({
            "title": title,
            "time": start.strftime("%H:%M"),
            "channel": channel,
            "rating": tmdb["rating"],
            "poster": tmdb["poster"],
            "imdb_id": tmdb["imdb_id"]
        })

    return sorted(movies, key=lambda x: x["rating"], reverse=True)

############################
# STREAMLIT UI
############################

def main():
    st.set_page_config(page_title="🎬 Filmy dziś w TV", layout="wide")

    st.title("🎬 Najlepsze filmy dziś wieczorem")

    init_db()

    st.sidebar.header("Filtry")
    min_rating = st.sidebar.slider("Minimalny rating", 0.0, 10.0, 6.5, 0.5)
    start_hour = st.sidebar.slider("Od godziny", 12, 23, 18)

    with st.spinner("Skanuję program TV..."):
        movies = load_movies_from_epg(start_hour)

    movies = [m for m in movies if m["rating"] >= min_rating]

    if not movies:
        st.warning("Brak filmów spełniających kryteria 😢")
        return

    cols = st.columns(4)

    for i, movie in enumerate(movies):
        col = cols[i % 4]
        with col:
            if movie["poster"]:
                st.image(movie["poster"])
            st.subheader(f"{movie['time']} ⭐ {movie['rating']}")
            st.write(movie["title"])
            st.caption(movie["channel"])

            if movie["imdb_id"]:
                st.markdown(f"[IMDb](https://www.imdb.com/title/{movie['imdb_id']})")

if __name__ == "__main__":
    main()
        return None

    data = r.json()
    if not data["results"]:
        return None

    movie = data["results"][0]
    rating = movie.get("vote_average", 0)
    poster_path = movie.get("poster_path")

    poster = None
    if poster_path:
        poster = f"https://image.tmdb.org/t/p/w500{poster_path}"

    imdb_id = None
    movie_id = movie.get("id")
    if movie_id:
        ext = requests.get(
            f"https://api.themoviedb.org/3/movie/{movie_id}/external_ids",
            params={"api_key": TMDB_API_KEY}
        ).json()
        imdb_id = ext.get("imdb_id")

    cache_movie(title.lower(), rating, poster, imdb_id)

    return {
        "rating": rating,
        "poster": poster,
        "imdb_id": imdb_id
    }

def parse_time(t):
    return datetime.strptime(t[:14], "%Y%m%d%H%M%S")

def load_movies_from_epg(start_hour=18):
    r = requests.get(EPG_URL)
    root = ET.fromstring(r.content)

    today = datetime.now().date()
    evening = datetime.now().replace(hour=start_hour, minute=0, second=0)

    movies = []

    for programme in root.findall("programme"):
        title_elem = programme.find("title")
        category = programme.find("category")

        if title_elem is None:
            continue

        if category is None or "film" not in category.text.lower():
            continue

        start = parse_time(programme.attrib["start"])
        if start.date() != today or start < evening:
            continue

        channel = programme.attrib.get("channel")
        title = clean_title(title_elem.text)

        tmdb = search_tmdb(title)
        if not tmdb:
            continue

        movies.append({
            "title": title,
            "time": start.strftime("%H:%M"),
            "channel": channel,
            "rating": tmdb["rating"],
            "poster": tmdb["poster"],
            "imdb_id": tmdb["imdb_id"]
        })

    return sorted(movies, key=lambda x: x["rating"], reverse=True)

def main():
    st.set_page_config(page_title="🎬 Filmy dziś w TV", layout="wide")

    st.title("🎬 Najlepsze filmy dziś wieczorem")

    init_db()

    st.sidebar.header("Filtry")
    min_rating = st.sidebar.slider("Minimalny rating", 0.0, 10.0, 6.5, 0.5)
    start_hour = st.sidebar.slider("Od godziny", 12, 23, 18)

    with st.spinner("Skanuję program TV..."):
        movies = load_movies_from_epg(start_hour)

    movies = [m for m in movies if m["rating"] >= min_rating]

    if not movies:
        st.warning("Brak filmów spełniających kryteria 😢")
        return

    cols = st.columns(4)

    for i, movie in enumerate(movies):
        col = cols[i % 4]
        with col:
            if movie["poster"]:
                st.image(movie["poster"])
            st.subheader(f"{movie['time']} ⭐ {movie['rating']}")
            st.write(movie["title"])
            st.caption(movie["channel"])

            if movie["imdb_id"]:
                st.markdown(f"[IMDb](https://www.imdb.com/title/{movie['imdb_id']})")

if __name__ == "__main__":
    main()
