CREATE TABLE IF NOT EXISTS repo_analysis (
    issue_number     INTEGER,
    repo_id          BIGINT,
    experience_level TEXT,
    reasoning        TEXT,
    analyzed_at      TIMESTAMP DEFAULT NOW()
);

 