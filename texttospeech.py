import streamlit as st
import tempfile
import os
import re
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
    from parler_tts import ParlerTTSForConditionalGeneration
    from transformers import AutoTokenizer
    import soundfile as sf
    PARLER_TTS_AVAILABLE = True
except ImportError:
    PARLER_TTS_AVAILABLE = False

try:
    from gtts import gTTS
    GTTS_AVAILABLE = True
except ImportError:
    GTTS_AVAILABLE = False

# Configure page
st.set_page_config(
    page_title="Indic Parler-TTS",
    page_icon="🗣️",
    layout="wide"
)

st.title("🗣️ Indic Parler-TTS")
st.markdown("Advanced multilingual TTS with voice control for 21 languages!")

# Supported languages with their speakers
INDIC_PARLER_LANGUAGES = {
    'hi': {
        'name': 'Hindi', 'display': 'हिन्दी',
        'speakers': ['Rohit', 'Divya', 'Aman', 'Rani'],
        'recommended': ['Rohit', 'Divya']
    },
    'bn': {
        'name': 'Bengali', 'display': 'বাংলা',
        'speakers': ['Arjun', 'Aditi', 'Tapan', 'Rashmi', 'Arnav', 'Riya'],
        'recommended': ['Arjun', 'Aditi']
    },
    'te': {
        'name': 'Telugu', 'display': 'తెలుగు',
        'speakers': ['Prakash', 'Lalitha', 'Kiran'],
        'recommended': ['Prakash', 'Lalitha']
    },
    'ta': {
        'name': 'Tamil', 'display': 'தமிழ்',
        'speakers': ['Kavitha', 'Jaya'],
        'recommended': ['Jaya']
    },
    'mr': {
        'name': 'Marathi', 'display': 'मराठी',
        'speakers': ['Sanjay', 'Sunita', 'Nikhil', 'Radha', 'Varun', 'Isha'],
        'recommended': ['Sanjay', 'Sunita']
    },
    'gu': {
        'name': 'Gujarati', 'display': 'ગુજરાતી',
        'speakers': ['Yash', 'Neha'],
        'recommended': ['Yash', 'Neha']
    },
    'kn': {
        'name': 'Kannada', 'display': 'ಕನ್ನಡ',
        'speakers': ['Suresh', 'Anu', 'Chetan', 'Vidya'],
        'recommended': ['Suresh', 'Anu']
    },
    'ml': {
        'name': 'Malayalam', 'display': 'മലയാളം',
        'speakers': ['Anjali', 'Anju', 'Harish'],
        'recommended': ['Anjali', 'Harish']
    },
    'as': {
        'name': 'Assamese', 'display': 'অসমীয়া',
        'speakers': ['Amit', 'Sita', 'Poonam', 'Rakesh'],
        'recommended': ['Amit', 'Sita']
    },
    'or': {
        'name': 'Odia', 'display': 'ଓଡ଼ିଆ',
        'speakers': ['Manas', 'Debjani'],
        'recommended': ['Manas', 'Debjani']
    },
    'ur': {
        'name': 'Urdu', 'display': 'اردو',
        'speakers': [],  # Will use default description
        'recommended': []
    },
    'en': {
        'name': 'English', 'display': 'English',
        'speakers': ['Thoma', 'Mary', 'Swapna', 'Dinesh', 'Meera'],
        'recommended': ['Thoma', 'Mary']
    }
}

# Voice style presets
VOICE_STYLES = {
    'clear_female': "A female speaker delivers clear, expressive speech with moderate speed and pitch. The recording is of very high quality with no background noise.",
    'clear_male': "A male speaker delivers clear, expressive speech with moderate speed and pitch. The recording is of very high quality with no background noise.",
    'fast_energetic': "A speaker delivers energetic, fast-paced speech with high expressiveness. The recording is very clear with excellent quality.",
    'slow_calm': "A speaker delivers calm, slow-paced speech with a soothing tone. The recording is very clear and close-sounding.",
    'news_anchor': "A professional news anchor delivers speech with clear articulation and moderate pace. The recording is broadcast quality with no noise.",
    'conversational': "A speaker delivers conversational, slightly expressive speech with natural pace and warmth. The recording is very clear."
}

