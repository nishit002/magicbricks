import streamlit as st
import pandas as pd
import requests
from groq import Groq
import os
import json
from datetime import datetime, timedelta

# Streamlit page configuration
st.set_page_config(page_title="MagicBricks Property Chatbot", page_icon="🏠", layout="wide")

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "user_profile" not in st.session_state:
    st.session_state.user_profile = {
        "budget": None,
        "locality": None,
        "bhk": None,
        "purpose": None,
        "soft_prefs": [],
        "last_interaction": None,
        "shortlisted": [],
        "dislikes": []
    }
if "first_time" not in st.session_state:
    st.session_state.first_time = True

# Simulated MagicBricks data (replace with actual API/scraping)
@st.cache_data
def fetch_magicbricks_data():
    data = {
        "id": [1, 2, 3, 4, 5],
        "city": ["Mumbai", "Delhi", "Bangalore", "Mumbai", "Delhi"],
        "property_type": ["Apartment", "Villa", "Apartment", "Plot", "Apartment"],
        "bhk": ["2 BHK", "3 BHK", "1 BHK", "N/A", "2 BHK"],
        "price": ["1.5 Cr", "3 Cr", "80 Lakh", "2 Cr", "1.2 Cr"],
        "location": ["Andheri", "Vasant Kunj", "Koramangala", "Navi Mumbai", "Dwarka"],
        "amenities": ["Park-facing", "Gated", "Metro nearby", "None", "Park-facing"],
        "possession": ["Ready", "Under-construction", "Ready", "N/A", "Ready"]
    }
    return pd.DataFrame(data)

# Function to query Grok API
def query_grok(prompt, model="mixtral-8x7b-32768"):
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
    try:
        response = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model=model,
            max_tokens=1000
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error querying Grok API: {str(e)}"

# Simulated Tabbly integration for advertiser calls
def call_advertiser(property_id):
    # Placeholder for Tabbly API call
    return {
        "property_id": property_id,
        "available": True,
        "details": f"Property {property_id} is available and matches preferences."
    }

# Load data
df = fetch_magicbricks_data()

# Streamlit UI
st.title("MagicBricks AI Co-Pilot")
st.write("Your personal assistant for finding the perfect property!")

# Model selection
model = st.selectbox("Select Grok Model", ["mixtral-8x7b-32768", "llama3-70b-8192", "llama3-8b-8192"])

# Onboarding for first-time users
if st.session_state.first_time:
    st.info("Welcome to MagicBricks AI Co-Pilot! I can help you find properties, verify availability, and schedule visits. Let's start by understanding your needs.")
    st.session_state.first_time = False
    st.session_state.messages.append({
        "role": "assistant",
        "content": "Not sure where to begin? Let me guide your property search. What's your budget range?"
    })

