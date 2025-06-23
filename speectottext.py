import streamlit as st
import tempfile
import os
import re
import subprocess
from typing import Optional, Tuple
import base64

# Import libraries with error handling
try:
    from langdetect import detect
    LANGDETECT_AVAILABLE = True
except ImportError:
    LANGDETECT_AVAILABLE = False

try:
    import torch
    import torchaudio
    from TTS.api import TTS
    AI4BHARAT_AVAILABLE = True
except ImportError:
    AI4BHARAT_AVAILABLE = False

try:
    from gtts import gTTS
    GTTS_AVAILABLE = True
except ImportError:
    GTTS_AVAILABLE = False

# Configure page
st.set_page_config(
    page_title="AI4Bharat TTS",
    page_icon="🗣️",
    layout="wide"
)

st.title("🗣️ AI4Bharat TTS")
st.markdown("Direct text-to-speech using AI4Bharat's neural models!")

# AI4Bharat language mapping
AI4BHARAT_LANGUAGES = {
    'hi': {'name': 'Hindi', 'display': 'हिन्दी', 'model_name': 'tts_models/hi/fastpitch/fastpitch'},
    'bn': {'name': 'Bengali', 'display': 'বাংলা', 'model_name': 'tts_models/bn/fastpitch/fastpitch'},
    'te': {'name': 'Telugu', 'display': 'తెలుగు', 'model_name': 'tts_models/te/fastpitch/fastpitch'},
    'ta': {'name': 'Tamil', 'display': 'தமிழ்', 'model_name': 'tts_models/ta/fastpitch/fastpitch'},
    'mr': {'name': 'Marathi', 'display': 'मराठी', 'model_name': 'tts_models/mr/fastpitch/fastpitch'},
    'gu': {'name': 'Gujarati', 'display': 'ગુજરાતી', 'model_name': 'tts_models/gu/fastpitch/fastpitch'},
    'kn': {'name': 'Kannada', 'display': 'ಕನ್ನಡ', 'model_name': 'tts_models/kn/fastpitch/fastpitch'},
    'ml': {'name': 'Malayalam', 'display': 'മലയാളം', 'model_name': 'tts_models/ml/fastpitch/fastpitch'},
    'or': {'name': 'Odia', 'display': 'ଓଡ଼ିଆ', 'model_name': 'tts_models/or/fastpitch/fastpitch'},
    'as': {'name': 'Assamese', 'display': 'অসমীয়া', 'model_name': 'tts_models/as/fastpitch/fastpitch'},
    'en': {'name': 'English', 'display': 'English', 'model_name': 'tts_models/en/ljspeech/tacotron2-DDC'}
}

# Initialize session state
if 'audio_file_path' not in st.session_state:
    st.session_state.audio_file_path = None
if 'detected_language' not in st.session_state:
    st.session_state.detected_language = None
if 'tts_method_used' not in st.session_state:
    st.session_state.tts_method_used = ""

def detect_language(text: str) -> Tuple[str, str]:
    """Detect language from text"""
    try:
        # Script-based detection
        if re.search(r'[\u0900-\u097F]', text):
            if any(word in text for word in ['महाराष्ट्र', 'मराठी']):
                return 'mr', 'Marathi'
            return 'hi', 'Hindi'
        elif re.search(r'[\u0980-\u09FF]', text):
            if any(word in text for word in ['অসম', 'আসাম']):
                return 'as', 'Assamese'
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
        elif re.search(r'[\u0B00-\u0B7F]', text):
            return 'or', 'Odia'
        
        # Use langdetect for English and fallback
        if LANGDETECT_AVAILABLE:
            try:
                detected = detect(text)
                if detected in AI4BHARAT_LANGUAGES:
                    return detected, AI4BHARAT_LANGUAGES[detected]['name']
            except:
                pass
        
        return 'hi', 'Hindi'  # Default
    except:
        return 'hi', 'Hindi'

