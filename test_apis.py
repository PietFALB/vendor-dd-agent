import os
import json
import requests
import pandas as pd
from dotenv import load_dotenv

load_dotenv()
os.makedirs("notes", exist_ok=True)


def save(name, data):
    with open(f"notes/{name}.json", "w") as f:
        json.dump(data, f, indent=2)


def test_gleif():
    r = requests.get(
        "https://api.gleif.org/api/v1/lei-records",
        params={"filter[fulltext]": "ING Groep", "page[size]": 3},
        timeout=15,
    )
    r.raise_for_status()
    data = r.json()
    save("gleif", data)
    print("GLEIF OK:", data["data"][0]["attributes"]["entity"]["legalName"]["name"])


def test_kvk():
    r = requests.get(
        "https://api.kvk.nl/test/api/v1/basisprofielen/68750110",
        headers={"apikey": os.environ["KVK_API_KEY"]},
        timeout=15,
    )
    r.raise_for_status()
    data = r.json()
    save("kvk", data)
    print("KvK OK:", data.get("naam"))


def test_tavily():
    from tavily import TavilyClient
    client = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])
    data = client.search("ING Groep fine", topic="news", max_results=3)
    save("tavily", data)
    print("Tavily OK:", data["results"][0]["title"])


def test_sanctions():
    for path in ["data/sanctions/targets.simple.csv", "data/sanctions/targets_simple.csv"]:
        if os.path.exists(path):
            df = pd.read_csv(path, low_memory=False)
            print("Sanctions OK:", df.shape[0], "rows, file:", path)
            return
    raise FileNotFoundError("No sanctions CSV found in data/sanctions/")


def test_openai():
    from langchain_openai import ChatOpenAI
    llm = ChatOpenAI(model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"))
    print("OpenAI OK:", llm.invoke("Say hi in 3 words").content)


def test_pinecone():
    from pinecone import Pinecone
    pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])
    print("Pinecone OK, indexes:", pc.list_indexes().names())


for test in [test_gleif, test_kvk, test_tavily, test_sanctions, test_openai, test_pinecone]:
    try:
        test()
    except Exception as e:
        print(f"{test.__name__} FAILED: {e}")
