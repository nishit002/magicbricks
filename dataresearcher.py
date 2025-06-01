import streamlit as st
import requests
import pandas as pd
import json

# --- SECRETS FROM STREAMLIT CLOUD ---
PERPLEXITY_API_KEY = st.secrets["api"]["perplexity_key"]
GROK_API_KEY = st.secrets["api"]["grok_key"]

# --- PERPLEXITY CHAT COMPLETION ---
def call_perplexity_chat(locality, fields):
    url = "https://api.perplexity.ai/chat/completions"
    headers = {
        "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "sonar",
        "messages": [
            {
                "role": "system",
                "content": "You are a precise and objective real estate researcher. Return structured facts in key:value format."
            },
            {
                "role": "user",
                "content": f"Give a factual analysis for {locality} based on: {', '.join(fields)}. Respond in JSON format with key-value pairs."
            }
        ]
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        result = response.json()
        content = result["choices"][0]["message"]["content"]
        return json.loads(content)
    except Exception as e:
        return {"Error": f"Perplexity Error: {e}"}

# --- GROK CHAT COMPLETION ---
def call_grok_chat(locality):
    url = "https://api.x.ai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROK_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "grok-3-latest",
        "stream": False,
        "temperature": 0,
        "messages": [
            {
                "role": "system",
                "content": "You are a real estate analyst. Return facts only, in JSON format."
            },
            {
                "role": "user",
                "content": f"Give factual structured data about {locality} including infrastructure, housing demand, safety, and rental trends. Respond as JSON key-value."
            }
        ]
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        result = response.json()
        content = result["choices"][0]["message"]["content"]
        return json.loads(content)
    except Exception as e:
        return {"Error": f"Grok Error: {e}"}

# --- STREAMLIT UI ---
st.title("📍 AI-Powered Locality Research Tool")

locality_input = st.text_input("Enter a Locality or Project Name")

data_points = [
    "Real Estate Trends", "Connectivity", "Price Trends", "Nearby Infrastructure",
    "Rental Yield", "Demographics", "Growth Potential", "Public Transport", "Safety"
]

selected_fields = st.multiselect("Select Data Points to Fetch", options=data_points)

if st.button("🔍 Fetch Insights"):
    if not locality_input or not selected_fields:
        st.warning("Please enter a locality and select at least one data point.")
    else:
        with st.spinner("Contacting Perplexity and Grok APIs..."):
            perplexity_output = call_perplexity_chat(locality_input, selected_fields)
            grok_output = call_grok_chat(locality_input)

        st.subheader("🧠 Perplexity Response")
        if isinstance(perplexity_output, dict):
            df1 = pd.DataFrame(perplexity_output.items(), columns=["Attribute", "Value"])
            st.dataframe(df1)
        else:
            st.error("Invalid Perplexity Output")

        st.subheader("🤖 Grok Response")
        if isinstance(grok_output, dict):
            df2 = pd.DataFrame(grok_output.items(), columns=["Attribute", "Value"])
            st.dataframe(df2)
        else:
            st.error("Invalid Grok Output")
