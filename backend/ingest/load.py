# load.py
def load(engine, df):
    df.to_sql("repositories", engine, if_exists="replace", index=False)
    print("Loaded", len(df), "rows")
