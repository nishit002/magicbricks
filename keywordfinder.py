import streamlit as st
import pandas as pd
import requests
from requests.auth import HTTPBasicAuth
import json

st.set_page_config(layout="wide")
st.title("🧠 AI Content Gap Finder for Real Estate")
st.write("Enter a Magicbricks URL to discover untapped content opportunities.")

# Load secrets
DFS_LOGIN = st.secrets["dataforseo"]["login"]
DFS_PASSWORD = st.secrets["dataforseo"]["password"]
GROK_API_KEY = st.secrets["grok"]["api_key"]

# Step 1: Fetch keywords for provided Magicbricks page
def fetch_keywords_for_url(url):
    endpoint = "https://api.dataforseo.com/v3/keywords_data/google_ads/keywords_for_url/live"
    payload = {
        "target": url,
        "language_code": "en",
        "location_code": 2356  # India
    }
    response = requests.post(endpoint, auth=HTTPBasicAuth(DFS_LOGIN, DFS_PASSWORD), json=payload)

    if response.status_code != 200:
        st.error(f"Failed to fetch keywords from Magicbricks URL: {response.status_code}")
        return []

    result = response.json()
    try:
        return result["tasks"][0]["result"][0]["items"]
    except (KeyError, IndexError):
        return []

# Step 2: Get keyword expansions from DataForSEO for each keyword
def get_keyword_expansions(keywords):
    endpoint = "https://api.dataforseo.com/v3/keywords_data/google_ads/keywords_for_keywords/live"
    expanded = []
    for k in keywords:
        payload = {
            "keywords": [k],
            "language_code": "en",
            "location_code": 2356
        }
        resp = requests.post(endpoint, auth=HTTPBasicAuth(DFS_LOGIN, DFS_PASSWORD), json=payload)
        if resp.status_code == 200:
            try:
                items = resp.json()["tasks"][0]["result"][0]["items"]
                expanded.extend(items)
            except (KeyError, IndexError):
                continue
    return expanded

# Step 3: Ask Grok if keyword is article-worthy and get title
def classify_with_grok(keyword):
    prompt = f"""
You are an SEO strategist. For the keyword: '{keyword}', determine:
1. Is this keyword suitable for a blog/article? (Yes/No)
2. If Yes, suggest an engaging title.
3. Identify the intent (How-To, Listicle, FAQ, Explainer)
4. Suggest 2 closely related content topics.
Respond in JSON format with keys: article_worthy, title, intent, related_topics
"""
    response = requests.post(
        "https://api.grok.xai.com/v1/completions",
        headers={"Authorization": f"Bearer {GROK_API_KEY}"},
        json={"prompt": prompt, "max_tokens": 300}
    )
    if response.status_code == 200:
        try:
            data = response.json()
            return json.loads(data["choices"][0]["text"].strip()) if "choices" in data else {"article_worthy": "No", "title": "", "intent": "", "related_topics": []}
        except (KeyError, json.JSONDecodeError):
            return {"article_worthy": "No", "title": "", "intent": "", "related_topics": []}
    return {"article_worthy": "No", "title": "", "intent": "", "related_topics": []}

# UI section
url_input = st.text_input("🔗 Enter a Magicbricks URL to analyze:")

if url_input and st.button("Discover Topics"):
    with st.spinner("🔍 Fetching keywords from Magicbricks page..."):
        mb_keywords = fetch_keywords_for_url(url_input)

    base_keywords = list(set([k["keyword"] for k in mb_keywords if k.get("search_volume", 0) > 50]))

    if not base_keywords:
        st.warning("No valid keywords found for this URL.")
        st.stop()

    with st.spinner("💡 Expanding to find new keyword opportunities..."):
        expanded = get_keyword_expansions(base_keywords)

    candidates = [k for k in expanded if k.get("search_volume", 0) > 100 and not any(b in k["keyword"].lower() for b in ["magicbricks", "login"])]
    df_all = pd.DataFrame(candidates)[["keyword", "search_volume", "competition"]].rename(columns={
        "keyword": "Keyword", "search_volume": "Search Volume", "competition": "Competition"
    })
    st.subheader("📊 Keyword Ideas Based on Magicbricks URL")
    st.dataframe(df_all)

    st.subheader("🤖 AI-Enhanced Article Ideas")
    enriched = []
    with st.spinner("Using AI to classify and suggest content topics..."):
        for kw in df_all["Keyword"].head(50):
            result = classify_with_grok(kw)
            if result["article_worthy"].lower() == "yes":
                enriched.append({
                    "Keyword": kw,
                    "Title Suggestion": result["title"],
                    "Intent": result["intent"],
                    "Related Topics": ", ".join(result["related_topics"])
                })

    df_final = pd.DataFrame(enriched)
    st.dataframe(df_final)
    st.download_button("⬇️ Download Suggestions", df_final.to_csv(index=False), "final_topics.csv")