# Initialize session state
if 'audio_file_path' not in st.session_state:
    st.session_state.audio_file_path = None
if 'detected_language' not in st.session_state:
    st.session_state.detected_language = None
if 'generation_info' not in st.session_state:
    st.session_state.generation_info = ""

@st.cache_resource
def load_parler_model():
    """Load Parler-TTS model with caching"""
    try:
        if not PARLER_TTS_AVAILABLE:
            return None, None, None
        
        device = "cuda:0" if torch.cuda.is_available() else "cpu"
        
        model = ParlerTTSForConditionalGeneration.from_pretrained("ai4bharat/indic-parler-tts").to(device)
        tokenizer = AutoTokenizer.from_pretrained("ai4bharat/indic-parler-tts")
        description_tokenizer = AutoTokenizer.from_pretrained(model.config.text_encoder._name_or_path)
        
        return model, tokenizer, description_tokenizer
    except Exception as e:
        st.error(f"Failed to load Parler-TTS model: {str(e)}")
        return None, None, None

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
        elif re.search(r'[\u0600-\u06FF]', text):
            return 'ur', 'Urdu'
        
        # Use langdetect for English and fallback
        if LANGDETECT_AVAILABLE:
            try:
                detected = detect(text)
                if detected in INDIC_PARLER_LANGUAGES:
                    return detected, INDIC_PARLER_LANGUAGES[detected]['name']
            except:
                pass
        
        return 'en', 'English'  # Default to English
    except:
        return 'en', 'English'

def generate_voice_description(speaker_name: str, voice_style: str, language_code: str) -> str:
    """Generate voice description for Parler-TTS"""
    try:
        # Get base style
        base_description = VOICE_STYLES.get(voice_style, VOICE_STYLES['clear_female'])
        
        # Add speaker name if provided
        if speaker_name and speaker_name != "Auto":
            # Replace generic speaker with specific name
            description = base_description.replace("A female speaker", f"{speaker_name}")
            description = description.replace("A male speaker", f"{speaker_name}")
            description = description.replace("A speaker", f"{speaker_name}")
        else:
            description = base_description
        
        return description
    except:
        return VOICE_STYLES['clear_female']

def generate_parler_tts(text: str, description: str, model, tokenizer, description_tokenizer) -> Optional[str]:
    """Generate speech using Parler-TTS"""
    try:
        device = next(model.parameters()).device
        
        # Tokenize inputs
        description_input_ids = description_tokenizer(description, return_tensors="pt").to(device)
        prompt_input_ids = tokenizer(text, return_tensors="pt").to(device)
        
        # Generate audio
        with torch.no_grad():
            generation = model.generate(
                input_ids=description_input_ids.input_ids,
                attention_mask=description_input_ids.attention_mask,
                prompt_input_ids=prompt_input_ids.input_ids,
                prompt_attention_mask=prompt_input_ids.attention_mask
            )
        
        # Convert to audio
        audio_arr = generation.cpu().numpy().squeeze()
        
        # Save to file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
        sf.write(temp_file.name, audio_arr, model.config.sampling_rate)
        temp_file.close()
        
        return temp_file.name
        
    except Exception as e:
        st.error(f"Parler-TTS generation failed: {str(e)}")
        return None

