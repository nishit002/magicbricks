import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from groq import Groq
import os

# Streamlit page configuration
st.set_page_config(page_title="MagicBricks Property Chatbot", page_icon="🏠", layout="wide")

# Initialize session state for chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Function to scrape MagicBricks data (simplified example, replace with actual scraping logic)
@st.cache_data
def fetch_magicbricks_data():
    # Sample data; replace with actual scraping logic
    # Note: Always respect website terms of service and robots.txt
    data = {
        "city": ["Mumbai", "Delhi", "Bangalore", "Mumbai", "Delhi"],
        "property_type": ["Apartment", "Villa", "Apartment", "Plot", "Apartment"],
        "bhk": ["2 BHK", "3 BHK", "1 BHK", "N/A", "2 BHK"],
        "price": ["1.5 Cr", "3 Cr", "80 Lakh", "2 Cr", "1.2 Cr"],
        "location": ["Andheri", "Vasant Kunj", "Koramangala", "Navi Mumbai", "Dwarka"]
    }
    return pd.DataFrame(data)

# Function to query Grok API
def query_grok(prompt, model="mixtral-8x7b-32768"):
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
    try:
        response = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model=model,
            max_tokens=500
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error querying Grok API: {str(e)}"

# Load MagicBricks data
df = fetch_magicbricks_data()

# Streamlit UI
st.title("MagicBricks Property Chatbot")
st.write("Ask about properties in cities like Mumbai, Delhi, or Bangalore!")

# Model selection
model = st.selectbox("Select Grok Model", ["mixtral-8x7b-32768", "llama3-70b-8192", "llama3-8b-8192"])

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("Ask about properties (e.g., 'Show 2 BHK apartments in Mumbai')"):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Filter data based on user query (simple keyword-based filtering)
    filtered_df = df
    if "mumbai" in prompt.lower():
        filtered_df = filtered_df[filtered_df["city"].str.lower() == "mumbai"]
    if "delhi" in prompt.lower():
        filtered_df = filtered_df[filtered_df["city"].str.lower() == "delhi"]
    if "bangalore" in prompt.lower():
        filtered_df = filtered_df[filtered_df["city"].str.lower() == "bangalore"]
    if "2 bhk" in prompt.lower():
        filtered_df = filtered_df[filtered_df["bhk"].str.lower() == "2 bhk"]
    if "apartment" in prompt.lower():
        filtered_df = filtered_df[filtered_df["property_type"].str.lower() == "apartment"]

    # Prepare context for Grok
    if not filtered_df.empty:
        context = "Here are some properties from MagicBricks:\n"
        for _, row in filtered_df.iterrows():
            context += f"- {row['bhk']} {row['property_type']} in {row['location']}, {row['city']} for {row['price']}\n"
    else:
        context = "No properties found matching your query. Try asking about properties in Mumbai, Delhi, or Bangalore."

    # Combine user prompt with context
    full_prompt = f"User query: {prompt}\nContext: {context}\nRespond as a helpful real estate assistant."

    # Query Grok API
    with st.chat_message("assistant"):
        with st.spinner("Fetching response..."):
            response = query_grok(full_prompt, model)
            st.markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})

# Display filtered data as a table
if not filtered_df.empty:
    st.subheader("Matching Properties")
    st.dataframe(filtered_df)
