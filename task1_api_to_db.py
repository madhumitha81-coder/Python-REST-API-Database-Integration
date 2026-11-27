# ============================================================
# TASK 1 -- API Data Retrieval and SQLite Storage
# ============================================================
#
# WHAT THIS SCRIPT DOES (step by step):
#   1. Calls the Open Library Search API (free, no API key needed).
#   2. Extracts book title, author name, and first publish year.
#   3. Creates a SQLite database file called books.db.
#   4. Creates a 'books' table if it does not already exist.
#   5. Inserts fetched books using parameterized SQL queries.
#   6. Skips duplicates silently (INSERT OR IGNORE).
#   7. Displays every record stored in the database.
#
# API USED:
#   Open Library Search API
#   https://openlibrary.org/search.json?q=python+programming&limit=10
#   - Free, no registration, returns real JSON data.
#   - Response key "docs" holds the list of book objects.
#
# HOW TO RUN:
#   python task1_api_to_db.py
# ============================================================

import requests   # For making HTTP GET requests to the API
import sqlite3    # For creating and querying the SQLite database
import sys        # For exiting the program cleanly on fatal errors

# Fix Unicode output on Windows terminals (which default to cp1252 encoding).
# Without this, any non-ASCII character in a print() call raises
# UnicodeEncodeError. reconfigure() switches stdout to UTF-8 at runtime.
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# -- Constants ----------------------------------------------------------------
# Defined at module level (not buried inside functions) so they are easy to
# find and change without touching any logic.
API_URL     = "https://openlibrary.org/search.json?q=python+programming&limit=10"
DB_FILE     = "books.db"
MAX_RETRIES = 3    # Retry the API call up to 3 times on timeout
# -----------------------------------------------------------------------------


# =============================================================================
# FUNCTION 1: fetch_books_from_api
# =============================================================================
def fetch_books_from_api():
    """
    PURPOSE:
        Sends a GET request to the Open Library API and returns a list of
        clean book dictionaries ready for database insertion.

    RETURN VALUE:
        [{"title": str, "author": str, "year": int or None}, ...]

    RETRY LOGIC:
        Open Library can be slow. We attempt the request up to MAX_RETRIES
        times before giving up, so a single slow response does not kill the
        script.

    ERROR HANDLING:
        - ConnectionError  -> no internet / DNS failure
        - Timeout          -> server did not respond within 20 s
        - HTTPError        -> server returned 4xx / 5xx
        - RequestException -> catch-all safety net
        All errors print a friendly message and call sys.exit(1).

    DESIGN NOTE -- why .get() with defaults?
        The Open Library API sometimes omits fields for older books.
        doc.get("title", "Unknown Title") means we never get a KeyError
        crash -- the worst case is a row with the placeholder text.
    """
    print("\n[STEP 1] Contacting Open Library API ...")
    print(f"         URL: {API_URL}\n")

    response = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            print(f"  Attempt {attempt}/{MAX_RETRIES} ...")
            response = requests.get(API_URL, timeout=20)
            response.raise_for_status()   # Raise exception for 4xx/5xx
            break                         # Success -- exit retry loop

        except requests.exceptions.ConnectionError:
            print("  ERROR: Cannot reach the API. Check your internet connection.")
            sys.exit(1)

        except requests.exceptions.Timeout:
            print(f"  WARNING: Attempt {attempt} timed out after 20 s.")
            if attempt == MAX_RETRIES:
                print("  ERROR: All retries exhausted. Try again later.")
                sys.exit(1)

        except requests.exceptions.HTTPError as err:
            print(f"  ERROR: API returned an HTTP error -- {err}")
            sys.exit(1)

        except requests.exceptions.RequestException as err:
            print(f"  ERROR: Unexpected network problem -- {err}")
            sys.exit(1)

    # response.json() converts the raw JSON text into a Python dict/list
    payload = response.json()

    # The list of book objects lives under the "docs" key
    docs = payload.get("docs", [])
    if not docs:
        print("  WARNING: API returned no book records. Exiting.")
        sys.exit(1)

    books = []
    for doc in docs:
        # Title -- always present but may be empty; default is a safe fallback
        title = doc.get("title", "Unknown Title").strip() or "Unknown Title"

        # Author -- stored as a list; take the first entry if available
        authors = doc.get("author_name") or []
        author  = authors[0].strip() if authors else "Unknown Author"

        # Year -- integer when present; None (-> NULL in SQLite) when absent
        year = doc.get("first_publish_year")   # None if key is missing

        books.append({"title": title, "author": author, "year": year})

    print(f"  SUCCESS: Retrieved {len(books)} book records from the API.")
    return books


