import streamlit as st
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
import io
import os

st.set_page_config(page_title="Blog Cover Title Enhancer", layout="centered")
st.title("📸 Blog Cover Enhancer with Bold Title")

# Upload image
uploaded_file = st.file_uploader("Upload an image", type=["png", "jpg", "jpeg"])
title_text = st.text_input("Enter your blog/post title")

text_color = st.color_picker("Choose text color", "#FFFFFF")
bg_shade = st.slider("Adjust brightness", 0.5, 2.0, 1.0)
position_choice = st.selectbox("Title position", ["Top", "Center", "Bottom"])

# Load modern blog-safe font
def get_font(image_width):
    try:
        font_path = "Montserrat-Bold.ttf"  # Replace with BebasNeue-Regular.ttf if you like
        return ImageFont.truetype(font_path, size=int(image_width * 0.06))
    except:
        return ImageFont.load_default()

# Overlay title
def overlay_title(img, text, fill_color, pos='Top'):
    draw = ImageDraw.Draw(img)
    width, height = img.size
    font = get_font(width)

    # Get text size
    try:
        bbox = font.getbbox(text)
        text_width, text_height = bbox[2] - bbox[0], bbox[3] - bbox[1]
    except AttributeError:
        text_width, text_height = font.getsize(text)

    # Positioning
    x = (width - text_width) // 2
    if pos == "Top":
        y = int(height * 0.05)
    elif pos == "Center":
        y = (height - text_height) // 2
    else:  # Bottom
        y = int(height * 0.85 - text_height)

    # Shadow layer (stroke effect)
    stroke_width = max(1, int(width * 0.002))
    draw.text((x, y), text, font=font, fill="black", stroke_width=stroke_width + 1, stroke_fill="black")
    draw.text((x, y), text, font=font, fill=fill_color, stroke_width=stroke_width, stroke_fill="black")
    return img

if uploaded_file and title_text:
    # Enhance and prepare
    image = Image.open(uploaded_file).convert("RGB")
    image = ImageEnhance.Brightness(image).enhance(bg_shade)

    # Draw title
    enhanced_image = overlay_title(image.copy(), title_text, fill_color=text_color, pos=position_choice)

    st.image(enhanced_image, caption="Enhanced Blog Banner", use_container_width=True)

    img_bytes = io.BytesIO()
    enhanced_image.save(img_bytes, format="JPEG")
    st.download_button("📥 Download Banner", data=img_bytes.getvalue(),
                       file_name="blog_banner.jpg", mime="image/jpeg")