def fallback_to_gtts(text: str, language_code: str) -> Optional[str]:
    """Fallback to Google TTS"""
    try:
        if not GTTS_AVAILABLE:
            return None
        
        # Map to gTTS codes
        gtts_mapping = {
            'hi': 'hi', 'bn': 'bn', 'te': 'te', 'ta': 'ta', 'mr': 'mr',
            'gu': 'gu', 'kn': 'kn', 'ml': 'ml', 'or': 'hi', 'as': 'bn', 
            'ur': 'ur', 'en': 'en'
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

# Load model
model, tokenizer, description_tokenizer = load_parler_model()

# Sidebar
st.sidebar.header("⚙️ Voice Settings")

# Show model status
if PARLER_TTS_AVAILABLE and model is not None:
    st.sidebar.success("✅ Indic Parler-TTS loaded")
    st.sidebar.info(f"Device: {'GPU' if torch.cuda.is_available() else 'CPU'}")
else:
    st.sidebar.error("❌ Parler-TTS not available")
    
    # Show specific error
    try:
        from parler_tts import ParlerTTSForConditionalGeneration
        st.sidebar.warning("⚠️ Parler-TTS installed but model failed to load")
    except ImportError:
        st.sidebar.error("📦 Parler-TTS not installed")
        st.sidebar.markdown("Run: `pip install git+https://github.com/huggingface/parler-tts.git`")
    
    if GTTS_AVAILABLE:
        st.sidebar.info("🔄 Using Google TTS fallback")

# Voice style selection
voice_style = st.sidebar.selectbox(
    "🎭 Voice Style",
    list(VOICE_STYLES.keys()),
    format_func=lambda x: x.replace('_', ' ').title(),
    index=0
)

# Manual language selection
manual_language = st.sidebar.selectbox(
    "🌐 Language (Optional)",
    ["Auto-detect"] + [f"{info['name']} ({info['display']})" for info in INDIC_PARLER_LANGUAGES.values()],
    index=0
)

# Speaker selection (only if language is manually selected)
selected_speaker = "Auto"
if manual_language != "Auto-detect":
    # Get language code from manual selection
    selected_lang_info = None
    for code, info in INDIC_PARLER_LANGUAGES.items():
        if f"{info['name']} ({info['display']})" == manual_language:
            selected_lang_info = info
            break
    
    if selected_lang_info and selected_lang_info['speakers']:
        selected_speaker = st.sidebar.selectbox(
            "🎤 Speaker",
            ["Auto"] + selected_lang_info['speakers'],
            index=0,
            help=f"Recommended: {', '.join(selected_lang_info['recommended'])}"
        )

# Show voice description preview
if st.sidebar.checkbox("📝 Show Voice Description"):
    preview_desc = generate_voice_description(selected_speaker, voice_style, 'hi')
    st.sidebar.text_area("Description Preview:", preview_desc, height=80, disabled=True)

# Main interface
input_text = st.text_area(
    "Enter text for speech generation:",
    height=150,
    placeholder="Type your text in any of the 21 supported languages..."
)

# Sample texts with various languages
with st.expander("📚 Try Sample Texts"):
    samples = {
        "Hindi News": "आज भारत में तकनीकी क्रांति का नया दौर शुरू हो रहा है। कृत्रिम बुद्धिमत्ता के क्षेत्र में हमारी उपलब्धियां विश्व स्तर पर पहचानी जा रही हैं।",
        "Bengali Story": "আজ সকালে আমি একটি অসাধারণ ঘটনার সাক্ষী হয়েছি। প্রযুক্তির জগতে নতুন আবিষ্কার মানুষের জীবনকে সহজ করে তুলছে।",
        "Tamil Poetry": "தமிழ் மொழியின் செழுமை என்றும் என் மனதில் நிற்கும். இன்றைய காலத்தில் தொழில்நুட்பம் நமது பாரம்பரியத்துடன் இணைந்து புதிய பாதைகளை உருவாக்குகிறது।",
        "Telugu Tech": "తెలుగు భాషలో మాట్లాడే కృత్రిమ మేధస్సు నేడు నిజమైంది। మన సంస్కృతి మరియు ఆధునిక సాంకేతికత కలిసి అద్భుతమైన ఫలితాలను ఇస్తున్నాయి।",
        "English AI": "The advancement of artificial intelligence in Indian languages represents a revolutionary step forward in making technology accessible to billions of people worldwide."
    }
    
    cols = st.columns(3)
    for i, (name, text) in enumerate(samples.items()):
        with cols[i % 3]:
            if st.button(f"📝 {name}", key=f"sample_{i}"):
                st.session_state.sample_text = text
    
    if hasattr(st.session_state, 'sample_text'):
        input_text = st.text_area(
            "Enter text for speech generation:",
            value=st.session_state.sample_text,
            height=150,
            key="updated_input"
        )

# Generate button
col1, col2 = st.columns([3, 1])

with col1:
    if st.button("🚀 Generate Speech", disabled=not input_text.strip(), type="primary"):
        if input_text.strip():
            with st.spinner("Generating high-quality speech with Parler-TTS..."):
                # Detect language
                if manual_language == "Auto-detect":
                    detected_lang_code, detected_lang_name = detect_language(input_text)
                else:
                    # Use manually selected language
                    for code, info in INDIC_PARLER_LANGUAGES.items():
                        if f"{info['name']} ({info['display']})" == manual_language:
                            detected_lang_code = code
                            detected_lang_name = info['name']
                            break
                
                st.session_state.detected_language = f"{detected_lang_name} ({INDIC_PARLER_LANGUAGES[detected_lang_code]['display']})"
                
                # Generate voice description
                speaker_to_use = selected_speaker if manual_language != "Auto-detect" else "Auto"
                description = generate_voice_description(speaker_to_use, voice_style, detected_lang_code)
                
                # Generate speech
                audio_file = None
                method_used = ""
                
                if PARLER_TTS_AVAILABLE and model is not None:
                    audio_file = generate_parler_tts(input_text, description, model, tokenizer, description_tokenizer)
                    method_used = "Indic Parler-TTS"
                
                # Fallback to Google TTS if Parler-TTS fails
                if not audio_file and GTTS_AVAILABLE:
                    st.info("🔄 Using Google TTS fallback...")
                    audio_file = fallback_to_gtts(input_text, detected_lang_code)
                    method_used = "Google TTS (Fallback)"
                
                if audio_file:
                    st.session_state.audio_file_path = audio_file
                    st.session_state.generation_info = f"{method_used} | Speaker: {speaker_to_use} | Style: {voice_style.replace('_', ' ').title()}"
                    st.success(f"✅ Speech generated using {method_used}!")
                else:
                    st.error("❌ Speech generation failed")

with col2:
    if st.button("🗑️ Clear"):
        for key in ['audio_file_path', 'detected_language', 'sample_text', 'generation_info']:
            if key in st.session_state:
                del st.session_state[key]
        st.experimental_rerun()

# Results
if st.session_state.detected_language:
    st.success(f"**🌐 Language:** {st.session_state.detected_language}")
    if st.session_state.generation_info:
        st.info(f"**ℹ️ Generation Info:** {st.session_state.generation_info}")

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
            file_name=f"parler_speech_{st.session_state.detected_language.split()[0].lower()}.{file_extension}",
            mime=audio_format
        )
        
    except Exception as e:
        st.error(f"Audio error: {str(e)}")