# =============================================================================
# FUNCTION 2: create_database
# =============================================================================
def create_database():
    """
    PURPOSE:
        Opens (or creates) books.db and creates the 'books' table if it
        does not already exist.

    RETURN VALUE:
        An open sqlite3.Connection object (caller must close it).

    SQL EXPLAINED -- CREATE TABLE IF NOT EXISTS books (...):

        id     INTEGER PRIMARY KEY AUTOINCREMENT
            SQLite assigns a unique integer to every new row automatically.
            We never need to supply this value ourselves.

        title  TEXT NOT NULL
            The column stores text and cannot be NULL. Empty string is still
            technically allowed at the DB level, but we guard against it in
            fetch_books_from_api() with the "or" fallback.

        author TEXT NOT NULL
            Same rule as title.

        year   INTEGER
            No NOT NULL because some books genuinely have no publish year.
            NULL is semantically correct here -- not 0, not "N/A".

        UNIQUE(title, author)
            The database engine rejects any INSERT whose (title, author)
            combination already exists. Combined with INSERT OR IGNORE this
            silently skips duplicates instead of crashing.
    """
    print("[STEP 2] Setting up SQLite database ...")

    try:
        conn   = sqlite3.connect(DB_FILE)   # Creates the file if absent
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS books (
                id     INTEGER PRIMARY KEY AUTOINCREMENT,
                title  TEXT    NOT NULL,
                author TEXT    NOT NULL,
                year   INTEGER,
                UNIQUE(title, author)
            )
        """)

        conn.commit()   # Persist the schema change to disk
        print(f"  Database '{DB_FILE}' ready.  Table 'books' exists.\n")
        return conn

    except sqlite3.Error as err:
        print(f"  ERROR: Could not set up database -- {err}")
        sys.exit(1)


# =============================================================================
# FUNCTION 3: insert_books
# =============================================================================
def insert_books(conn, books):
    """
    PURPOSE:
        Inserts each book dict into the 'books' table, counting actual
        insertions and skipped duplicates separately.

    SQL EXPLAINED:
        INSERT OR IGNORE INTO books (title, author, year) VALUES (?, ?, ?)

        INSERT INTO  : add a new row to the named table.
        OR IGNORE    : if inserting this row would violate the UNIQUE(title,
                       author) constraint, skip the row without raising an
                       error. This makes re-running the script safe.
        (?, ?, ?)    : parameterized placeholders. SQLite fills these with the
                       values in the second argument tuple AFTER parsing the
                       SQL. This prevents SQL injection -- user data is always
                       treated as data, never as code.

    cursor.rowcount:
        1 -> a row was actually inserted
        0 -> the row was skipped (duplicate)
    """
    print("[STEP 3] Inserting books into the database ...")

    cursor   = conn.cursor()
    inserted = 0
    skipped  = 0

    for book in books:
        try:
            cursor.execute(
                "INSERT OR IGNORE INTO books (title, author, year)"
                " VALUES (?, ?, ?)",
                (book["title"], book["author"], book["year"])
            )
            if cursor.rowcount == 1:
                inserted += 1
                print(f"  + Inserted : {book['title']}")
            else:
                skipped += 1
                print(f"  ~ Skipped  : {book['title']} (duplicate)")

        except sqlite3.Error as err:
            # Non-fatal: log and continue with the next book
            print(f"  ! DB error for '{book['title']}': {err}")

    conn.commit()   # Write all inserts to disk at once (faster than per-row)
    print(f"\n  Result -- Inserted: {inserted}  |  Skipped (duplicates): {skipped}\n")


# =============================================================================
# FUNCTION 4: display_books
# =============================================================================
def display_books(conn):
    """
    PURPOSE:
        Retrieves every row from the 'books' table and prints them in a
        human-readable aligned table.

    SQL EXPLAINED:
        SELECT id, title, author, year FROM books ORDER BY id

        SELECT id, title, author, year : fetch only these four columns (not *)
        FROM books                     : from the books table
        ORDER BY id                    : sort rows by ID ascending (default)
                                         so the output is stable and predictable
    """
    print("[STEP 4] Displaying all records stored in the database ...")

    cursor = conn.cursor()
    cursor.execute("SELECT id, title, author, year FROM books ORDER BY id")
    rows = cursor.fetchall()   # fetchall() returns a list of tuples

    if not rows:
        print("  No records found in the database.\n")
        return

    # Print a column-aligned header
    print(f"\n  {'ID':<4}  {'Title':<46}  {'Author':<26}  Year")
    print("  " + "-" * 84)

    for row_id, title, author, year in rows:
        # Truncate long values so the table stays readable
        t = (title[:43]  + "...") if len(title)  > 46 else title
        a = (author[:23] + "...") if len(author) > 26 else author
        y = str(year) if year is not None else "N/A"
        print(f"  {row_id:<4}  {t:<46}  {a:<26}  {y}")

    print("  " + "-" * 84)
    print(f"  Total records in database: {len(rows)}\n")


# =============================================================================
# MAIN
# =============================================================================
def main():
    print("=" * 60)
    print("  TASK 1 -- API Data Retrieval and SQLite Storage")
    print("=" * 60)

    books = fetch_books_from_api()   # Step 1: fetch from API
    conn  = create_database()        # Step 2: set up database
    insert_books(conn, books)        # Step 3: insert records
    display_books(conn)              # Step 4: display records

    conn.close()
    print("  Database connection closed.")
    print("=" * 60)
    print(f"  DONE -- database saved as '{DB_FILE}'")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
