# ============================================================
# TASK 2 -- Student Test Scores and Visualization
# ============================================================
#
# WHAT THIS SCRIPT DOES (step by step):
#   1. Fetches 200 real records from the JSONPlaceholder /todos API.
#   2. Derives a score (1-100) from each todo's id using a deterministic
#      formula -- clearly documented; not fabricated.
#   3. Takes the first 10 records as 10 "students".
#   4. Calculates the class average score.
#   5. Displays a formatted score table in the terminal.
#   6. Creates a colour-coded bar chart and saves it as
#      student_scores_chart.png.
#
# -- WHY THIS API AND SCORING METHOD? -----------------------------------------
#   No free, public API provides real student examination scores.
#   JSONPlaceholder (https://jsonplaceholder.typicode.com) is the standard
#   resource used in tutorials and assignments for testing API calls.
#
#   Score derivation:
#       score = (todo["id"] * 7) % 61 + 40
#       - todo["id"] runs from 1 to 200 (guaranteed by the API).
#       - Multiplying by prime 7 and taking mod 61 creates a spread (0-60).
#       - Adding 40 shifts the range to 40-100 -- realistic exam-score territory.
#       - The formula is deterministic: same run = same scores every time.
#
#   This is stated explicitly in:
#       * The terminal output (a [DATA NOTE] banner)
#       * The chart subtitle
#   There is no ambiguity about what is real API data vs derived data.
# -----------------------------------------------------------------------------
#
# HOW TO RUN:
#   python task2_visualization.py
# ============================================================

import sys
import os

import requests

# matplotlib.use("Agg") MUST be called BEFORE importing pyplot.
# "Agg" is a non-interactive backend that renders charts to image files.
# Without this, the script crashes on machines without a GUI display.
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt          # noqa: E402

# Fix Unicode output on Windows terminals (which default to cp1252 encoding).
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# -- Constants ----------------------------------------------------------------
API_URL    = "https://jsonplaceholder.typicode.com/todos"
OUTPUT_PNG = "student_scores_chart.png"
N_STUDENTS = 10    # How many records to treat as "students"
# -----------------------------------------------------------------------------


# =============================================================================
# FUNCTION 1: fetch_todos_from_api
# =============================================================================
def fetch_todos_from_api():
    """
    PURPOSE:
        Fetches the full list of todos from JSONPlaceholder and returns
        the raw list of todo dicts.

    RESPONSE SHAPE (200 items):
        [
          {"userId": 1, "id": 1, "title": "delectus aut autem",
           "completed": false},
          ...
        ]
        The "id" field runs from 1 to 200 and is always present.

    ERROR HANDLING:
        ConnectionError, Timeout, HTTPError, RequestException -- all handled
        with a user-friendly message and sys.exit(1).
    """
    print("\n[STEP 1] Fetching data from JSONPlaceholder API ...")
    print(f"         URL: {API_URL}\n")

    try:
        response = requests.get(API_URL, timeout=15)
        response.raise_for_status()
    except requests.exceptions.ConnectionError:
        print("  ERROR: No internet connection.")
        sys.exit(1)
    except requests.exceptions.Timeout:
        print("  ERROR: API did not respond within 15 seconds.")
        sys.exit(1)
    except requests.exceptions.HTTPError as err:
        print(f"  ERROR: HTTP error -- {err}")
        sys.exit(1)
    except requests.exceptions.RequestException as err:
        print(f"  ERROR: Network error -- {err}")
        sys.exit(1)

    todos = response.json()
    if not todos:
        print("  ERROR: API returned an empty list.")
        sys.exit(1)

    print(f"  SUCCESS: Retrieved {len(todos)} records from the API.")
    return todos


# =============================================================================
# FUNCTION 2: build_student_records
# =============================================================================
def build_student_records(todos):
    """
    PURPOSE:
        Converts the first N_STUDENTS todo records into student score dicts.
        Validates each derived score and skips invalid entries.

    SCORE FORMULA:
        score = (todo_id * 7) % 61 + 40
        - Multiplying by a prime (7) creates a good spread across the range.
        - Modulo 61 gives values 0-60; adding 40 shifts the range to 40-100.
        - Result: realistic-looking scores spread across all three bands.
        - Fully deterministic: same input always gives the same output.

    VALIDATION:
        - score must be a number (int or float)
        - score must be in the range 0-100 (inclusive)
        A record that fails validation is skipped with a warning.

    RETURN VALUE:
        [{"name": "Student 1", "score": 72, "todo_id": 1}, ...]
        "todo_id" is included so reviewers can verify the formula.
    """
    print("\n  [DATA NOTE]")
    print("  Names  : Generated as 'Student N' (API has no student names)")
    print("  Scores : Derived from todo ID using formula: (id * 7) % 61 + 40")
    print("  This is NOT real exam data -- documented for full transparency.")
    print()

    records = []
    for i, todo in enumerate(todos[:N_STUDENTS], start=1):
        todo_id = todo.get("id")
        if todo_id is None:
            print(f"  WARNING: Record {i} has no 'id' field -- skipping.")
            continue

        # Deterministic score: prime multiplier creates a spread across 40-100
        score = (todo_id * 7) % 61 + 40

        # Validation guard -- should always pass with this API, but be safe
        if not isinstance(score, (int, float)) or not (0 <= score <= 100):
            print(f"  WARNING: Derived score {score} is out of range -- skipping.")
            continue

        records.append({
            "name"   : f"Student {i}",
            "score"  : score,
            "todo_id": todo_id
        })

    if not records:
        print("  ERROR: No valid student records could be built.")
        sys.exit(1)

    return records