def generate_ai4bharat_tts(text: str, language_code: str) -> Optional[str]:
    """Generate speech using AI4Bharat TTS"""
    try:
        if not AI4BHARAT_AVAILABLE:
            st.warning("AI4Bharat TTS not available. Install: pip install TTS torch")
            return None
        
        lang_info = AI4BHARAT_LANGUAGES.get(language_code, AI4BHARAT_LANGUAGES['hi'])
        model_name = lang_info['model_name']
        
        st.info(f"🚀 Using AI4Bharat {lang_info['name']} model")
        
        # Initialize TTS with AI4Bharat model
        tts = TTS(model_name=model_name, progress_bar=False)
        
        # Generate speech
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
        temp_file.close()
        
        tts.tts_to_file(text=text, file_path=temp_file.name)
        
        return temp_file.name
        
    except Exception as e:
        st.error(f"AI4Bharat TTS failed: {str(e)}")
        return None

def fallback_to_gtts(text: str, language_code: str) -> Optional[str]:
    """Fallback to Google TTS"""
    try:
        if not GTTS_AVAILABLE:
            return None
        
        # Map AI4Bharat codes to gTTS codes
        gtts_mapping = {
            'hi': 'hi', 'bn': 'bn', 'te': 'te', 'ta': 'ta', 'mr': 'mr',
            'gu': 'gu', 'kn': 'kn', 'ml': 'ml', 'or': 'hi', 'as': 'bn', 'en': 'en'
        }
        
        gtts_lang = gtts_mapping.get(language_code, 'hi')
        
        tts = gTTS(text=text, lang=gtts_lang, slow=False, tld='co.in')
        
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
        tts.save(temp_file.name)
        temp_file.close()
        
        return temp_file.name
        
    except Exception as e:
        st.error(f"Google TTS fallback failed: {str(e)}")
        return None

# Sidebar
st.sidebar.header("⚙️ Status")

# Show availability
if AI4BHARAT_AVAILABLE:
    st.sidebar.success("✅ AI4Bharat TTS available")
else:
    st.sidebar.error("❌ AI4Bharat TTS not installed")

if GTTS_AVAILABLE:
    st.sidebar.success("✅ Google TTS fallback available")
else:
    st.sidebar.error("❌ Google TTS not available")

# Main interface
input_text = st.text_area(
    "Enter text for speech conversion:",
    height=150,
    placeholder="Type your text here in any supported language..."
)

# Sample texts
with st.expander("📚 Sample Texts"):
    samples = {
        "Hindi Cricket": "हेडिंग्ले में भारत की शॉर्ट-बॉल रणनीति आखिरकार रंग लाई। जेमी स्मिथ 40 रन पर आउट हो गए।",
        "Bengali News": "আজ কলকাতায় প্রযুক্তি সম্মেলনে কৃত্রিম বুদ্ধিমত্তার নতুন অগ্রগতি নিয়ে আলোচনা হয়েছে।",
        "Tamil News": "தமிழ்நাட்டில் இன்று தொழில்நுட்ப மாநாட்டில் செயற்கை நுண்ணறிவின் புதிய முன্নেত্রিত्ব বিষয়ে আলোচনা হয়েছে।",
        "Telugu Tech": "తెలుగు రాష্ట్రాలలో సాంకేতికత వేगంగా అభివృద्धি చెందుতోంది।",
        "English": "Today's technology conference showcased amazing advances in artificial intelligence."
    }
    
    cols = st.columns(3)
    for i, (name, text) in enumerate(samples.items()):
        with cols[i % 3]:
            if st.button(f"{name}", key=f"sample_{i}"):
                st.session_state.sample_text = text
    
    if hasattr(st.session_state, 'sample_text'):
        input_text = st.text_area(
            "Enter text for speech conversion:",
            value=st.session_state.sample_text,
            height=150,
            key="updated_input"
        )

# Generate button
col1, col2 = st.columns([3, 1])

