# api/main.py
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
import pandas as pd

load_dotenv()
engine = create_engine(
    f"postgresql+psycopg2://postgres:{os.getenv('DB_PASSWORD')}@localhost:5432/repo_finder"
)


def get_available_languages():
    """Show what languages actually exist in the data, so the user picks a real one."""
    df = pd.read_sql(
        "SELECT language, COUNT(*) AS repos FROM repo_languages "
        "GROUP BY language ORDER BY repos DESC LIMIT 10", engine)
    return df


def find_matches(language, experience, min_pct=30):
    query = """  
        WITH repo_totals AS (
            SELECT repo_id, SUM(bytes) AS total_bytes
            FROM repo_languages GROUP BY repo_id
        )
        SELECT DISTINCT r.full_name,
               r.html_url,
               a.experience_level,
               ROUND(100.0 * l.bytes / t.total_bytes, 1) AS language_pct
        FROM repo_analysis a
        JOIN repositories r   ON r.id = a.repo_id
        JOIN repo_languages l ON l.repo_id = a.repo_id
        JOIN repo_totals t    ON t.repo_id = a.repo_id
        WHERE l.language = %(language)s
          AND a.experience_level = %(experience)s
          AND (100.0 * l.bytes / t.total_bytes) >= %(min_pct)s
        ORDER BY language_pct DESC
    """
    return pd.read_sql(query, engine, params={
        "language": language,
        "experience": experience,
        "min_pct": min_pct
    })


def main():
    print("\n=== Repo Finder ===")
    print("Find open-source repos matched to what you're learning.\n")

    print("Languages available in the dataset:")
    langs = get_available_languages()
    for _, row in langs.iterrows():
        print(f"  - {row['language']} ({row['repos']} repos)")

    language = input("\nWhich language are you learning? ").strip()

    experience = ""
    while experience not in ("beginner", "intermediate", "advanced"):
        experience = input("Your experience level (beginner/intermediate/advanced)? ").strip().lower()
        if experience not in ("beginner", "intermediate", "advanced"):
            print("  Please type: beginner, intermediate, or advanced")

    results = find_matches(language, experience)

    if results.empty:
        print(f"\nNo {experience} matches found for {language}. Try another language or level.\n")
        return

    print(f"\nFound {len(results)} matching repos:\n")
    for i, (_, row) in enumerate(results.iterrows(), 1):
        print(f"  [{i}] {row['full_name']}  ({row['language_pct']}% {language})")
        print(f"      {row['html_url']}")
        print()

    choice = input("Enter a number to open that repo's link (or press Enter to quit): ").strip()
    if choice.isdigit():
        idx = int(choice) - 1
        if 0 <= idx < len(results):
            selected = results.iloc[idx]
            print(f"\nYou selected: {selected['full_name']}")
            print(f"Link: {selected['html_url']}\n")
        else:
            print("Invalid selection.\n")


if __name__ == "__main__":
    main()