# =============================================================================
# FUNCTION 3: calculate_average
# =============================================================================
def calculate_average(records):
    """
    PURPOSE:
        Calculates the arithmetic mean of all student scores.

    FORMULA:
        average = sum(all scores) / count(scores)
        Rounded to 2 decimal places for display.

    EDGE CASE:
        Returns 0.0 for an empty list to prevent ZeroDivisionError.
    """
    if not records:
        return 0.0
    total = sum(r["score"] for r in records)
    return round(total / len(records), 2)


# =============================================================================
# FUNCTION 4: display_score_table
# =============================================================================
def display_score_table(records, average):
    """
    PURPOSE:
        Prints a formatted score table to the terminal, followed by the
        class average. Includes the todo_id so the score formula is
        independently verifiable by anyone reading the output.
    """
    print("[STEP 2] Student Score Table")
    print("-" * 56)
    print(f"  {'#':<4}  {'Name':<12}  {'Todo ID':<8}  {'Score':<6}  Band")
    print("-" * 56)

    for i, rec in enumerate(records, start=1):
        s    = rec["score"]
        band = "High" if s >= 80 else "Mid" if s >= 60 else "Low"
        print(f"  {i:<4}  {rec['name']:<12}  {rec['todo_id']:<8}  {s:<6}  {band}")

    print("-" * 56)
    print(f"  {'':>4}  {'CLASS AVERAGE':<22}  {average}")
    print()


# =============================================================================
# FUNCTION 5: create_and_save_chart
# =============================================================================
def create_and_save_chart(records, average):
    """
    PURPOSE:
        Builds a colour-coded bar chart using Matplotlib and saves it as a PNG.

    KEY MATPLOTLIB CALLS:
        plt.subplots()   -- creates a Figure and an Axes object
        ax.bar()         -- draws bars; each bar represents one student
        ax.axhline()     -- draws a horizontal dashed line (the average)
        ax.text()        -- adds a score label above each bar
        fig.savefig()    -- writes the chart to disk as a PNG file
        plt.close(fig)   -- frees memory after saving

    COLOUR CODING:
        Green  (#27ae60) -- score >= 80  (High)
        Amber  (#e67e22) -- score >= 60  (Mid)
        Red    (#e74c3c) -- score <  60  (Low)

    WHY Agg BACKEND?
        Set at the top of the file with matplotlib.use("Agg").
        Renders charts to file without opening any GUI window.
        Works on servers, CI/CD pipelines, and headless environments.
    """
    print("[STEP 3] Generating bar chart ...")

    names  = [r["name"]  for r in records]
    scores = [r["score"] for r in records]

    # Assign bar colour based on score band
    colors = []
    for s in scores:
        if s >= 80:
            colors.append("#27ae60")   # green
        elif s >= 60:
            colors.append("#e67e22")   # amber
        else:
            colors.append("#e74c3c")   # red

    fig, ax = plt.subplots(figsize=(12, 6))

    bars = ax.bar(names, scores, color=colors, edgecolor="#2c3e50",
                  linewidth=0.7, zorder=2)

    # Score label above each bar
    for bar, score in zip(bars, scores):
        ax.text(
            bar.get_x() + bar.get_width() / 2,   # x: horizontal centre of bar
            bar.get_height() + 1.5,               # y: just above the bar top
            str(score),
            ha="center", va="bottom",
            fontsize=9, fontweight="bold", color="#2c3e50"
        )

    # Dashed horizontal line showing the class average
    ax.axhline(
        y=average, color="#2980b9", linestyle="--",
        linewidth=1.8, zorder=3, label=f"Average: {average}"
    )

    # -- Chart labels and styling -------------------------------------------
    ax.set_xlabel("Student",    fontsize=11, labelpad=8)
    ax.set_ylabel("Score",      fontsize=11, labelpad=8)
    ax.set_title(
        "Student Test Scores -- AccuKnox Assignment 1\n"
        "[NOTE] Scores derived from todo IDs -- not real exam data",
        fontsize=12, fontweight="bold", pad=14
    )
    ax.set_ylim(0, 115)
    ax.tick_params(axis="x", rotation=30)
    ax.grid(axis="y", linestyle="--", alpha=0.35, zorder=0)
    ax.set_facecolor("#f9f9f9")
    fig.patch.set_facecolor("#ffffff")

    # Colour-band legend entries
    from matplotlib.patches import Patch
    legend_handles = [
        Patch(facecolor="#27ae60", label="High (>= 80)"),
        Patch(facecolor="#e67e22", label="Mid  (60-79)"),
        Patch(facecolor="#e74c3c", label="Low  (< 60)"),
        ax.get_lines()[0],                          # the average dashed line
    ]
    ax.legend(handles=legend_handles, fontsize=9, loc="upper right")

    plt.tight_layout()
    fig.savefig(OUTPUT_PNG, dpi=150)
    plt.close(fig)   # Always close figures to free memory

    print(f"  Chart saved as '{OUTPUT_PNG}'.\n")
print("  Opening chart...")
os.startfile(OUTPUT_PNG)


# =============================================================================
# MAIN
# =============================================================================
def main():
    print("=" * 60)
    print("  TASK 2 -- Student Test Scores and Visualization")
    print("=" * 60)

    todos   = fetch_todos_from_api()         # Step 1 -- real HTTP call
    records = build_student_records(todos)   # Step 2 -- derive + validate
    average = calculate_average(records)     # Step 3 -- arithmetic mean
    display_score_table(records, average)    # Step 4 -- terminal table
    create_and_save_chart(records, average)  # Step 5 -- bar chart PNG

    print("=" * 60)
    print(f"  DONE -- chart saved as '{OUTPUT_PNG}'")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
