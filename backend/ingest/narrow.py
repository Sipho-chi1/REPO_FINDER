import time
import requests
import pandas as pd


def fetch(url, header, retries=3):
    """Authenticated GET returning JSON.
    Retries on connection errors, pauses on rate limits, returns None on failure."""
    for attempt in range(retries):
        try:
            r = requests.get(url, headers=header, timeout=10)

            if r.status_code == 200:
                return r.json()

            if r.status_code == 403:          # rate limited
                print(f"  Rate limited on {url} — pausing 10s")
                time.sleep(10)
                continue

            print(f"  Error {r.status_code} for {url}")
            return None

        except requests.exceptions.RequestException as e:
            print(f"  Connection error (attempt {attempt + 1}/{retries}): {e}")
            time.sleep(2)

    print(f"  Gave up on {url} after {retries} attempts")
    return None


def enrich_and_build_tables(engine, repos, header):
    # 1. Cheap filter first — uses fields already present, no API calls
    candidates = [r for r in repos if not r["fork"] and r["description"]]
    print(f"{len(candidates)} candidates after cheap filter (from {len(repos)})")

    language_rows = []
    issue_rows = []

    # 2. Expensive enrichment — only on survivors, paced and error-tolerant
    for i, repo in enumerate(candidates, 1):
        repo_id = repo["id"]
        print(f"[{i}/{len(candidates)}] enriching {repo.get('full_name', repo_id)}")

        # --- languages ---
        langs = fetch(repo["languages_url"], header)
        if langs:
            for language, num_bytes in langs.items():
                language_rows.append({
                    "repo_id": repo_id,
                    "language": language,
                    "bytes": num_bytes,
                })

        # --- issues ---
        issues_url = repo["issues_url"].replace("{/number}", "")
        issues = fetch(issues_url, header)
        if issues:
            for issue in issues:
                if "pull_request" in issue:   # skip PRs — GitHub returns them here
                    continue
                issue_rows.append({
                    "repo_id": repo_id,
                    "issue_number": issue["number"],
                    "title": issue["title"],
                    "labels": ",".join(l["name"] for l in issue["labels"]),
                    "state": issue["state"],
                })

        time.sleep(0.5)   # gentle pacing so we don't hammer GitHub

    # 3. Load both tables (guard against empty results)
    if language_rows:
        pd.DataFrame(language_rows).to_sql("repo_languages", engine,
                                           if_exists="replace", index=False)
    if issue_rows:
        pd.DataFrame(issue_rows).to_sql("repo_issues", engine,
                                        if_exists="replace", index=False)

    print(f"Loaded {len(language_rows)} language rows, {len(issue_rows)} issue rows")


