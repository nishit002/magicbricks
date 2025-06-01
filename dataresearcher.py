import streamlit as st
import requests
import pandas as pd
import json

# --- CONFIGURATION ---
PERPLEXITY_API_KEY = "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"
GROK_API_KEY = "xai-0SUbMopdzRt6FgFO6rrudOiBu2JHgZ3yimfkPXoK0bwCOnbgLJupZcDoJ4c4GnenFncizgOpeZwXg9rQ"

# --- FUNCTIONS ---

def call_perplexity_api(topic, fields):
    url = "https://api.perplexity.ai/search"
    headers = {
        "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "query": f"Objective, relevant data for locality: {topic}, focused on: {', '.join(fields)}",
        "include_sources": True
    }
    response = requests.post(url, headers=headers, data=json.dumps(payload))
    if response.status_code == 200:
        return response.json()
    else:
        st.error(f"Perplexity API error: {response.text}")
        return None

def call_grok_api(topic):
    url = "https://api.grok.com/v1/query"
    headers = {
        "Authorization": f"Bearer {GROK_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "prompt": f"Provide contextual information for the locality: {topic}. Focus on socio-economic, real estate trends, and development factors. Give a paragraph.",
        "max_tokens": 300
    }
    response = requests.post(url, headers=headers, data=json.dumps(payload))
    if response.status_code == 200:
        return response.json().get("output", "")
    else:
        st.error(f"Grok API error: {response.text}")
        return ""

def parse_perplexity_result(result):
    data_points = []
    for source in result.get("results", []):
        data_points.append({
            "Title": source.get("title"),
            "Snippet": source.get("snippet"),
            "URL": source.get("url"),
            "Source": source.get("source")
        })
    return pd.DataFrame(data_points)

# --- STREAMLIT UI ---
st.title("🔍 Locality Research using Perplexity + Grok")

locality_input = st.text_input("Enter Locality or Project Name")

data_options = [
    "Real Estate Trends",
    "Connectivity",
    "Nearby Infrastructure",
    "Rental Yield",
    "Buyer Demographics",
    "Upcoming Projects",
    "Price Trends",
    "Social Infrastructure",
    "Schools & Hospitals",
    "Green Cover & Pollution Levels"
]

selected_options = st.multiselect("Select Data Points to Fetch", options=data_options)

if st.button("Fetch Data"):
    if not locality_input or not selected_options:
        st.warning("Please provide both locality and at least one data point.")
    else:
        with st.spinner("Fetching objective data using Perplexity and Grok..."):
            perplexity_result = call_perplexity_api(locality_input, selected_options)
            grok_context = call_grok_api(locality_input)

            if perplexity_result:
                df = parse_perplexity_result(perplexity_result)
                st.subheader("📊 Structured Results from Perplexity")
                st.dataframe(df)

            if grok_context:
                st.subheader("🧠 Contextual Summary from Grok")
                st.write(grok_context)
