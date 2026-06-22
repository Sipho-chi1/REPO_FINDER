# main.py
from sqlalchemy import create_engine
from ingest import github_client ,load,transform,narrow
import os
import json
from dotenv import load_dotenv
from analysis.analyze import run_analysis
from db.repo_analysis import create_repo_analysis_table

load_dotenv()
api_key = os.getenv("GITHUB_TOKEN")
print("Token loaded:", api_key is not None)

header = {"Authorization": f"token {api_key}"}
engine = create_engine("postgresql+psycopg2://postgres:postgres@localhost:5432/repo_finder")
url = "https://api.github.com/repositories"
def pipeline():
    # create_repo_analysis_table()
    github_client.extract(url,"github_repodata.json")
    df = transform.transform()
    load.load(engine,df)
    with open("data/raw/github_repodata.json", "r") as f:
        repos = json.load(f)
    narrow.enrich_and_build_tables(engine,repos,header)
    run_analysis(engine,"Python")
if __name__ == "__main__":
    pipeline()