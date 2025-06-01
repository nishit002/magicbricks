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
                "content": "You are a precise and objective real estate researcher. Return factual paragraph summaries."
            },
            {
                "role": "user",
                "content": f"Give a factual analysis for {locality} based on: {', '.join(fields)}. Provide clear, objective paragraph output."
            }
        ]
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code != 200:
            return None, f"Perplexity API Error {response.status_code}: {response.text}"
        result = response.json()
        if "choices" in result and len(result["choices"]) > 0:
            content = result["choices"][0]["message"]["content"]
            return content.strip(), None
        return None, "Perplexity returned no usable content."
    except Exception as e:
        return None, f"Perplexity Exception: {str(e)}"

# --- GROK CHAT COMPLETION ---
def call_grok_chat(locality, fields):
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
                "content": "You are a real estate analyst. Provide clean, concise paragraph summaries only."
            },
            {
                "role": "user",
                "content": f"Give factual insights about {locality} based on: {', '.join(fields)}. Return the output as a paragraph."
            }
        ]
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code != 200:
            return None, f"Grok API Error {response.status_code}: {response.text}"
        result = response.json()
        if "choices" in result and len(result["choices"]) > 0:
            content = result["choices"][0]["message"]["content"]
            return content.strip(), None
        return None, "Grok returned no usable content."
    except Exception as e:
        return None, f"Grok Exception: {str(e)}"

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
            # Try Perplexity first
            perplexity_output, perplexity_error = call_perplexity_chat(locality_input, selected_fields)
            fallback_used = False

            if perplexity_output is None:
                fallback_used = True
                grok_output, grok_error = call_grok_chat(locality_input, selected_fields)
                final_output = grok_output
                final_error = grok_error
            else:
                final_output = perplexity_output
                final_error = None

        st.subheader("📊 Locality Research Results")
        if final_output:
            st.write(final_output)
        else:
            st.warning("⚠️ No valid data received from either API.")

        if final_error:
            st.caption(f"🔧 Debug: {final_error}")
        elif fallback_used:
            st.caption("⚠️ Perplexity failed. Fallback used: Grok")
