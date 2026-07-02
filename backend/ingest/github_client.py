import os
from dotenv import load_dotenv
import requests
import json  

load_dotenv()
api_key = os.getenv("GITHUB_TOKEN")
print("Token loaded:", api_key is not None)

header = {"Authorization": f"token {api_key}"}

def extract(url, file):
    response = requests.get(url, headers=header)
    data = response.json()

    
    repos = data["items"] if isinstance(data, dict) and "items" in data else data
    for r in repos:
        if not passes_threshold(r) and not  is_false(r) and not is_true(r):
            repos.remove(r)  
    with open(f"data/raw/{file}", "w") as f:
        json.dump(repos, f, indent=2)
    
    with open(f"data/raw/{file}", "r") as f:
        return json.load(f)
    
def passes_threshold(repo):
    return (
        repo["stargazers_count"] >= 10 and
        repo["forks_count"] >= 2 and
        repo["open_issues_count"] >= 1
    )

def is_false(repo):
    return (repo["archived"] == "false" and repo["disabled"])

def is_true(repo):
    return (repo["has_issues"] == "true" and repo["has_projects"] == "true")

