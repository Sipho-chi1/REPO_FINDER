# transform.py
import json
import pandas as pd

def transform():
    with open("data/raw/github_repodata.json", "r") as rf:
        data = json.load(rf)
    df = pd.json_normalize(data)
    columns = ["id", "name", "full_name", "description",
               "html_url", "fork", "owner.login", "owner.type"]
    df = df[columns]
    df = df.rename(columns={"owner.login": "owner_login",
                            "owner.type": "owner_type"})
    return df