# Installation guide
with st.expander("🛠️ Setup Indic Parler-TTS"):
    st.markdown("""
    ### 🚨 Fix Parler-TTS Installation:
    
    **Step 1: Install Parler-TTS**
    ```bash
    pip install git+https://github.com/huggingface/parler-tts.git
    ```
    
    **Step 2: Install dependencies**
    ```bash
    pip install torch>=1.9.0 transformers>=4.40.0 soundfile accelerate
    ```
    
    **Step 3: Test installation**
    ```python
    # Test in Python console:
    try:
        from parler_tts import ParlerTTSForConditionalGeneration
        print("✅ Parler-TTS installed successfully!")
    except ImportError as e:
        print(f"❌ Error: {e}")
    ```
    
    **Step 4: Download model (first time)**
    ```python
    # This downloads ~1GB model
    from parler_tts import ParlerTTSForConditionalGeneration
    model = ParlerTTSForConditionalGeneration.from_pretrained("ai4bharat/indic-parler-tts")
    ```
    
    **Alternative Installation:**
    ```bash
    # If git install fails, try:
    git clone https://github.com/huggingface/parler-tts.git
    cd parler-tts
    pip install -e .
    ```
    
    **Troubleshooting:**
    - Make sure you have Python 3.8+
    - Install PyTorch first: `pip install torch`
    - Use `--upgrade` flag if needed
    - Restart your app after installation
    """)

# Language and speaker information
with st.expander("🌐 Supported Languages & Speakers"):
    st.markdown("### Languages with Available Speakers:")
    
    for code, info in INDIC_PARLER_LANGUAGES.items():
        if info['speakers']:
            st.write(f"**{info['name']} ({info['display']}):**")
            st.write(f"- All speakers: {', '.join(info['speakers'])}")
            st.write(f"- Recommended: {', '.join(info['recommended'])}")
            st.write("")

# Cleanup
def cleanup_temp_files():
    if st.session_state.audio_file_path and os.path.exists(st.session_state.audio_file_path):
        try:
            os.unlink(st.session_state.audio_file_path)
        except:
            pass

import atexit
atexit.register(cleanup_temp_files)
