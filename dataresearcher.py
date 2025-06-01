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
                "content": "You are a precise and objective real estate researcher."
            },
            {
                "role": "user",
                "content": f"Give a data-backed analysis for {locality} based on: {', '.join(fields)}. Be objective and structured."
            }
        ]
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"❌ Perplexity Error: {e}"

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
                "content": "You are a real estate analyst. Focus only on location-specific facts."
            },
            {
                "role": "user",
                "content": f"Write a factual summary about {locality} including infrastructure, livability, housing demand, and growth potential."
            }
        ]
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"❌ Grok Error: {e}"

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
        st.write(perplexity_output)

        st.subheader("🤖 Grok Response")
        st.write(grok_output)
