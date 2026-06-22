import os
from dotenv import load_dotenv
import requests
import json  

load_dotenv()
api_key = os.getenv("GITHUB_TOKEN")
print("Token loaded:", api_key is not None)

header = {"Authorization": f"token {api_key}"}

def extract(url,file):
    response = requests.get(url, headers=header)
    data = response.json()
    with open(f"data/raw/{file}", "w") as f:
        json.dump(data, f, indent=2)
    
    with open(f"data/raw/{file}", "r") as f:
        data_repo = json.load(f)
    return data_repo

