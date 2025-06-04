import streamlit as st
import openai
import base64
from PIL import Image
import io
from fpdf import FPDF

# === Load OpenAI API key from Streamlit secrets ===
openai.api_key = st.secrets["openai"]["api_key"]

# === Prompt templates ===
VASTU_PROMPT = """
You are a certified Vastu consultant. Share clear, bullet-point-based insights for a house facing {direction}:

- Key benefits of this direction
- Ideal room placements (e.g., entrance, kitchen, toilet, bedrooms)
- Color and element suggestions
- Common mistakes to avoid
- Simple remedies for Vastu doshas

Keep it factual, under 300 words, and actionable.
"""

VASTU_PROMPT_WITH_IMAGE = """
You are a certified Vastu Shastra consultant. Analyze the uploaded floor plan image for a house facing {direction}.

Based on the layout and directional placement:
- Identify rooms or spaces placed correctly as per Vastu (e.g., kitchen, toilet, bedroom, entrance, puja room)
- Highlight rooms placed incorrectly as per Vastu with specific improvement suggestions
- Recommend appropriate Vastu remedies (e.g., mirrors, colors, symbols, plants, crystals) for incorrect placements
- List actionable improvements the homeowner can implement without reconstruction
- Keep the response in clear bullet points under each section

Keep the language concise, factual, and easy to follow.
Avoid generic advice — tailor the suggestions to the floor plan.
"""

# === Encode image to base64 ===
def encode_image_to_base64(image_file):
    image = Image.open(image_file)
    if image.mode != "RGB":
        image = image.convert("RGB")
    buffered = io.BytesIO()
    image.save(buffered, format="JPEG")
    return base64.b64encode(buffered.getvalue()).decode("utf-8")

# === Generate insights from OpenAI ===
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

# === Generate downloadable PDF ===
def generate_pdf(content, direction):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.multi_cell(0, 10, f"Vastu Analysis for {direction}-Facing Home\n\n{content}")
    output = io.BytesIO()
    pdf.output(output)
    return output.getvalue()

# === Streamlit UI ===
st.set_page_config(page_title="Vastu Insights", page_icon="🏡", layout="centered")
st.title("🏡 Vastu Insights for Your Home")
st.markdown("Upload your floor plan and select the facing direction to get personalized, factual Vastu analysis.")

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
        help="Upload your home layout for directional Vastu analysis"
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

            pdf_bytes = generate_pdf(insights, direction)
            st.download_button(
                label="📄 Download PDF",
                data=pdf_bytes,
                file_name=f"Vastu_Analysis_{direction}.pdf",
                mime="application/pdf"
            )
else:
    if st.button("Get General Vastu Tips"):
        with st.spinner("Fetching direction-based Vastu tips..."):
            insights = get_vastu_insights(direction)
            st.subheader(f"General Vastu Tips for {direction}-Facing Home")
            st.markdown(insights)

            pdf_bytes = generate_pdf(insights, direction)
            st.download_button(
                label="📄 Download PDF",
                data=pdf_bytes,
                file_name=f"Vastu_Tips_{direction}.pdf",
                mime="application/pdf"
            )

# === Tips Section ===
st.markdown("---")
st.markdown("### 📝 Tips for better results:")
st.markdown("""
- Upload a complete and clearly labeled floor plan  
- Include directions or North arrow if possible  
- Choose the correct facing direction (main entrance)
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
