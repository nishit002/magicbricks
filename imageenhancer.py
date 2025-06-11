import streamlit as st
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
import io
import os

st.set_page_config(page_title="Image Enhancer with Title", layout="centered")
st.title("✨ Upload an Image & Add a Beautiful Title")

# Upload image
uploaded_file = st.file_uploader("Choose an image", type=["jpg", "jpeg", "png"])
title_text = st.text_input("Enter the title text")

# Settings
text_color = st.color_picker("Pick text color", "#FFFFFF")
bg_shade = st.slider("Image brightness", 0.5, 2.0, 1.0, 0.1)
shadow = st.checkbox("Add shadow to text", value=True)

def add_text_with_shadow(img, text, text_color, shadow=True):
    draw = ImageDraw.Draw(img)
    width, height = img.size

    # Load font
    try:
        font_size = int(height * 0.08)
        font = ImageFont.truetype("arial.ttf", font_size)
    except:
        font = ImageFont.load_default()

    # Resize font until it fits
    while True:
        try:
            bbox = font.getbbox(text)
            text_width, text_height = bbox[2] - bbox[0], bbox[3] - bbox[1]
        except AttributeError:
            text_width, text_height = font.getsize(text)

        if text_width < width * 0.95:
            break
        font_size -= 2
        font = ImageFont.truetype("arial.ttf", font_size) if os.path.exists("arial.ttf") else ImageFont.load_default()

    x = (width - text_width) // 2
    y = 20

    # Shadow effect
    if shadow:
        draw.text((x+2, y+2), text, font=font, fill="black")

    # Main text
    draw.text((x, y), text, font=font, fill=text_color)
    return img

if uploaded_file and title_text:
    # Load and enhance image
    image = Image.open(uploaded_file).convert("RGB")
    enhancer = ImageEnhance.Brightness(image)
    image = enhancer.enhance(bg_shade)

    # Add title text
    enhanced_image = add_text_with_shadow(image.copy(), title_text, text_color, shadow=shadow)

    st.image(enhanced_image, caption="Enhanced Image", use_column_width=True)

    # Download button
    img_bytes = io.BytesIO()
    enhanced_image.save(img_bytes, format='JPEG')
    st.download_button("📥 Download Enhanced Image", data=img_bytes.getvalue(),
                       file_name="enhanced_image.jpg", mime="image/jpeg")
