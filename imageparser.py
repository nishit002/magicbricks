import streamlit as st
import requests
import base64
from PIL import Image
import io
import openai

# === Load OpenAI API key from Streamlit secrets ===
openai.api_key = st.secrets["openai"]["api_key"]

# === Vastu prompt templates ===
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

# === Encode uploaded image ===
def encode_image_to_base64(image_file):
    image = Image.open(image_file)
    if image.mode != "RGB":
        image = image.convert("RGB")
    buffered = io.BytesIO()
    image.save(buffered, format="JPEG")
    return base64.b64encode(buffered.getvalue()).decode("utf-8")

# === Generate Vastu insights ===
def get_vastu_insights(direction, image_base64=None):
    try:
        if image_base64:
            content = [
                {"type": "text", "text": VASTU_PROMPT_WITH_IMAGE.format(direction=direction)},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}}
            ]
        else:
            content = VASTU_PROMPT.format(direction=direction)

        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a Vastu Shastra expert."},
                {"role": "user", "content": content}
            ],
            max_tokens=1000
        )
        return response.choices[0].message.content

    except Exception as e:
        return f"❌ Error fetching insights: {str(e)}"

# === Streamlit UI ===
st.set_page_config(page_title="Vastu Insights", page_icon="🏡", layout="centered")
st.title("🏡 Vastu Insights for Your Home")
st.markdown("Upload your floor plan and select the facing direction to get personalized Vastu analysis!")

# === Inputs ===
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

# === Output ===
if uploaded_image:
    st.image(uploaded_image, caption="Your Floor Plan", use_container_width=True)
    if st.button("🔮 Get Vastu Analysis"):
        with st.spinner("Analyzing your layout with Vastu principles..."):
            image_base64 = encode_image_to_base64(uploaded_image)
            insights = get_vastu_insights(direction, image_base64)
            st.success("✨ Analysis Complete!")
            st.subheader(f"Vastu Analysis for {direction}-Facing Home")
            st.markdown(insights)
else:
    if st.button("Get General Vastu Tips"):
        with st.spinner("Fetching insights..."):
            insights = get_vastu_insights(direction)
            st.subheader(f"General Vastu Tips for {direction}-Facing Home")
            st.markdown(insights)

# === Tips Section ===
st.markdown("---")
st.markdown("### 📝 Tips for better results:")
st.markdown("""
- Ensure your floor plan image is clear and readable  
- Include room labels if possible  
- Make sure the image shows the complete layout  
- Specify the correct facing direction of your main entrance
""")

# === Styling ===
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