# Handle returning users
if st.session_state.user_profile["last_interaction"]:
    last_interaction = datetime.strptime(st.session_state.user_profile["last_interaction"], "%Y-%m-%d %H:%M:%S")
    days_inactive = (datetime.now() - last_interaction).days
    if days_inactive > 30:
        st.info("It's been a while! Shall we reconfirm your preferences?")
        st.session_state.messages.append({
            "role": "assistant",
            "content": "You haven’t been here for a while. Want to update your preferences or continue with past ones?"
        })
    elif days_inactive > 7:
        st.session_state.messages.append({
            "role": "assistant",
            "content": "Welcome back! Anything changed in your requirements since we last spoke?"
        })
    else:
        st.session_state.messages.append({
            "role": "assistant",
            "content": f"Welcome back! Last time, you looked for {st.session_state.user_profile['bhk']} in {st.session_state.user_profile['locality']}. Continue from there?"
        })

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

    # Update user profile based on input
    prompt_lower = prompt.lower()
    if "budget" in prompt_lower:
        budget = prompt.split("budget")[-1].strip()
        st.session_state.user_profile["budget"] = budget
    if "bhk" in prompt_lower:
        bhk = "2 BHK" if "2 bhk" in prompt_lower else "3 BHK" if "3 bhk" in prompt_lower else None
        st.session_state.user_profile["bhk"] = bhk
    if "mumbai" in prompt_lower:
        st.session_state.user_profile["locality"] = "Mumbai"
    if "delhi" in prompt_lower:
        st.session_state.user_profile["locality"] = "Delhi"
    if "bangalore" in prompt_lower:
        st.session_state.user_profile["locality"] = "Bangalore"
    if "park-facing" in prompt_lower or "metro nearby" in prompt_lower:
        st.session_state.user_profile["soft_prefs"].append(prompt_lower)

    # Filter data based on user profile
    filtered_df = df
    if st.session_state.user_profile["locality"]:
        filtered_df = filtered_df[filtered_df["city"].str.lower() == st.session_state.user_profile["locality"].lower()]
    if st.session_state.user_profile["bhk"]:
        filtered_df = filtered_df[filtered_df["bhk"].str.lower() == st.session_state.user_profile["bhk"].lower()]
    if "apartment" in prompt_lower:
        filtered_df = filtered_df[filtered_df["property_type"].str.lower() == "apartment"]

    # Contextual nudges
    if len(filtered_df) < 5 and len(filtered_df) > 0:
        st.session_state.messages.append({
            "role": "assistant",
            "content": "Only a few matches found. Want to expand your search radius or increase budget?"
        })
    elif len(filtered_df) > 30:
        st.session_state.messages.append({
            "role": "assistant",
            "content": "That's a lot of options! Want help narrowing it down to the top 5?"
        })
    elif len(filtered_df) == 0:
        st.session_state.messages.append({
            "role": "assistant",
            "content": "No properties found. Try relaxing some filters or exploring nearby localities."
        })

    # Prepare context for Grok
    if not filtered_df.empty:
        context = "Here are some properties from MagicBricks:\n"
        for _, row in filtered_df.iterrows():
            context += f"- {row['bhk']} {row['property_type']} in {row['location']}, {row['city']} for {row['price']} ({row['amenities']}, {row['possession']})\n"
        context += "User preferences: " + str(st.session_state.user_profile)
    else:
        context = "No properties found. Suggest relaxing filters or exploring nearby localities."

    # Combine user prompt with context
    full_prompt = f"User query: {prompt}\nContext: {context}\nRespond as a helpful real estate assistant. Use nudges and preference capture as per MagicBricks AI Co-Pilot guidelines."

    # Query Grok API
    with st.chat_message("assistant"):
        with st.spinner("Fetching response..."):
            response = query_grok(full_prompt, model)
            st.markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})

    # Update last interaction
    st.session_state.user_profile["last_interaction"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# Display filtered data as a table
if not filtered_df.empty:
    st.subheader("Matching Properties")
    st.dataframe(filtered_df)

    # Shortlist and call advertiser
    st.subheader("Shortlist Properties")
    selected_properties = st.multiselect("Select properties to shortlist", filtered_df["id"].tolist())
    if selected_properties:
        st.session_state.user_profile["shortlisted"].extend(selected_properties)
        if st.button("Check Availability with Sellers"):
            for prop_id in selected_properties:
                call_result = call_advertiser(prop_id)
                st.write(f"Call Result for Property {prop_id}: {call_result['details']}")
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": f"Checked availability for Property {prop_id}: {call_result['details']}"
                })

# Nudge for preference capture if profile is incomplete
if not st.session_state.user_profile["budget"] or not st.session_state.user_profile["locality"]:
    st.sidebar.info("Help me understand your needs better!")
    budget = st.sidebar.text_input("What's your budget range? (e.g., 80L–1.2Cr)")
    locality = st.sidebar.selectbox("Preferred locality", ["Mumbai", "Delhi", "Bangalore", "Other"])
    bhk = st.sidebar.selectbox("BHK preference", ["1 BHK", "2 BHK", "3 BHK", "N/A"])
    purpose = st.sidebar.radio("Buying for?", ["Self-use", "Investment"])
    if st.sidebar.button("Save Preferences"):
        st.session_state.user_profile.update({
            "budget": budget,
            "locality": locality,
            "bhk": bhk,
            "purpose": purpose
        })
        st.sidebar.success("Preferences saved!")
        st.session_state.messages.append({
            "role": "assistant",
            "content": "Got your preferences! Let me find some properties for you."
        })
