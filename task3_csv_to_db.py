# ============================================================
# TASK 3 -- CSV Data Ingestion into SQLite
# ============================================================
#
# WHAT THIS SCRIPT DOES (step by step):
#   1. Creates users.csv with 10 sample rows if it does not exist.
#      (8 valid rows + 1 missing-email row + 1 bad-email row -- intentional,
#       to demonstrate validation logic during the interview.)
#   2. Opens the CSV file using csv.DictReader.
#   3. Validates every row: skips rows with empty name, empty email,
#      or an email without '@'.
#   4. Creates users.db with a 'users' table (UNIQUE on email).
#   5. Inserts valid rows using INSERT OR IGNORE parameterized queries.
#   6. Displays all records stored in the database.
#
# FILE:
#   users.csv -- created by this script if absent; can also be supplied
#   externally. Must have columns: name, email.
#
# HOW TO RUN:
#   python task3_csv_to_db.py
# ============================================================

import csv      # Built-in: read comma-separated value files row by row
import sqlite3  # Built-in: lightweight SQL database in a single file
import os       # Built-in: check whether a file path exists
import sys      # Built-in: exit cleanly on fatal errors

# Fix Unicode output on Windows terminals (which default to cp1252 encoding).
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# -- Constants ----------------------------------------------------------------
CSV_FILE = "users.csv"
DB_FILE  = "users.db"
# -----------------------------------------------------------------------------


# =============================================================================
# FUNCTION 1: create_sample_csv
# =============================================================================
def create_sample_csv(path):
    """
    PURPOSE:
        Writes a sample users.csv file so the script can be run immediately
        without any external setup. If the file already exists it is left
        untouched -- no data is overwritten.

    SAMPLE DATA -- 10 rows:
        Rows 1-8  : Valid name + properly formatted email.
        Row  9    : Valid name + EMPTY email  -> demonstrates missing-value
                    validation.
        Row  10   : Valid name + email without '@' -> demonstrates format
                    validation.

    DESIGN NOTE:
        The two invalid rows are intentional. During a technical interview
        you can point to these rows and show exactly how validation works,
        what the warning messages say, and why only 8 of 10 rows end up in
        the database.
    """
    if os.path.exists(path):
        print(f"  '{path}' already exists -- using existing file.")
        return

    rows = [
        # Header
        ["name",           "email"],
        # 8 valid rows
        ["Alice Johnson",  "alice.johnson@example.com"],
        ["Bob Smith",      "bob.smith@example.com"],
        ["Carol White",    "carol.white@example.com"],
        ["David Brown",    "david.brown@example.com"],
        ["Eva Green",      "eva.green@example.com"],
        ["Frank Miller",   "frank.miller@example.com"],
        ["Grace Lee",      "grace.lee@example.com"],
        ["Henry Davis",    "henry.davis@example.com"],
        # Row 9: missing email (empty string)
        ["Ivy Clark",      ""],
        # Row 10: invalid email format (no @ symbol)
        ["Jack Wilson",    "jackwilson-no-at-sign"],
    ]

    # newline="" is required by Python's csv docs to prevent extra blank lines
    # on Windows. encoding="utf-8" handles names with accented characters.
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(rows)

    total_data_rows = len(rows) - 1   # exclude the header row
    print(f"  Created '{path}' with {total_data_rows} data rows "
          f"(includes 2 intentionally invalid rows for validation testing).")


