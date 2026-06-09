# Repo Finder

A data engineering project that helps beginner developers find open-source
repositories matched to what they are currently learning — and ranks those
repositories from easy to hard.

> **Status:** in development · **Elective:** Data Engineering (WeThinkCode_)

---

## The problem

Most beginner developers struggle to find repositories that match the skills
they are learning. Existing "good first issue" lists surface beginner-friendly
issues but do little to match a repo to *what a specific learner is studying*,
or to convey *how hard* a repo actually is to contribute to. This project
closes that gap: a learner states what they are learning, and the platform
returns repositories that (a) actually use those skills and (b) have
approachable work available, ranked by difficulty.

---

## Architecture

The project is an ETL pipeline that lands raw data, transforms it into a
relational schema, enriches a filtered subset with an LLM, and serves the
results through an API to a front end.

```
GitHub API
    │  (extract: raw JSON)
    ▼
data/raw/*.json        ← raw landing zone (untouched API responses)
    │  (transform: flatten nested JSON, compute language %)
    ▼
PostgreSQL             ← repos, repo_languages, issues
    │  (narrow: SQL filter on language share + issue board)
    ▼
LLM analysis (Gemini)  ← runs only on the narrowed shortlist; cached
    │
    ▼
FastAPI backend        ← queries Postgres, returns ranked suggestions
    │
    ▼
React front end        ← user inputs skills, sees ranked repo cards
```

**Design principle — cheap before expensive.** The pipeline narrows the
candidate set with free, fast operations (GitHub API filters, then SQL) and
only calls the LLM on the small surviving shortlist. LLM analysis is cached per
repo so the same repo is never analysed twice.

---

## Tech stack

| Layer            | Technology              |
| ---------------- | ----------------------- |
| Ingestion / glue | Python                  |
| Database         | PostgreSQL              |
| Schema & queries | SQL                     |
| LLM analysis     | Gemini (Google AI Studio) |
| Backend API      | FastAPI                 |
| Front end        | React (JavaScript)      |

---

## Data model

Three core tables, plus one for cached LLM output. They are split (rather than
one wide table) because the source JSON contains one-to-many relationships:
one repo has many languages and many issues. Storing those in separate tables
avoids duplicating repo data on every row (normalisation).

- **repos** — one row per repository (name, owner, stars, open-issue count, etc.)
- **repo_languages** — one row per repo-language pair (bytes, percentage);
  many per repo
- **issues** — one row per open issue (title, labels, created date); many per repo
- **repo_analysis** — cached LLM output per repo (skills exercised, difficulty
  bucket, reasoning)

See `backend/db/schema.sql` for the definitions.

---

## Project structure

```
repo-finder/
├── README.md
├── .gitignore
├── .env.example              # template — variable names, no secrets
│
├── backend/
│   ├── .env                  # GITHUB_TOKEN, GEMINI_API_KEY, DB_URL (gitignored)
│   ├── requirements.txt
│   │
│   ├── db/
│   │   ├── schema.sql        # CREATE TABLE definitions
│   │   └── connection.py     # Postgres connection helper
│   │
│   ├── ingest/
│   │   ├── github_client.py  # EXTRACT: calls GitHub API, saves raw JSON
│   │   ├── transform.py      # TRANSFORM: flatten JSON, compute language %
│   │   └── load.py           # LOAD: insert rows into Postgres
│   │
│   ├── analysis/
│   │   ├── llm_client.py     # calls Gemini (with fallback)
│   │   └── analyze.py        # runs LLM on shortlist, caches to repo_analysis
│   │
│   ├── api/
│   │   └── main.py           # FastAPI app + endpoints
│   │
│   └── run_pipeline.py       # orchestrator: ingest → transform → load → analyze
│
├── data/
│   └── raw/                  # raw API JSON (gitignored)
│
└── frontend/
    ├── package.json
    ├── public/
    └── src/
        ├── App.jsx
        ├── api.js            # fetch calls to the backend
        └── components/
            ├── SearchInput.jsx
            └── RepoCard.jsx
```

---

## Setup

1. **Clone and enter the project**
2. **Create `backend/.env`** from `.env.example` and fill in your keys
   (GitHub personal access token, Gemini API key)
3. **Install Python dependencies** — see `backend/requirements.txt`
4. **Create the database schema** — run `backend/db/schema.sql` against your
   local PostgreSQL instance
5. **Run the pipeline** — `python backend/run_pipeline.py`
6. **Start the API** and **the front end** (see respective sections)

> `.env` and `data/` are gitignored. Never commit API keys.

---

## Pipeline stages

1. **Extract** — `github_client.py` pulls repo objects, language breakdowns,
   and issues from the GitHub API and saves raw JSON to `data/raw/`.
2. **Transform** — `transform.py` flattens the nested JSON, pulls out the
   fields of interest, and computes each language's percentage from its byte count.
3. **Load** — `load.py` inserts the shaped rows into Postgres.
4. **Narrow** — SQL filters repos by language share and by the presence of
   approachable open issues.
5. **Analyse** — `analyze.py` sends the narrowed shortlist (README + issues)
   to the LLM, which returns a difficulty read and the skills exercised; results
   are cached in `repo_analysis`.
6. **Serve** — `api/main.py` exposes the ranked suggestions over HTTP for the
   front end.

---

## Limitations & next steps

- Language byte counts reflect file size, not importance, so a repo can look
  skewed toward a language with large generated files.
- "good first issue" labels are a convention, not a guarantee; the LLM step
  partly compensates by reading actual issue text.
- v1 works with a small set of repos; scaling ingestion is future work.
- Resource/difficulty scoring could incorporate more signals (merge rate,
  maintainer responsiveness, docs quality).

---

## License

MIT
