import streamlit as st
import pandas as pd
import requests
from requests.auth import HTTPBasicAuth
import json
import os

st.set_page_config(layout="wide")
st.title("🧠 AI Content Gap Finder for Real Estate")
st.write("Enter a Magicbricks URL or use uploaded keyword list to discover content opportunities.")

# Load secrets
DFS_LOGIN = st.secrets["dataforseo"]["login"]
DFS_PASSWORD = st.secrets["dataforseo"]["password"]
GROK_API_KEY = st.secrets["grok"]["api_key"]
SCRAPER_API_KEY = st.secrets["scraper"]["api_key"]

# Load keywords from Excel file
def load_keywords_from_excel():
    try:
        df = pd.read_excel("keyword with url.xlsx")
        return df[["Keyword", "URL"]].dropna().to_dict(orient="records")
    except FileNotFoundError:
        st.error("keyword with url.xlsx not found in the directory.")
        return []
    except Exception as e:
        st.error(f"Error loading Excel file: {str(e)}")
        return []

# Step 1: Fetch keywords using DataForSEO or Scraper API
def fetch_keywords_for_url(url):
    # Try DataForSEO first
    endpoint = "https://api.dataforseo.com/v3/keywords_data/google_ads/keywords_for_url/live"
    payload = [{"target": url, "language_code": "en", "location_code": 2356}]
    response = requests.post(endpoint, auth=HTTPBasicAuth(DFS_LOGIN, DFS_PASSWORD), json=payload)

    st.write("DataForSEO API Status Code:", response.status_code)
    st.write("DataForSEO API Response:", response.text)

    if response.status_code == 200:
        result = response.json()
        st.write("Raw DataForSEO Result:", result)
        try:
            return result["tasks"][0]["result"][0]["items"]
        except (KeyError, IndexError):
            st.error("Error parsing DataForSEO response.")
            return []
    elif response.status_code == 404:  # Fallback to Scraper API
        st.warning("DataForSEO failed with 404. Trying Scraper API...")
        scraper_url = f"http://api.scraperapi.com?api_key={SCRAPER_API_KEY}&url={url}&render=true"
        scraper_response = requests.get(scraper_url)
        st.write("Scraper API Status Code:", scraper_response.status_code)
        st.write("Scraper API Response:", scraper_response.text)

        if scraper_response.status_code == 200:
            # Simple keyword extraction from HTML (basic approach)
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(scraper_response.text, "html.parser")
            keywords = []
            for meta in soup.find_all("meta"):
                if "keywords" in meta.get("name", "").lower():
                    keywords.extend(meta.get("content", "").split(","))
            return [{"keyword": kw.strip(), "search_volume": 0} for kw in keywords if kw.strip()]
        else:
            st.error(f"Scraper API failed: {scraper_response.status_code}")
            return []

    st.error(f"Failed to fetch keywords from Magicbricks URL: {response.status_code}")
    return []

# Step 2: Get keyword expansions from DataForSEO for each keyword
def get_keyword_expansions(keywords):
    endpoint = "https://api.dataforseo.com/v3/keywords_data/google_ads/keywords_for_keywords/live"
    payload = [{"keywords": [k], "language_code": "en", "location_code": 2356} for k in keywords]
    response = requests.post(endpoint, auth=HTTPBasicAuth(DFS_LOGIN, DFS_PASSWORD), json=payload)
    expanded = []
    if response.status_code == 200:
        try:
            result = response.json()
            for task in result.get("tasks", []):
                items = task.get("result", [{}])[0].get("items", [])
                expanded.extend(items)
        except (KeyError, IndexError):
            pass
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
url_input = st.text_input("🔗 Enter a Magicbricks URL to analyze (optional):")
keywords_data = load_keywords_from_excel()

if st.button("Discover Topics"):
    if url_input:
        with st.spinner("🔍 Fetching keywords from Magicbricks page..."):
            mb_keywords = fetch_keywords_for_url(url_input)
        base_keywords = list(set([k["keyword"] for k in mb_keywords if k.get("search_volume", 0) > 0]))
    elif keywords_data:
        base_keywords = list(set([item["Keyword"] for item in keywords_data]))
    else:
        st.warning("No valid keywords found. Please provide a URL or ensure the Excel file is available.")
        st.stop()

    if not base_keywords:
        st.warning("No valid keywords found for this URL or Excel data.")
        st.stop()

    with st.spinner("💡 Expanding to find new keyword opportunities..."):
        expanded = get_keyword_expansions(base_keywords)

    candidates = [k for k in expanded if k.get("search_volume", 0) > 100 and not any(b in k["keyword"].lower() for b in ["magicbricks", "login"])]
    df_all = pd.DataFrame(candidates)[["keyword", "search_volume", "competition"]].rename(columns={
        "keyword": "Keyword", "search_volume": "Search Volume", "competition": "Competition"
    })
    st.subheader("📊 Keyword Ideas Based on Input")
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

# Install required package if not present
try:
    import bs4
except ImportError:
    st.warning("Please install BeautifulSoup: `pip install beautifulsoup4`")
