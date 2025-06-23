import streamlit as st
import tempfile
import os
import re
from typing import Optional, Tuple
import base64

# Import libraries with error handling
try:
    import pyttsx3
    PYTTSX3_AVAILABLE = True
except ImportError:
    PYTTSX3_AVAILABLE = False

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

# Configure page
st.set_page_config(
    page_title="Indic Text-to-Speech",
    page_icon="🗣️",
    layout="wide"
)

# Title and description
st.title("🗣️ Indic Text-to-Speech Converter")
st.markdown("Advanced text-to-speech with automatic Indic language detection and natural tonality!")

# Indic language mapping for gTTS
INDIC_LANGUAGES = {
    'hi': {'name': 'Hindi', 'code': 'hi', 'display': 'हिन्दी'},
    'bn': {'name': 'Bengali', 'code': 'bn', 'display': 'বাংলা'},
    'te': {'name': 'Telugu', 'code': 'te', 'display': 'తెలుగు'},
    'ta': {'name': 'Tamil', 'code': 'ta', 'display': 'தமிழ்'},
    'mr': {'name': 'Marathi', 'code': 'mr', 'display': 'मराठी'},
    'gu': {'name': 'Gujarati', 'code': 'gu', 'display': 'ગુજરાતી'},
    'kn': {'name': 'Kannada', 'code': 'kn', 'display': 'ಕನ್ನಡ'},
    'ml': {'name': 'Malayalam', 'code': 'ml', 'display': 'മലയാളം'},
    'pa': {'name': 'Punjabi', 'code': 'pa', 'display': 'ਪੰਜਾਬੀ'},
    'ur': {'name': 'Urdu', 'code': 'ur', 'display': 'اردو'},
    'en': {'name': 'English', 'code': 'en', 'display': 'English'},
    'sa': {'name': 'Sanskrit', 'code': 'hi', 'display': 'संस्कृत'}  # Use Hindi TTS for Sanskrit
}

# Initialize session state
if 'generated_audio' not in st.session_state:
    st.session_state.generated_audio = None
if 'detected_language' not in st.session_state:
    st.session_state.detected_language = None
if 'audio_file_path' not in st.session_state:
    st.session_state.audio_file_path = None

def detect_language(text: str) -> Tuple[str, str]:
    """Detect language from text with Indic language priority"""
    try:
        # Clean text for better detection
        clean_text = re.sub(r'[^\w\s]', '', text).strip()
        
        if not clean_text:
            return 'en', 'English'
        
        # Manual detection for common Indic scripts
        if re.search(r'[\u0900-\u097F]', text):  # Devanagari (Hindi/Sanskrit)
            return 'hi', 'Hindi'
        elif re.search(r'[\u0980-\u09FF]', text):  # Bengali
            return 'bn', 'Bengali'
        elif re.search(r'[\u0C00-\u0C7F]', text):  # Telugu
            return 'te', 'Telugu'
        elif re.search(r'[\u0B80-\u0BFF]', text):  # Tamil
            return 'ta', 'Tamil'
        elif re.search(r'[\u0A80-\u0AFF]', text):  # Gujarati
            return 'gu', 'Gujarati'
        elif re.search(r'[\u0C80-\u0CFF]', text):  # Kannada
            return 'kn', 'Kannada'
        elif re.search(r'[\u0D00-\u0D7F]', text):  # Malayalam
            return 'ml', 'Malayalam'
        elif re.search(r'[\u0A00-\u0A7F]', text):  # Gurmukhi (Punjabi)
            return 'pa', 'Punjabi'
        elif re.search(r'[\u0600-\u06FF]', text):  # Arabic script (Urdu)
            return 'ur', 'Urdu'
        
        # Use langdetect for other languages
        if LANGDETECT_AVAILABLE:
            try:
                detected = detect(clean_text)
                if detected in INDIC_LANGUAGES:
                    return detected, INDIC_LANGUAGES[detected]['name']
            except:
                pass
        
        # Default to English
        return 'en', 'English'
        
    except Exception as e:
        st.warning(f"Language detection failed: {str(e)}")
        return 'en', 'English'

def generate_speech_gtts(text: str, language_code: str, slow: bool = False) -> Optional[str]:
    """Generate speech using Google Text-to-Speech"""
    try:
        # Map language code to gTTS supported code
        gtts_lang = INDIC_LANGUAGES.get(language_code, {}).get('code', 'en')
        
        # Create TTS object
        tts = gTTS(text=text, lang=gtts_lang, slow=slow)
        
        # Save to temporary file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
        tts.save(temp_file.name)
        temp_file.close()
        
        return temp_file.name
        
    except Exception as e:
        st.error(f"gTTS generation failed: {str(e)}")
        return None