with col1:
    if st.button("🎤 Generate Speech", disabled=not input_text.strip(), type="primary"):
        if input_text.strip():
            with st.spinner("Converting text to speech..."):
                # Detect language
                detected_lang_code, detected_lang_name = detect_language(input_text)
                st.session_state.detected_language = f"{detected_lang_name} ({AI4BHARAT_LANGUAGES[detected_lang_code]['display']})"
                
                # Generate speech with AI4Bharat first
                audio_file = None
                method_used = ""
                
                if AI4BHARAT_AVAILABLE:
                    audio_file = generate_ai4bharat_tts(input_text, detected_lang_code)
                    method_used = "AI4Bharat"
                
                # Fallback to Google TTS if AI4Bharat fails
                if not audio_file and GTTS_AVAILABLE:
                    st.info("🔄 Using Google TTS fallback...")
                    audio_file = fallback_to_gtts(input_text, detected_lang_code)
                    method_used = "Google TTS"
                
                if audio_file:
                    st.session_state.audio_file_path = audio_file
                    st.session_state.tts_method_used = method_used
                    st.success(f"✅ Speech generated using {method_used}!")
                else:
                    st.error("❌ Speech generation failed")

with col2:
    if st.button("🗑️ Clear"):
        for key in ['audio_file_path', 'detected_language', 'sample_text', 'tts_method_used']:
            if key in st.session_state:
                del st.session_state[key]
        st.experimental_rerun()

# Results
if st.session_state.detected_language:
    col1, col2 = st.columns(2)
    with col1:
        st.success(f"**Language:** {st.session_state.detected_language}")
    with col2:
        if st.session_state.tts_method_used:
            quality = "🏆 SOTA" if st.session_state.tts_method_used == "AI4Bharat" else "🥈 Good"
            st.info(f"**Method:** {st.session_state.tts_method_used} {quality}")

# Audio output
if st.session_state.audio_file_path:
    st.subheader("🔊 Generated Speech")
    
    try:
        with open(st.session_state.audio_file_path, 'rb') as f:
            audio_bytes = f.read()
        
        # Determine format
        audio_format = 'audio/wav' if st.session_state.audio_file_path.endswith('.wav') else 'audio/mp3'
        st.audio(audio_bytes, format=audio_format)
        
        # Download
        file_extension = 'wav' if st.session_state.audio_file_path.endswith('.wav') else 'mp3'
        st.download_button(
            label="💾 Download Audio",
            data=audio_bytes,
            file_name=f"speech_{st.session_state.detected_language.split()[0].lower()}.{file_extension}",
            mime=audio_format
        )
        
    except Exception as e:
        st.error(f"Audio error: {str(e)}")

# Installation guide
with st.expander("🛠️ Setup AI4Bharat TTS"):
    st.markdown("""
    ### Install AI4Bharat TTS:
    
    ```bash
    pip install TTS torch torchaudio
    ```
    
    ### Test installation:
    ```python
    from TTS.api import TTS
    tts = TTS("tts_models/hi/fastpitch/fastpitch")
    tts.tts_to_file("नमस्कार", "output.wav")
    ```
    
    ### Available Models:
    - Hindi, Bengali, Telugu, Tamil, Marathi
    - Gujarati, Kannada, Malayalam, Odia, Assamese
    - English (LJSpeech)
    """)

# Show supported languages
with st.expander("🌐 Supported Languages"):
    for code, info in AI4BHARAT_LANGUAGES.items():
        status = "✅" if AI4BHARAT_AVAILABLE else "⏳"
        st.write(f"{status} **{info['name']}** ({info['display']}) - `{code}`")

# Cleanup
def cleanup_temp_files():
    if st.session_state.audio_file_path and os.path.exists(st.session_state.audio_file_path):
        try:
            os.unlink(st.session_state.audio_file_path)
        except:
            pass

import atexit
atexit.register(cleanup_temp_files)
