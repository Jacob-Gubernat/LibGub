# search.py

import re
import pandas as pd
from pathlib import Path
import mysql.connector as mc
from rapidfuzz.distance import Levenshtein
from rapidfuzz.fuzz import token_set_ratio

DB = dict(
    host="localhost", 
    user="root", 
    password="", 
    database="libgub", 
    autocommit=True
)

ROOT = Path(__file__).resolve().parent

INPUT_CSV = ROOT / "demo" / "input_books.csv"
SAVED_CSV = ROOT / "demo" / "saved_books.csv"
MISSING_CSV = ROOT / "demo" / "missing_books.csv"

def open_db():
    global conn, cur
    conn = mc.connect(**DB)
    cur = conn.cursor(dictionary=True)

def close_db():
    global conn, cur
    try:
        cur.close()
    finally:
        conn.close()

def get_newest(books):
    best = None
    max_year = -1

    for b in books:
        year_str = (b.get("Year") or "").strip()
        if year_str.isdigit():
            yr = int(year_str)
        else:
            yr = -1

        if best is None or yr > max_year:
            best = b
            max_year = yr

    return best

def title_match(t1, t2):
    T1 = str(t1).lower()
    T2 = str(t2).lower()

    if SHORT:
        T1 = T1.split(":")[0]
        T2 = T2.split(":")[0]

    return token_set_ratio(T1, T2) >= 80

def author_match(a1, a2):
    A1 = normalize_authors(a1)
    A2 = normalize_authors(a2)

    for x in A1:
        for y in A2:
            if Levenshtein.normalized_similarity(x, y) * 100 >= 80:
                return True
    return False

def normalize_authors(val):
    if val is None or (isinstance(val, float) and pd.isna(val)):
        text = ""
    elif isinstance(val, (list, tuple, set)):
        text = " ".join(map(str, val))
    else:
        text = str(val)

    text = re.sub(r'[\[\]"\\\']+', "", text)
    tokens = re.split(r"[,\s;/\.\-]+", text.lower())
    tokens = [t for t in tokens if len(t) > 2 and not re.fullmatch(r"[a-z]{1,2}", t)]

    return set(tokens)

def fetch_by_title(title):
    if SHORT:
        title = title.split(":")[0]
    phrase = build_title_query(title)

    cur.execute("""
        SELECT ID, Title, Author, Year, Edition, MD5, Filesize, Extension, Identifier
          FROM libgub
         WHERE MATCH(Title) AGAINST (%s IN BOOLEAN MODE)
           AND Extension = 'pdf'
         ORDER BY Year IS NULL, Year DESC
         LIMIT 1000;
    """, (phrase,))

    return cur.fetchall()

def build_title_query(title):
    toks = re.findall(r"\w{3,}", title.lower())
    if toks:
        return " ".join(f"+{t}" for t in toks)

    safe = title.replace('"', ' ')
    return f'"{safe}"'

def fetch_by_author(author):
    phrase = build_author_query(author)
    if not phrase:
        return []

    cur.execute("""
        SELECT ID, Title, Author, Year, Edition, MD5, Filesize, Extension, Identifier
          FROM libgub
         WHERE MATCH(Author) AGAINST (%s IN BOOLEAN MODE)
           AND Extension = 'pdf'
         ORDER BY Year IS NULL, Year DESC
         LIMIT 1000;
    """, (phrase,))

    return cur.fetchall()

def build_author_query(author):
    toks = normalize_authors(author)
    return " ".join(f"+{t}" for t in toks) if toks else ""

def search_book(title, authors):
    global SHORT
    SHORT = False

    results = fetch_by_title(title)
    matches = filter_results(title, authors, results)
    if len(matches) != 0:
        return get_newest(matches)

    for author in authors:
        results = fetch_by_author(author)
        matches = filter_results(title, authors, results)
        if len(matches) != 0:
            return get_newest(matches)

    SHORT = True

    results = fetch_by_title(title)
    matches = filter_results(title, authors, results)
    if len(matches) != 0:
        return get_newest(matches)

    for author in authors:
        results = fetch_by_author(author)
        matches = filter_results(title, authors, results)
        if len(matches) != 0:
            return get_newest(matches)

    return None

def filter_results(title, author, rows):
    books = []
    for r in rows:
        if title_match(title, r["Title"]) and author_match(author, r["Author"]):
            books.append(r)
    return books

def main():
    df = pd.read_csv(INPUT_CSV)

    saved = []
    missing = []

    id = df["id"].tolist()
    doi = df["doi"].tolist()
    type = df["type"].tolist()
    title = df["title"].tolist()
    author = df["author"].tolist()

    for n in range(len(id)):
        if type[n] not in ("book", "book-chapter"):
            continue

        best = search_book(title[n], author[n])

        if best is not None:
            best["id"] = id[n]
            saved.append(best)
        else:
            row = {
                "id": id[n],
                "doi": doi[n],
                "type": type[n],
                "title": title[n],
                "author": author[n],
            }
            missing.append(row)

    print(f"saved:   {len(saved):,}")
    print(f"missing: {len(missing):,}")

    pd.DataFrame(saved).to_csv(SAVED_CSV, index=False)
    pd.DataFrame(missing).to_csv(MISSING_CSV, index=False)