# main.py
import streamlit as st
import pandas as pd
import requests
from requests.auth import HTTPBasicAuth

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
    if response.status_code == 200:
        result = response.json()
        return result["tasks"][0]["result"][0]["items"]
    else:
        st.error(f"DataForSEO API error: {response.status_code}")
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
            parsed = response.json()["text"]
            return eval(parsed)
        except:
            return {"article_worthy": "No", "title": "", "intent": ""}
    else:
        return {"article_worthy": "No", "title": "", "intent": ""}

# UI to trigger
if st.button("🔍 Discover Topics"):
    with st.spinner("Fetching keywords from housing.com..."):
        raw_keywords = fetch_keywords_from_site()

    filtered = [k for k in raw_keywords if k["search_volume"] > 100 and not any(b in k["keyword"] for b in ["magicbricks", "99acres", "login", "property id"])]
    st.success(f"Filtered {len(filtered)} keywords with volume > 100")

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
