# main.py
import streamlit as st
import pandas as pd
import requests
from requests.auth import HTTPBasicAuth
import json

st.set_page_config(layout="wide")
st.title("🧠 AI Content Gap Finder for Real Estate")
st.write("Generate high-volume article ideas not covered by Magicbricks")

# Load secrets
DFS_LOGIN = st.secrets["dataforseo"]["login"]
DFS_PASSWORD = st.secrets["dataforseo"]["password"]
GROK_API_KEY = st.secrets["grok"]["api_key"]

# Step 1: Call DataForSEO Keywords for Site
def fetch_keywords_from_site(site="housing.com"):
    url = "https://api.dataforseo.com/v3/keywords_data/google_ads/keywords_for_site/live"
    payload = {
        "target": site,
        "language_code": "en",
        "location_code": 2356  # India
    }
    response = requests.post(url, auth=HTTPBasicAuth(DFS_LOGIN, DFS_PASSWORD), json=payload)

    if response.status_code != 200:
        st.error(f"DataForSEO error {response.status_code}: {response.text}")
        return []

    result = response.json()
    try:
        if result.get("tasks") and result["tasks"][0].get("result"):
            return result["tasks"][0]["result"][0].get("items", [])
        else:
            st.error("No keyword results returned. Check if the domain has sufficient data.")
            return []
    except (KeyError, IndexError, TypeError):
        st.error("Invalid response structure from DataForSEO API.")
        return []

# Step 2: Ask Grok if keyword is article-worthy and get title
def classify_with_grok(keyword):
    prompt = f"""
You are an SEO strategist. For the keyword: '{keyword}', determine:
1. Is this keyword suitable for a blog/article? (Yes/No)
2. If Yes, suggest an engaging title.
3. Identify the intent (How-To, Listicle, FAQ, Explainer)
Respond in JSON format with keys: article_worthy, title, intent
"""
    response = requests.post(
        "https://api.grok.xai.com/v1/completions",
        headers={"Authorization": f"Bearer {GROK_API_KEY}"},
        json={"prompt": prompt, "max_tokens": 200}
    )
    if response.status_code == 200:
        try:
            parsed = json.loads(response.json()["text"].strip())
            return parsed
        except Exception as e:
            return {"article_worthy": "No", "title": "", "intent": ""}
    else:
        return {"article_worthy": "No", "title": "", "intent": ""}

# UI to trigger
if st.button("🔍 Discover Topics"):
    with st.spinner("Fetching keywords from housing.com..."):
        raw_keywords = fetch_keywords_from_site()

    if not raw_keywords:
        st.stop()

    filtered = [k for k in raw_keywords if k.get("search_volume", 0) > 100 and not any(b in k.get("keyword", "") for b in ["magicbricks", "99acres", "login", "property id"])]
    st.success(f"Filtered {len(filtered)} keywords with volume > 100")

    full_keywords = pd.DataFrame(filtered)[["keyword", "search_volume", "cpc", "competition"]].rename(columns={
        "keyword": "Keyword", "search_volume": "Search Volume", "cpc": "CPC", "competition": "Competition"
    })
    st.subheader("📊 All High-Volume Keywords")
    st.dataframe(full_keywords)

    st.subheader("🤖 Article Ideas via AI")
    records = []
    with st.spinner("Using AI to filter and enhance topics..."):
        for k in filtered[:50]:
            g = classify_with_grok(k["keyword"])
            if g["article_worthy"].lower() == "yes":
                records.append({
                    "Keyword": k["keyword"],
                    "Volume": k["search_volume"],
                    "Title Suggestion": g["title"],
                    "Intent": g["intent"]
                })

    df = pd.DataFrame(records)
    st.dataframe(df)
    st.download_button("Download CSV", df.to_csv(index=False), "topic_suggestions.csv")
