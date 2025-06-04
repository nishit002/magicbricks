import streamlit as st
import requests
import base64
from PIL import Image
import io

# API key (hardcoded for testing; use .env in production)
XAI_API_KEY = "xai-jAEisoP6P018c58iDzp8yjBXJVwscN7NGw1QxgyTUvkA67AwTdG7L8OgXBE10Wuy9ha5DW3IUd1GJrXg"

# API endpoint
API_URL = "https://api.x.ai/v1/chat/completions"

# Vastu prompt templates
VASTU_PROMPT = """
You are a Vastu Shastra expert. Provide engaging and concise Vastu insights for a building layout facing the {direction} direction. 
Include:
1. Key benefits of this direction
2. Recommended room placements
3. Colors and elements to enhance positive energy
4. Any precautions or remedies
Format the response in a friendly, conversational tone, and keep it under 300 words.
"""

VASTU_PROMPT_WITH_IMAGE = """
You are a Vastu Shastra expert. Analyze the provided floor plan image for a building facing the {direction} direction.
Provide specific insights based on the layout you can see:
1. Analysis of current room placements according to Vastu principles
2. Key benefits of the {direction} facing direction for this layout
3. Specific recommendations for improvement based on the floor plan
4. Colors and elements to enhance positive energy in each area
5. Any precautions or remedies for problematic placements
Format the response in a friendly, conversational tone, and keep it under 400 words.
"""

def encode_image_to_base64(image_file):
    """Convert uploaded image to base64 string"""
    try:
        image = Image.open(image_file)
        if image.mode != 'RGB':
            image = image.convert('RGB')
        buffer = io.BytesIO()
        image.save(buffer, format='JPEG')
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        return image_base64
    except Exception as e:
        st.error(f"Error processing image: {str(e)}")
        return None

def get_vastu_insights(direction, image_base64=None):
    """Get Vastu insights with or without image analysis"""
    if not XAI_API_KEY:
        return "Error: API key not found. Please set XAI_API_KEY."
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {XAI_API_KEY}"
    }
    
    if image_base64:
        model = "grok-3"  # Verify correct model name from xAI API docs
        messages = [
            {
                "role": "system",
                "content": "You are a Vastu Shastra expert analyzing floor plans and providing insights."
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": VASTU_PROMPT_WITH_IMAGE.format(direction=direction)
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_base64}"
                        }
                    }
                ]
            }
        ]
    else:
        model = "grok-3"  # Verify correct model name from xAI API docs
        messages = [
            {
                "role": "system",
                "content": "You are a Vastu Shastra expert providing insightful advice."
            },
            {
                "role": "user",
                "content": VASTU_PROMPT.format(direction=direction)
            }
        ]
    
    data = {
        "model": model,
        "messages": messages,
        "stream": False,
        "temperature": 0.7,
        "max_tokens": 1000
    }
    
    try:
        response = requests.post(API_URL, headers=headers, json=data)
        response.raise_for_status()
        result = response.json()
        return result["choices"][0]["message"]["content"]
    except requests.exceptions.HTTPError as e:
        try:
            error_message = response.json().get("error", {}).get("message", str(e))
        except:
            error_message = str(e)
        return f"Error fetching insights: {error_message}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"

# Streamlit app configuration
st.set_page_config(page_title="Vastu Insights", page_icon="🏡", layout="centered")

# Main app interface
st.title("🏡 Vastu Insights for Your Home")
st.markdown("Upload your floor plan and select the facing direction to get personalized Vastu analysis!")

# Create layout
col1, col2 = st.columns([1, 1])

with col1:
    direction = st.selectbox(
        "🧭 Select facing direction:",
        ["North", "East", "South", "West", "Northeast", "Northwest", "Southeast", "Southwest"],
        help="Choose the direction your main entrance faces"
    )

with col2:
    uploaded_image = st.file_uploader(
        "📋 Upload floor plan:",
        type=["png", "jpg", "jpeg"],
        help="Upload your home layout for detailed analysis"
    )

# Show current selections
st.write(f"Selected direction: **{direction}**")
st.write(f"Image uploaded: **{'Yes' if uploaded_image else 'No'}**")

# Display uploaded image and analysis
if uploaded_image is not None:
    st.image(uploaded_image, caption="Your Floor Plan", use_container_width=True)
    
    if st.button("🔮 Get Vastu Analysis", type="primary"):
        with st.spinner("Analyzing your floor plan with Vastu principles..."):
            image_base64 = encode_image_to_base64(uploaded_image)
            if image_base64:
                insights = get_vastu_insights(direction, image_base64)
                st.success("✨ Analysis Complete!")
                st.subheader(f"Vastu Analysis for {direction}-Facing Home")
                st.markdown(insights)
            else:
                st.error("Failed to process image. Please try uploading again.")
else:
    st.info("👆 Please upload your floor plan image above to get started.")
    if st.button("Get General Vastu Tips"):
        with st.spinner("Getting Vastu insights..."):
            insights = get_vastu_insights(direction)
            st.subheader(f"General Vastu Tips for {direction}-Facing Home")
            st.markdown(insights)

# Additional information
st.markdown("---")
st.markdown("### 📝 Tips for better results:")
st.markdown("""
- Ensure your floor plan image is clear and readable
- Include room labels if possible  
- Make sure the image shows the complete layout
- Specify the correct facing direction of your main entrance
""")

# Basic styling
st.markdown("""
<style>
    .stButton > button {
        background-color: #4CAF50;
        color: white;
        border-radius: 10px;
        border: none;
        padding: 10px 20px;
        font-weight: bold;
    }
    .stButton > button:hover {
        background-color: #45a049;
    }
</style>
""", unsafe_allow_html=True)
