import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

engine = create_engine(
    f"postgresql+psycopg2://postgres:{os.getenv('DB_PASSWORD')}@localhost:5432/repo_finder"
)
def create_repo_analysis_table():

    with open("db/create_repo_analysis.sql") as f:
        schema = f.read()

    with engine.begin() as conn:
        conn.execute(text(schema))

    print("repo_analysis table created")