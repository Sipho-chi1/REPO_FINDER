# scripts/live_smoke_test.py
"""
Manual smoke test -- run this by hand (python scripts/live_smoke_test.py
from backend/) to sanity-check your actual Postgres DB and Gemini API key.

This is NOT a pytest test: it hits real services and needs a live DB and
a valid GEMINI_API_KEY/GITHUB_TOKEN in .env, so it does not belong in the
automated suite (which mocks all of that in tests/test_run_pipeline.py).
"""
import os
import json
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

# ─────────────────────────────────────────────
# TEST 1: Environment variables loaded
# ─────────────────────────────────────────────
print("\n=== TEST 1: Environment ===")
github_token = os.getenv("GITHUB_TOKEN")
gemini_key = os.getenv("GEMINI_API_KEY")
db_password = os.getenv("DB_PASSWORD")  # adjust to your var name
print("GITHUB_TOKEN loaded:", github_token is not None)
print("GEMINI_API_KEY loaded:", gemini_key is not None)
print("DB_PASSWORD loaded:", db_password is not None)

# ─────────────────────────────────────────────
# TEST 2: Database connection
# ─────────────────────────────────────────────
print("\n=== TEST 2: Database connection ===")
try:
    engine = create_engine(
        f"postgresql+psycopg2://postgres:{db_password}@localhost:5432/repo_finder")
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        print("Connection OK:", result.scalar() == 1)
except Exception as e:
    print("DB connection FAILED:", e)

# ─────────────────────────────────────────────
# TEST 3: Tables exist and have data
# ─────────────────────────────────────────────
print("\n=== TEST 3: Tables and row counts ===")
for table in ["repositories", "repo_languages", "repo_issues", "repo_analysis"]:
    try:
        with engine.connect() as conn:
            count = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
        print(f"  {table}: {count} rows")
    except Exception as e:
        print(f"  {table}: MISSING or error — {e}")

# ─────────────────────────────────────────────
# TEST 4: Gemini connection (basic call)
# ─────────────────────────────────────────────
print("\n=== TEST 4: Gemini connection ===")
try:
    from analysis.llm_client import ask_gemini
    reply = ask_gemini("Reply with exactly the word: OK")
    print("Gemini replied:", reply.strip()[:50])
except Exception as e:
    print("Gemini FAILED:", e)

# ─────────────────────────────────────────────
# TEST 5: Gemini returns parseable JSON
# ─────────────────────────────────────────────
print("\n=== TEST 5: Gemini JSON output ===")
try:
    from analysis.analyze import analyze_issue   # adjust import to your file
    prompt = analyze_issue(
        title="Fix typo in README",
        body="There is a spelling mistake in the installation section.",
        labels="good first issue,documentation",
        language="Python")
    raw = ask_gemini(prompt)
    cleaned = raw.replace("```json", "").replace("```", "").strip()
    result = json.loads(cleaned)
    print("Parsed JSON OK:", result)
    print("Has 'level' key:", "level" in result)
except Exception as e:
    print("JSON parse FAILED:", e)
    print("Raw response was:", raw[:200] if 'raw' in dir() else "(no response)")

# ─────────────────────────────────────────────
# TEST 6: The narrow query returns issues
# ─────────────────────────────────────────────
print("\n=== TEST 6: Narrow query ===")
try:
    from analysis.analyze import get_issues_to_analyze   # adjust import
    issues = get_issues_to_analyze(engine, "Python")
    print(f"  Narrow query returned {len(issues)} issues")
    if len(issues) > 0:
        print("  Sample:", issues.iloc[0]["title"][:60])
except Exception as e:
    print("Narrow query FAILED:", e)

print("\n=== Tests complete ===")