def generate_speech_pyttsx3(text: str, language_code: str, rate: int = 150, volume: float = 0.9) -> Optional[str]:
    """Generate speech using pyttsx3 (offline)"""
    try:
        engine = pyttsx3.init()
        
        # Set properties
        engine.setProperty('rate', rate)
        engine.setProperty('volume', volume)
        
        # Try to set voice based on language
        voices = engine.getProperty('voices')
        for voice in voices:
            if language_code in voice.id.lower() or INDIC_LANGUAGES.get(language_code, {}).get('name', '').lower() in voice.name.lower():
                engine.setProperty('voice', voice.id)
                break
        
        # Save to temporary file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
        temp_file.close()
        
        engine.save_to_file(text, temp_file.name)
        engine.runAndWait()
        
        return temp_file.name
        
    except Exception as e:
        st.error(f"pyttsx3 generation failed: {str(e)}")
        return None

def create_audio_download_link(file_path: str, filename: str = "speech.mp3") -> str:
    """Create download link for audio file"""
    try:
        with open(file_path, 'rb') as f:
            audio_bytes = f.read()
        
        b64_audio = base64.b64encode(audio_bytes).decode()
        href = f'<a href="data:audio/mp3;base64,{b64_audio}" download="{filename}">Download Audio File</a>'
        return href
    except Exception as e:
        return f"Error creating download link: {str(e)}"

# Sidebar settings
st.sidebar.header("⚙️ Settings")

# TTS Engine selection
tts_engine = st.sidebar.selectbox(
    "Text-to-Speech Engine",
    ["Google TTS (Online)", "System TTS (Offline)"] if GTTS_AVAILABLE else ["System TTS (Offline)"],
    index=0 if GTTS_AVAILABLE else 0
)

# Voice settings
st.sidebar.subheader("Voice Settings")

if "Google TTS" in tts_engine:
    speech_speed = st.sidebar.selectbox(
        "Speech Speed",
        ["Normal", "Slow"],
        index=0
    )
else:
    speech_rate = st.sidebar.slider(
        "Speech Rate",
        min_value=50,
        max_value=300,
        value=150,
        step=10
    )
    
    speech_volume = st.sidebar.slider(
        "Volume",
        min_value=0.0,
        max_value=1.0,
        value=0.9,
        step=0.1
    )

# Language override
manual_language = st.sidebar.selectbox(
    "Override Language Detection",
    ["Auto-detect"] + [f"{lang['display']} ({lang['name']})" for lang in INDIC_LANGUAGES.values()],
    index=0
)

# Main interface
st.subheader("📝 Enter Text")

# Text input area
input_text = st.text_area(
    "Enter text in any Indic language or English:",
    height=200,
    placeholder="यहाँ अपना टेक्स्ट लिखें... / Enter your text here... / আপনার লেখা এখানে লিখুন..."
)

# Sample texts for demonstration
with st.expander("📚 Sample Texts"):
    sample_texts = {
        "Hindi": "नमस्कार! मैं एक बुद्धिमान टेक्स्ट-टू-स्पीच सिस्टम हूँ। मैं हिंदी में बहुत अच्छी तरह से बोल सकता हूँ।",
        "Bengali": "নমস্কার! আমি একটি বুদ্ধিমান টেক্সট-টু-স্পিচ সিস্টেম। আমি বাংলায় খুব ভালভাবে কথা বলতে পারি।",
        "Tamil": "வணக்கம்! நான் ஒரு புத்திசாலித்தனமான உரையிலிருந்து பேச்சு அமைப்பு. நான் தமிழில் மிக நன்றாக பேச முடியும்.",
        "Telugu": "నమస్కారం! నేను ఒక తెలివైన టెక్స్ట్-టు-స్పీచ్ సిస్టెమ్. నేను తెలుగులో చాలా బాగా మాట్లాడగలను.",
        "English": "Hello! I am an intelligent text-to-speech system. I can speak very well in multiple Indian languages."
    }
    
    cols = st.columns(len(sample_texts))
    for i, (lang, text) in enumerate(sample_texts.items()):
        with cols[i]:
            if st.button(f"Use {lang} Sample", key=f"sample_{lang}"):
                st.session_state.sample_text = text
    
    if hasattr(st.session_state, 'sample_text'):
        input_text = st.text_area(
            "Enter text in any Indic language or English:",
            value=st.session_state.sample_text,
            height=200,
            key="updated_text_area"
        )

# Generate speech button
col1, col2 = st.columns([1, 1])

