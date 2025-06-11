import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import io

st.set_page_config(page_title="Image Enhancer with Title", layout="centered")

st.title("🖼️ Image Enhancer with Title Text")

# File uploader
uploaded_file = st.file_uploader("Upload an image", type=["png", "jpg", "jpeg"])

# Title input
title_text = st.text_input("Enter the title to overlay on the image")

if uploaded_file and title_text:
    # Open the image
    image = Image.open(uploaded_file).convert("RGBA")

    # Prepare drawing context
    txt_layer = Image.new("RGBA", image.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(txt_layer)

    # Load a font (fallback to default if no font file is found)
    try:
        font = ImageFont.truetype("arial.ttf", size=int(image.size[1] * 0.07))
    except:
        font = ImageFont.load_default()

    # Calculate text size and position
    text_width, text_height = draw.textsize(title_text, font=font)
    position = ((image.width - text_width) // 2, 20)  # top-center

    # Draw the text
    draw.text(position, title_text, font=font, fill=(255, 255, 255, 255))

    # Merge image and text layer
    combined = Image.alpha_composite(image, txt_layer)

    # Convert back to RGB
    final_image = combined.convert("RGB")

    st.image(final_image, caption="Enhanced Image", use_column_width=True)

    # Offer download
    img_bytes = io.BytesIO()
    final_image.save(img_bytes, format='JPEG')
    st.download_button(label="📥 Download Enhanced Image", data=img_bytes.getvalue(),
                       file_name="enhanced_image.jpg", mime="image/jpeg")
