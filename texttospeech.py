import streamlit as st
import tempfile
import os
import re
from typing import Optional, Tuple
import base64

# Import libraries with error handling
try:
    from gtts import gTTS
    GTTS_AVAILABLE = True
except ImportError:
    GTTS_AVAILABLE = False

try:
    from langdetect import detect
    LANGDETECT_AVAILABLE = True
except ImportError:
    LANGDETECT_AVAILABLE = False

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

# Configure page
st.set_page_config(
    page_title="Fast Indic TTS",
    page_icon="🗣️",
    layout="wide"
)

st.title("🗣️ Fast Human-like Indic TTS")
st.markdown("Enhanced text-to-speech with natural pace and emotion!")

# Language mapping
INDIC_LANGUAGES = {
    'hi': {'name': 'Hindi', 'code': 'hi', 'display': 'हिन्दी'},
    'bn': {'name': 'Bengali', 'code': 'bn', 'display': 'বাংলা'},
    'te': {'name': 'Telugu', 'code': 'te', 'display': 'తెలుగు'},
    'ta': {'name': 'Tamil', 'code': 'ta', 'display': 'தমிழ்'},
    'mr': {'name': 'Marathi', 'code': 'mr', 'display': 'मराठी'},
    'gu': {'name': 'Gujarati', 'code': 'gu', 'display': 'ગુજરાતી'},
    'kn': {'name': 'Kannada', 'code': 'kn', 'display': 'ಕನ್ನಡ'},
    'ml': {'name': 'Malayalam', 'code': 'ml', 'display': 'മലയാളം'},
    'en': {'name': 'English', 'code': 'en', 'display': 'English'}
}

# Initialize session state
if 'audio_file_path' not in st.session_state:
    st.session_state.audio_file_path = None
if 'enhanced_text' not in st.session_state:
    st.session_state.enhanced_text = ""
if 'detected_language' not in st.session_state:
    st.session_state.detected_language = None

def initialize_openai():
    """Initialize OpenAI client"""
    try:
        if "OPENAI_API_KEY" in st.secrets:
            return OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
        else:
            st.sidebar.error("Add OPENAI_API_KEY to Streamlit secrets")
            return None
    except Exception as e:
        st.sidebar.error(f"OpenAI init failed: {str(e)}")
        return None

def enhance_text_for_dynamic_speech(text: str, language: str, client: OpenAI) -> str:
    """Enhance text for fast, emotional, dynamic speech"""
    try:
        lang_name = INDIC_LANGUAGES.get(language, INDIC_LANGUAGES['en'])['name']
        
        prompt = f"""Transform this {lang_name} text for fast, dynamic, emotional speech delivery:

RULES:
1. Make it sound like an excited sports commentator or news anchor
2. Add emotional words and expressions
3. Use short, punchy sentences for speed
4. Add natural enthusiasm and energy
5. Remove unnecessary pauses - make it flow fast
6. Add emphasis words but keep it natural
7. Make it sound urgent and engaging
8. NO slow fillers or long pauses

Text: "{text}"

Enhanced dynamic version:"""

        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system", 
                    "content": f"""You are an expert at creating fast, dynamic, emotional {lang_name} speech content. 
                    Make text sound like an energetic news anchor or sports commentator - fast, engaging, and full of energy.
                    NO slow speech patterns. Focus on speed and emotion."""
                },
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000,
            temperature=0.8,
            top_p=0.9
        )
        
        enhanced_text = response.choices[0].message.content.strip()
        enhanced_text = re.sub(r'^["\']|["\']$', '', enhanced_text)
        enhanced_text = re.sub(r'^(Enhanced.*?:|Dynamic.*?:)\s*', '', enhanced_text, flags=re.IGNORECASE)
        
        # Remove slow speech patterns and optimize for speed
        enhanced_text = re.sub(r'\.{2,}', '.', enhanced_text)  # Remove multiple dots
        enhanced_text = re.sub(r'\s+', ' ', enhanced_text)     # Clean spaces
        
        return enhanced_text
        
    except Exception as e:
        st.warning(f"Enhancement failed: {str(e)}")
        return text

def detect_language(text: str) -> Tuple[str, str]:
    """Detect language from text"""
    try:
        # Script-based detection
        if re.search(r'[\u0900-\u097F]', text):
            return 'hi', 'Hindi'
        elif re.search(r'[\u0980-\u09FF]', text):
            return 'bn', 'Bengali'
        elif re.search(r'[\u0C00-\u0C7F]', text):
            return 'te', 'Telugu'
        elif re.search(r'[\u0B80-\u0BFF]', text):
            return 'ta', 'Tamil'
        elif re.search(r'[\u0A80-\u0AFF]', text):
            return 'gu', 'Gujarati'
        elif re.search(r'[\u0C80-\u0CFF]', text):
            return 'kn', 'Kannada'
        elif re.search(r'[\u0D00-\u0D7F]', text):
            return 'ml', 'Malayalam'
        
        # Use langdetect for others
        if LANGDETECT_AVAILABLE:
            try:
                detected = detect(text)
                if detected in INDIC_LANGUAGES:
                    return detected, INDIC_LANGUAGES[detected]['name']
            except:
                pass
        
        return 'en', 'English'
    except:
        return 'en', 'English'

