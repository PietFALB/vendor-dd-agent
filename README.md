# Vendor Due-Diligence Agent

LangGraph agent that checks a company against public registers, sanctions data and news, and writes a vendor due-diligence report with a risk rating.

## Setup

Mac / Linux:

```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Windows:

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and fill in your API keys.

Download the sanctions data (simplified CSV) from https://www.opensanctions.org/datasets/sanctions/ and save it as `data/sanctions/targets.simple.csv`.

## Check the APIs

```
python test_apis.py
```