with col1:
    if st.button("🎤 Generate Speech", disabled=not input_text.strip()):
        if input_text.strip():
            with st.spinner("Detecting language and generating speech..."):
                
                # Detect language
                if manual_language == "Auto-detect":
                    detected_lang_code, detected_lang_name = detect_language(input_text)
                else:
                    # Extract language code from manual selection
                    lang_info = [lang for lang in INDIC_LANGUAGES.values() 
                               if f"{lang['display']} ({lang['name']})" == manual_language][0]
                    detected_lang_code = [code for code, info in INDIC_LANGUAGES.items() 
                                        if info == lang_info][0]
                    detected_lang_name = lang_info['name']
                
                st.session_state.detected_language = f"{detected_lang_name} ({INDIC_LANGUAGES[detected_lang_code]['display']})"
                
                # Generate speech
                audio_file = None
                
                if "Google TTS" in tts_engine and GTTS_AVAILABLE:
                    slow_speech = speech_speed == "Slow"
                    audio_file = generate_speech_gtts(input_text, detected_lang_code, slow_speech)
                elif PYTTSX3_AVAILABLE:
                    audio_file = generate_speech_pyttsx3(input_text, detected_lang_code, speech_rate, speech_volume)
                else:
                    st.error("No TTS engine available. Please install gtts or pyttsx3.")
                
                if audio_file:
                    st.session_state.audio_file_path = audio_file
                    st.success("✅ Speech generated successfully!")
                else:
                    st.error("❌ Failed to generate speech")

with col2:
    # Clear button
    if st.button("🗑️ Clear"):
        st.session_state.audio_file_path = None
        st.session_state.detected_language = None
        if hasattr(st.session_state, 'sample_text'):
            del st.session_state.sample_text
        st.experimental_rerun()

# Results section
if st.session_state.detected_language:
    st.subheader("🎯 Detection Results")
    st.info(f"**Detected Language:** {st.session_state.detected_language}")

if st.session_state.audio_file_path:
    st.subheader("🔊 Generated Speech")
    
    # Audio player
    try:
        with open(st.session_state.audio_file_path, 'rb') as f:
            audio_bytes = f.read()
        
        st.audio(audio_bytes, format='audio/mp3' if st.session_state.audio_file_path.endswith('.mp3') else 'audio/wav')
        
        # Download button
        st.markdown("### 💾 Download")
        filename = f"speech_{st.session_state.detected_language.split()[0].lower()}.mp3"
        download_link = create_audio_download_link(st.session_state.audio_file_path, filename)
        st.markdown(download_link, unsafe_allow_html=True)
        
    except Exception as e:
        st.error(f"Error playing audio: {str(e)}")

# Instructions
st.subheader("📋 How to Use")

with st.expander("🚀 Quick Start Guide"):
    st.markdown("""
    ### Quick Steps:
    
    1. **Enter Text**: Type or paste text in any Indic language or English
    2. **Choose Engine**: Select Google TTS (online, better quality) or System TTS (offline)
    3. **Adjust Settings**: Set speech speed, volume, or override language detection
    4. **Generate**: Click "Generate Speech" to create audio
    5. **Listen & Download**: Play the audio and download if needed
    
    ### Supported Languages:
    - **Hindi** (हिन्दी)
    - **Bengali** (বাংলা) 
    - **Tamil** (தமிழ்)
    - **Telugu** (తెలుగు)
    - **Marathi** (मराठी)
    - **Gujarati** (ગુજરાતી)
    - **Kannada** (ಕನ್ನಡ)
    - **Malayalam** (മലയാളം)
    - **Punjabi** (ਪੰਜਾਬੀ)
    - **Urdu** (اردو)
    - **English**
    - **Sanskrit** (संस्कृत)
    """)

with st.expander("💡 Tips for Better Results"):
    st.markdown("""
    ### Best Practices:
    
    **Text Input:**
    - Use proper punctuation for natural pauses
    - Avoid excessive special characters
    - Keep sentences reasonably short for better pronunciation
    
    **Language Detection:**
    - System automatically detects Indic scripts
    - Use manual override if detection is incorrect
    - Mixed language text will use the dominant language
    
    **Voice Quality:**
    - Google TTS: Better quality, requires internet
    - System TTS: Works offline, quality depends on system voices
    - Adjust speed for clarity (slower for complex text)
    
    **Common Issues:**
    - If no audio plays, check browser audio settings
    - For best results with Indic text, use proper Unicode fonts
    - Some rare words might not pronounce perfectly
    """)

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center'>
    <p><strong>Indic Text-to-Speech Converter</strong></p>
    <p>Built with ❤️ using Streamlit, gTTS, and pyttsx3</p>
    <p><em>Supporting multiple Indic languages with natural tonality</em></p>
</div>
""", unsafe_allow_html=True)

# Cleanup function
def cleanup_temp_files():
    if st.session_state.audio_file_path and os.path.exists(st.session_state.audio_file_path):
        try:
            os.unlink(st.session_state.audio_file_path)
        except:
            pass

import atexit
atexit.register(cleanup_temp_files)