def generate_fast_speech(text: str, language_code: str) -> Optional[str]:
    """Generate fast, dynamic speech using optimized gTTS"""
    try:
        # Use fast speech settings - NO slow parameter
        tts = gTTS(
            text=text, 
            lang=language_code,
            slow=False,  # Always fast
            tld='co.in' if language_code != 'en' else 'com'
        )
        
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
        tts.save(temp_file.name)
        temp_file.close()
        
        return temp_file.name
        
    except Exception as e:
        st.error(f"Speech generation failed: {str(e)}")
        return None

# Sidebar settings
st.sidebar.header("⚙️ Settings")

use_enhancement = st.sidebar.checkbox(
    "🤖 ChatGPT Enhancement",
    value=True if OPENAI_AVAILABLE else False,
    help="Make speech more dynamic and emotional"
)

# Initialize OpenAI
openai_client = None
if use_enhancement and OPENAI_AVAILABLE:
    openai_client = initialize_openai()
    if openai_client:
        st.sidebar.success("✅ ChatGPT ready")

# Main interface
input_text = st.text_area(
    "Enter text:",
    height=150,
    placeholder="Enter your text here for fast, dynamic speech conversion..."
)

# Sample texts
with st.expander("📚 Try Sample Texts"):
    samples = {
        "Hindi Sports": "हेडिंग्ले में भारत की शॉर्ट-बॉल रणनीति आखिरकार रंग लाई। जेमी स्मिथ 40 रन पर आउट हो गए।",
        "Hindi News": "आज दिल्ली में भारी बारिश के कारण जल-जमाव की स्थिति हो गई है। मेट्रो सेवाएं प्रभावित हैं।",
        "English News": "Breaking news: The stock market has reached an all-time high today with technology stocks leading the surge."
    }
    
    cols = st.columns(len(samples))
    for i, (name, text) in enumerate(samples.items()):
        with cols[i]:
            if st.button(f"{name}", key=f"sample_{i}"):
                st.session_state.sample_text = text
    
    if hasattr(st.session_state, 'sample_text'):
        input_text = st.text_area(
            "Enter text:",
            value=st.session_state.sample_text,
            height=150,
            key="updated_input"
        )

# Generate button
col1, col2 = st.columns([3, 1])

with col1:
    if st.button("🚀 Generate Fast Speech", disabled=not input_text.strip(), type="primary"):
        if input_text.strip():
            with st.spinner("Generating fast speech..."):
                # Detect language
                detected_lang_code, detected_lang_name = detect_language(input_text)
                st.session_state.detected_language = detected_lang_name
                
                # Enhance text if enabled
                final_text = input_text
                if use_enhancement and openai_client:
                    enhanced_text = enhance_text_for_dynamic_speech(input_text, detected_lang_code, openai_client)
                    st.session_state.enhanced_text = enhanced_text
                    final_text = enhanced_text
                else:
                    st.session_state.enhanced_text = ""
                
                # Generate speech
                if GTTS_AVAILABLE:
                    audio_file = generate_fast_speech(final_text, detected_lang_code)
                    if audio_file:
                        st.session_state.audio_file_path = audio_file
                        st.success("✅ Fast speech generated!")
                    else:
                        st.error("❌ Failed to generate speech")
                else:
                    st.error("❌ gTTS not available. Install: pip install gtts")

with col2:
    if st.button("🗑️ Clear"):
        for key in ['audio_file_path', 'enhanced_text', 'detected_language', 'sample_text']:
            if key in st.session_state:
                del st.session_state[key]
        st.experimental_rerun()

# Results
if st.session_state.detected_language:
    st.success(f"**Language:** {st.session_state.detected_language}")

# Text comparison
if st.session_state.enhanced_text:
    with st.expander("📊 Text Enhancement"):
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Original:**")
            st.text_area("", input_text, height=100, disabled=True, key="orig")
        with col2:
            st.markdown("**Enhanced:**")
            st.text_area("", st.session_state.enhanced_text, height=100, disabled=True, key="enh")

# Audio output
if st.session_state.audio_file_path:
    st.subheader("🔊 Fast Speech Output")
    
    try:
        with open(st.session_state.audio_file_path, 'rb') as f:
            audio_bytes = f.read()
        
        st.audio(audio_bytes, format='audio/mp3')
        
        # Download
        st.download_button(
            label="💾 Download Audio",
            data=audio_bytes,
            file_name=f"fast_speech_{st.session_state.detected_language.lower()}.mp3",
            mime="audio/mp3"
        )
        
    except Exception as e:
        st.error(f"Audio error: {str(e)}")

# Quick tips
with st.expander("⚡ Speed Tips"):
    st.markdown("""
    **For Fastest, Most Dynamic Speech:**
    - ✅ Always enable ChatGPT Enhancement
    - ✅ Use short, punchy sentences
    - ✅ The system automatically uses fast speech (no slow mode)
    - ✅ Enhancement adds energy and emotion automatically
    - ❌ Don't use very long paragraphs
    """)

# Cleanup
def cleanup_temp_files():
    if st.session_state.audio_file_path and os.path.exists(st.session_state.audio_file_path):
        try:
            os.unlink(st.session_state.audio_file_path)
        except:
            pass

import atexit
atexit.register(cleanup_temp_files)