# =============================================================================
# FUNCTION 2: read_and_validate_csv
# =============================================================================
def read_and_validate_csv(path):
    """
    PURPOSE:
        Opens the CSV file, reads every data row using csv.DictReader,
        applies three validation rules, and returns only the clean records.

    HOW csv.DictReader WORKS:
        It treats the first row as a header and returns each subsequent row
        as a dict: {"name": "Alice Johnson", "email": "alice@..."}
        This is safer than indexing by column number because column order
        in the file does not matter.

    VALIDATION RULES (applied in order):
        1. 'name'  must not be empty after stripping whitespace.
        2. 'email' must not be empty after stripping whitespace.
        3. 'email' must contain the '@' character (minimal format check).

    DESIGN NOTE:
        row_number starts at 2 (row 1 is the header) so warning messages
        match what you see when opening the file in Excel or Notepad.

    ERROR HANDLING:
        - FileNotFoundError : path does not exist on disk
        - csv.Error         : malformed CSV (e.g. unclosed quotes)
        - UnicodeDecodeError: file is not UTF-8 encoded
    """
    print(f"\n[STEP 2] Reading and validating '{path}' ...")

    try:
        with open(path, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            # Guard: file must have at least 'name' and 'email' columns
            required = {"name", "email"}
            if not required.issubset(set(reader.fieldnames or [])):
                print(f"  ERROR: CSV must contain columns: {required}")
                print(f"         Found columns: {reader.fieldnames}")
                sys.exit(1)

            valid_records = []

            for row_number, row in enumerate(reader, start=2):
                name  = (row.get("name",  "") or "").strip()
                email = (row.get("email", "") or "").strip()

                # Rule 1 -- name must not be empty
                if not name:
                    print(f"  WARNING row {row_number}: "
                          f"'name' is empty -- row skipped.")
                    continue

                # Rule 2 -- email must not be empty
                if not email:
                    print(f"  WARNING row {row_number}: "
                          f"email is missing for '{name}' -- row skipped.")
                    continue

                # Rule 3 -- email must contain '@'
                if "@" not in email:
                    print(f"  WARNING row {row_number}: "
                          f"email '{email}' is invalid for '{name}' "
                          f"-- row skipped.")
                    continue

                valid_records.append({"name": name, "email": email})

    except FileNotFoundError:
        print(f"  ERROR: '{path}' not found. "
              f"Run the script from the assignment_1 folder.")
        sys.exit(1)
    except csv.Error as err:
        print(f"  ERROR: Failed to parse CSV -- {err}")
        sys.exit(1)
    except UnicodeDecodeError:
        print("  ERROR: File is not UTF-8 encoded. Re-save it as UTF-8.")
        sys.exit(1)

    print(f"  Read {len(valid_records)} valid records "
          f"(invalid rows were skipped with warnings above).\n")
    return valid_records


# =============================================================================
# FUNCTION 3: create_database
# =============================================================================
def create_database():
    """
    PURPOSE:
        Opens (or creates) users.db and ensures the 'users' table exists.

    SQL EXPLAINED -- CREATE TABLE IF NOT EXISTS users (...):

        id    INTEGER PRIMARY KEY AUTOINCREMENT
            Unique row number assigned automatically by SQLite.
            We never supply this value manually.

        name  TEXT NOT NULL
            Every user must have a name. NULL is rejected at the DB level.

        email TEXT NOT NULL UNIQUE
            Email must be present (NOT NULL) AND unique across all rows.
            Writing UNIQUE directly on the column is equivalent to
            adding UNIQUE(email) as a table constraint -- both work.
    """
    print(f"[STEP 3] Setting up database '{DB_FILE}' ...")

    try:
        conn   = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id    INTEGER PRIMARY KEY AUTOINCREMENT,
                name  TEXT    NOT NULL,
                email TEXT    NOT NULL UNIQUE
            )
        """)

        conn.commit()
        print(f"  Database '{DB_FILE}' ready.  Table 'users' exists.\n")
        return conn

    except sqlite3.Error as err:
        print(f"  ERROR: Cannot set up database -- {err}")
        sys.exit(1)


# =============================================================================
# FUNCTION 4: insert_users
# =============================================================================
def insert_users(conn, records):
    """
    PURPOSE:
        Inserts each validated record into the 'users' table.

    SQL EXPLAINED:
        INSERT OR IGNORE INTO users (name, email) VALUES (?, ?)

        INSERT INTO   : add a new row to the users table.
        OR IGNORE     : if the email already exists (UNIQUE violation),
                        skip the row without raising a Python exception.
        VALUES (?, ?) : parameterized placeholders -- the second argument
                        (name, email) is bound AFTER SQL parsing, preventing
                        SQL injection attacks.

    cursor.rowcount:
        1  -> row was successfully inserted
        0  -> row was skipped (duplicate email already in the table)
    """
    print(f"[STEP 4] Inserting {len(records)} records into 'users' table ...")

    cursor   = conn.cursor()
    inserted = 0
    skipped  = 0

    for rec in records:
        try:
            cursor.execute(
                "INSERT OR IGNORE INTO users (name, email) VALUES (?, ?)",
                (rec["name"], rec["email"])
            )
            if cursor.rowcount == 1:
                inserted += 1
                print(f"  + Inserted : {rec['name']:<20}  {rec['email']}")
            else:
                skipped += 1
                print(f"  ~ Skipped  : {rec['name']:<20}  (email already in DB)")

        except sqlite3.Error as err:
            print(f"  ! DB error for '{rec['name']}': {err}")

    conn.commit()
    print(f"\n  Result -- Inserted: {inserted}  |  Skipped (duplicates): {skipped}\n")


# =============================================================================
# FUNCTION 5: display_users
# =============================================================================
def display_users(conn):
    """
    PURPOSE:
        Retrieves every row from 'users' and prints a clean aligned table.

    SQL EXPLAINED:
        SELECT id, name, email FROM users ORDER BY id

        SELECT id, name, email : explicitly name the columns we want
        FROM users             : from the users table
        ORDER BY id            : ascending order (lowest id first)
                                  makes output stable and easy to verify
    """
    print("[STEP 5] Displaying all records stored in the database ...")

    cursor = conn.cursor()
    cursor.execute("SELECT id, name, email FROM users ORDER BY id")
    rows = cursor.fetchall()

    if not rows:
        print("  No records found in the database.\n")
        return

    print(f"\n  {'ID':<5}  {'Name':<22}  Email")
    print("  " + "-" * 58)

    for user_id, name, email in rows:
        print(f"  {user_id:<5}  {name:<22}  {email}")

    print("  " + "-" * 58)
    print(f"  Total records in database: {len(rows)}\n")


# =============================================================================
# MAIN
# =============================================================================
def main():
    print("=" * 60)
    print("  TASK 3 -- CSV Data Ingestion into SQLite")
    print("=" * 60)

    # Step 1 -- create sample CSV if it does not already exist
    print("\n[STEP 1] Preparing input CSV file ...")
    create_sample_csv(CSV_FILE)

    # Step 2 -- read the CSV and validate every row
    records = read_and_validate_csv(CSV_FILE)

    # Step 3 -- open/create the database
    conn = create_database()

    # Step 4 -- insert valid records
    insert_users(conn, records)

    # Step 5 -- display what is now stored
    display_users(conn)

    conn.close()
    print("  Database connection closed.")
    print("=" * 60)
    print(f"  DONE -- database saved as '{DB_FILE}'")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
