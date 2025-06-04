import streamlit as st
import requests
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get API key from environment (works for both local .env and Streamlit Cloud secrets)
API_KEY = os.getenv("XAI_API_KEY")

# API endpoint
API_URL = "https://api.x.ai/v1/chat/completions"

# Vastu prompt template
VASTU_PROMPT = """
You are a Vastu Shastra expert. Provide engaging and concise Vastu insights for a building layout facing the {direction} direction. 
Include:
1. Key benefits of this direction
2. Recommended room placements
3. Colors and elements to enhance positive energy
4. Any precautions or remedies
Format the response in a friendly, conversational tone, and keep it under 300 words.
"""

def get_vastu_insights(direction):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }
    
    data = {
        "messages": [
            {
                "role": "system",
                "content": "You are a Vastu Shastra expert providing insightful and engaging advice."
            },
            {
                "role": "user",
                "content": VASTU_PROMPT.format(direction=direction)
            }
        ],
        "model": "grok-3-latest",
        "stream": False,
        "temperature": 0.7
    }
    
    try:
        response = requests.post(API_URL, headers=headers, json=data)
        response.raise_for_status()
        result = response.json()
        return result["choices"][0]["message"]["content"]
    except requests.exceptions.RequestException pase:
        return f"Error fetching insights: {str(e)}"

# Streamlit app
st.set_page_config(page_title="Vastu Insights", page_icon="🏡", layout="centered")

st.title("🏡 Vastu Insights for Your Home")
st.markdown("Discover Vastu Shastra tips for your home based on its facing direction! Select a direction below and optionally upload a layout image to get personalized insights.")

# Direction selection
direction = st.selectbox(
    "Select the facing direction of your home:",
    ["North", "East", "South", "West", "Northeast", "Northwest", "Southeast", "Southwest"]
)

# Image upload
uploaded_image = st.file_uploader("Upload your home layout image (optional):", type=["png", "jpg", "jpeg"])

# Display uploaded image if provided
if uploaded_image is not None:
    st.image(uploaded_image, caption="Uploaded Home Layout", use_column_width=True)

# Get and display insights
if st.button("Get Vastu Insights"):
    if not API_KEY:
        st.error("API key not found. Please ensure the XAI_API_KEY is set in secrets.toml or .env file.")
    else:
        with st.spinner("Fetching Vastu wisdom..."):
            insights = get_vastu_insights(direction)
            st.subheader(f"Vastu Insights for {direction}-Facing Home")
            st.markdown(insights, unsafe_allow_html=True)
        
# Styling for engagement
st.markdown("""
<style>
    .stButton>button {
        background-color: #4CAF50;
        color: white;
        border-radius: 10px;
        padding: 10px 20px;
    }
    .stSelectbox {
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 10px;
    }
    .stFileUploader {
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 10px;
    }
</style>
""", unsafe_allow_html=True)
