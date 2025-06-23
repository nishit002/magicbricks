import streamlit as st
import speech_recognition as sr
import tempfile
import os
from io import BytesIO
import time
import re
from typing import Tuple, Optional

# Import OpenAI with proper error handling
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
try:
    from indic_transliteration import sanscript
    from indic_transliteration.sanscript import transliterate
    TRANSLITERATION_AVAILABLE = True
except ImportError:
    TRANSLITERATION_AVAILABLE = False

try:
    from pydub import AudioSegment
    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False

# Configure page
st.set_page_config(
    page_title="AI-Enhanced Speech-to-Text",
    page_icon="🎤",
    layout="wide"
)

# Title and description
st.title("🎤 AI-Enhanced Speech-to-Text Converter")
st.markdown("Advanced speech recognition for English and Indic languages with OpenAI-powered quality enhancement!")

# Language options (Focused on English and Indic languages)
LANGUAGES = {
    # English variants
    'English (India)': 'en-IN',
    'English (US)': 'en-US',
    'English (UK)': 'en-GB',
    
    # Indian Languages
    'Hindi': 'hi-IN',
    'Tamil': 'ta-IN',
    'Telugu': 'te-IN',
    'Bengali': 'bn-IN',
    'Marathi': 'mr-IN',
    'Gujarati': 'gu-IN',
    'Kannada': 'kn-IN',
    'Malayalam': 'ml-IN',
    'Punjabi': 'pa-IN',
    'Urdu': 'ur-IN',
    'Odia': 'or-IN',
    'Assamese': 'as-IN',
    'Sanskrit': 'sa-IN'
}

# Language detection priority for auto-detection
DETECTION_PRIORITY = ['hi-IN', 'en-IN', 'en-US', 'ta-IN', 'te-IN', 'bn-IN', 'mr-IN', 'gu-IN', 'kn-IN', 'ml-IN']

# Indic languages for transliteration
INDIC_LANGUAGES = ['hi-IN', 'ta-IN', 'te-IN', 'bn-IN', 'mr-IN', 'gu-IN', 'kn-IN', 'ml-IN', 'pa-IN', 'or-IN', 'as-IN', 'sa-IN']

# Initialize session state
if 'transcription' not in st.session_state:
    st.session_state.transcription = ""
if 'enhanced_transcription' not in st.session_state:
    st.session_state.enhanced_transcription = ""
if 'uploaded_audio' not in st.session_state:
    st.session_state.uploaded_audio = None
if 'detected_language' not in st.session_state:
    st.session_state.detected_language = ""
if 'transliterated_text' not in st.session_state:
    st.session_state.transliterated_text = ""
if 'confidence_score' not in st.session_state:
    st.session_state.confidence_score = 0.0

def initialize_openai():
    """Initialize OpenAI client using Streamlit secrets"""
    try:
        # Get OpenAI API key from Streamlit secrets
        if "OPENAI_API_KEY" in st.secrets:
            client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
            return client
        else:
            st.error("OpenAI API key not found in secrets. Please add OPENAI_API_KEY to your Streamlit secrets.")
            return None
    except Exception as e:
        st.error(f"Failed to initialize OpenAI: {str(e)}")
        return None

def enhance_transcription_with_openai(text: str, language: str, client: OpenAI) -> str:
    """Enhance transcription using OpenAI for better accuracy and readability"""
    try:
        # Get language name for better prompt
        lang_name = [k for k, v in LANGUAGES.items() if v == language]
        lang_name = lang_name[0] if lang_name else "the detected language"
        
        # Create context-aware prompt
        prompt = f"""Please improve the following speech-to-text transcription in {lang_name}. 

Fix any spelling errors, grammar issues, and improve readability while maintaining the original meaning.
Handle fast speech patterns, unclear pronunciations, and common speech-to-text errors.
Ensure proper punctuation and sentence structure.
If the text contains mixed languages (code-switching), preserve that naturally.

Original transcription: "{text}"

Enhanced transcription:"""

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an expert language processing assistant specializing in improving speech-to-text transcriptions for English and Indian languages. Focus on accuracy, readability, and natural language flow."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000,
            temperature=0.3
        )
        
        enhanced_text = response.choices[0].message.content.strip()
        
        # Remove any quotes or formatting that might be added
        enhanced_text = re.sub(r'^["\']|["\']

def process_uploaded_audio(uploaded_file):
    """Process uploaded audio file and convert if needed"""
    try:
        file_extension = uploaded_file.name.split('.')[-1].lower()
        
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{file_extension}') as temp_input:
            temp_input.write(uploaded_file.read())
            temp_input_path = temp_input.name

        # Convert to WAV if needed and pydub is available
        if PYDUB_AVAILABLE and file_extension in ['mp3', 'm4a', 'ogg', 'flac']:
            try:
                if file_extension == 'mp3':
                    audio = AudioSegment.from_mp3(temp_input_path)
                elif file_extension == 'm4a':
                    audio = AudioSegment.from_file(temp_input_path, format='m4a')
                elif file_extension == 'ogg':
                    audio = AudioSegment.from_ogg(temp_input_path)
                elif file_extension == 'flac':
                    audio = AudioSegment.from_file(temp_input_path, format='flac')
                
                # Export as WAV
                with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_wav:
                    audio.export(temp_wav.name, format='wav')
                    wav_path = temp_wav.name
                
                os.unlink(temp_input_path)  # Remove original temp file
                return wav_path
                
            except Exception as e:
                st.warning(f"Audio conversion failed: {str(e)}. Trying with original file.")
                return temp_input_path
        else:
            return temp_input_path
            
    except Exception as e:
        st.error(f"Error processing audio file: {str(e)}")
        return None

def transcribe_with_language_detection(audio_file_path) -> Tuple[str, str, str, float]:
    """Transcribe audio with automatic language detection"""
    try:
        r = sr.Recognizer()
        
        # Optimize recognizer settings for better accuracy
        r.energy_threshold = 300
        r.dynamic_energy_threshold = True
        r.pause_threshold = 0.8
        r.operation_timeout = None
        r.phrase_threshold = 0.3
        r.non_speaking_duration = 0.8
        
        with sr.AudioFile(audio_file_path) as source:
            # Adjust for ambient noise with longer duration for better results
            r.adjust_for_ambient_noise(source, duration=1)
            audio = r.record(source)
        
        best_transcription = ""
        best_language = ""
        best_confidence = 0.0
        
        # Try languages in priority order
        for lang_code in DETECTION_PRIORITY:
            try:
                text = r.recognize_google(audio, language=lang_code, show_all=False)
                if text and len(text.strip()) > 0:
                    # Calculate confidence based on text length and language match
                    confidence = min(len(text.strip()) / 100.0, 1.0)
                    
                    if confidence > best_confidence:
                        best_transcription = text
                        best_language = lang_code
                        best_confidence = confidence
                        
                        # If we get a good result, use it
                        if confidence > 0.7:
                            break
                            
            except sr.UnknownValueError:
                continue
            except sr.RequestError as e:
                st.warning(f"Recognition service error for {lang_code}: {str(e)}")
                continue
        
        # If no good result found, try with remaining languages
        if best_confidence < 0.5:
            remaining_languages = [lang for lang in LANGUAGES.values() if lang not in DETECTION_PRIORITY]
            for lang_code in remaining_languages:
                try:
                    text = r.recognize_google(audio, language=lang_code, show_all=False)
                    if text and len(text.strip()) > len(best_transcription):
                        best_transcription = text
                        best_language = lang_code
                        best_confidence = min(len(text.strip()) / 100.0, 1.0)
                        break
                except:
                    continue
        
        if not best_transcription:
            return "Could not understand the audio. Please ensure clear audio quality.", "", "Unknown", 0.0
            
        # Get language name
        lang_name = [k for k, v in LANGUAGES.items() if v == best_language]
        lang_name = lang_name[0] if lang_name else "Unknown"
        
        return best_transcription, best_language, lang_name, best_confidence
        
    except Exception as e:
        return f"Transcription error: {str(e)}", "", "Unknown", 0.0

def generate_transliteration(text: str, language_code: str) -> str:
    """Generate transliteration for Indic languages"""
    if not TRANSLITERATION_AVAILABLE or language_code not in INDIC_LANGUAGES:
        return ""
    
    try:
        if language_code == 'hi-IN':
            # Hindi to Roman transliteration
            return transliterate(text, sanscript.DEVANAGARI, sanscript.ITRANS)
        elif language_code in ['ta-IN', 'te-IN', 'kn-IN', 'ml-IN']:
            # Other Indic scripts to Roman
            script_map = {
                'ta-IN': sanscript.TAMIL,
                'te-IN': sanscript.TELUGU,
                'kn-IN': sanscript.KANNADA,
                'ml-IN': sanscript.MALAYALAM
            }
            source_script = script_map.get(language_code, sanscript.DEVANAGARI)
            return transliterate(text, source_script, sanscript.ITRANS)
    except Exception as e:
        st.warning(f"Transliteration failed: {str(e)}")
    
    return ""

# Sidebar for settings
st.sidebar.header("⚙️ Settings")

# Mode selection
mode = st.sidebar.selectbox(
    "Recognition Mode",
    ["Auto-detect Language", "Manual Language Selection"],
    index=0
)

selected_language_code = None
if mode == "Manual Language Selection":
    selected_language = st.sidebar.selectbox(
        "Select Language",
        list(LANGUAGES.keys()),
        index=0
    )
    selected_language_code = LANGUAGES[selected_language]

# OpenAI Enhancement toggle
use_openai = st.sidebar.checkbox(
    "🤖 Enable AI Enhancement",
    value=True if OPENAI_AVAILABLE else False,
    disabled=not OPENAI_AVAILABLE,
    help="Use OpenAI to improve transcription quality, fix errors, and enhance readability"
)

# Audio quality settings
st.sidebar.subheader("Audio Settings")
audio_quality = st.sidebar.selectbox(
    "Expected Audio Quality",
    ["High Quality", "Medium Quality", "Low Quality/Noisy"],
    index=1
)

# Initialize OpenAI if enhancement is enabled
openai_client = None
if use_openai and OPENAI_AVAILABLE:
    openai_client = initialize_openai()
    if openai_client:
        st.sidebar.success("✅ OpenAI enhancement ready")
    else:
        st.sidebar.error("❌ OpenAI enhancement unavailable")
elif not OPENAI_AVAILABLE:
    st.sidebar.warning("⚠️ OpenAI library not installed")

# Main interface
st.subheader("📁 Upload Audio File")

# File upload with support for multiple formats
file_types = ['wav', 'flac']
if PYDUB_AVAILABLE:
    file_types.extend(['mp3', 'm4a', 'ogg'])

uploaded_file = st.file_uploader(
    "Choose an audio file to transcribe",
    type=file_types,
    help=f"Supported formats: {', '.join(file_types).upper()}"
)

# Process uploaded file
if uploaded_file is not None:
    with st.spinner("Processing audio file..."):
        processed_audio = process_uploaded_audio(uploaded_file)
        if processed_audio:
            st.session_state.uploaded_audio = processed_audio
            st.success("✅ Audio file processed successfully!")
            
            # Show audio player
            try:
                with open(processed_audio, 'rb') as f:
                    st.audio(f.read(), format='audio/wav')
            except:
                # Fallback to original file
                st.audio(uploaded_file.read(), format=f'audio/{uploaded_file.name.split(".")[-1]}')

# Recording instructions
with st.expander("🎙️ How to Record Audio"):
    st.markdown("""
    **For Best Results:**
    
    **Option 1: Online Voice Recorder**
    1. Visit: https://online-voice-recorder.com/
    2. Click "Record" and speak clearly
    3. Download as WAV or MP3
    4. Upload here
    
    **Option 2: Mobile Recording**
    1. Use your phone's voice recorder
    2. Record in a quiet environment
    3. Save as high-quality audio
    4. Transfer and upload here
    
    **Option 3: Computer Recording**
    1. Use Windows Voice Recorder or Mac Voice Memos
    2. Ensure good microphone quality
    3. Record in WAV format if possible
    
    **Tips for Better Recognition:**
    - Speak clearly and at normal pace
    - Minimize background noise
    - Use a good quality microphone
    - Avoid very fast speech (the AI will help correct it)
    - For Indic languages, natural speech patterns work best
    """)

# Transcription section
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("🔄 Transcription")
    
    # Transcribe button
    if st.button("🎯 Start Transcription", disabled=not st.session_state.uploaded_audio):
        if st.session_state.uploaded_audio:
            with st.spinner("Transcribing audio... This may take a moment."):
                
                if mode == "Auto-detect Language":
                    # Auto-detect language
                    transcription, detected_lang_code, detected_lang_name, confidence = transcribe_with_language_detection(
                        st.session_state.uploaded_audio
                    )
                    st.session_state.detected_language = detected_lang_name
                else:
                    # Use manually selected language
                    try:
                        r = sr.Recognizer()
                        r.energy_threshold = 300
                        r.dynamic_energy_threshold = True
                        
                        with sr.AudioFile(st.session_state.uploaded_audio) as source:
                            r.adjust_for_ambient_noise(source, duration=1)
                            audio = r.record(source)
                        
                        transcription = r.recognize_google(audio, language=selected_language_code)
                        detected_lang_code = selected_language_code
                        st.session_state.detected_language = selected_language
                        confidence = 0.8  # Assume good confidence for manual selection
                        
                    except sr.UnknownValueError:
                        transcription = "Could not understand the audio in the selected language."
                        detected_lang_code = selected_language_code
                        confidence = 0.0
                    except Exception as e:
                        transcription = f"Error: {str(e)}"
                        detected_lang_code = selected_language_code
                        confidence = 0.0
                
                st.session_state.transcription = transcription
                st.session_state.confidence_score = confidence
                
                # Generate transliteration for Indic languages
                if detected_lang_code in INDIC_LANGUAGES and transcription:
                    transliterated = generate_transliteration(transcription, detected_lang_code)
                    st.session_state.transliterated_text = transliterated
                else:
                    st.session_state.transliterated_text = ""
                
                # Enhance with OpenAI if enabled and available
                if use_openai and openai_client and transcription and not transcription.startswith("Error") and not transcription.startswith("Could not"):
                    with st.spinner("🤖 Enhancing transcription with AI..."):
                        enhanced = enhance_transcription_with_openai(transcription, detected_lang_code, openai_client)
                        st.session_state.enhanced_transcription = enhanced
                else:
                    st.session_state.enhanced_transcription = ""

with col2:
    st.subheader("⚙️ Transcription Details")
    
    if st.session_state.detected_language:
        st.info(f"**Detected Language:** {st.session_state.detected_language}")
    
    if st.session_state.confidence_score > 0:
        confidence_color = "🟢" if st.session_state.confidence_score > 0.7 else "🟡" if st.session_state.confidence_score > 0.4 else "🔴"
        st.info(f"**Confidence:** {confidence_color} {st.session_state.confidence_score:.1%}")

# Results section
if st.session_state.transcription:
    st.subheader("📝 Transcription Results")
    
    # Original transcription
    st.text_area(
        "Original Transcription:",
        st.session_state.transcription,
        height=120,
        key="original_transcription"
    )
    
    # Enhanced transcription (if available)
    if st.session_state.enhanced_transcription:
        st.text_area(
            "🤖 AI-Enhanced Transcription:",
            st.session_state.enhanced_transcription,
            height=120,
            key="enhanced_transcription"
        )
        
        # Comparison
        with st.expander("📊 Compare Original vs Enhanced"):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Original:**")
                st.write(st.session_state.transcription)
            with col2:
                st.markdown("**Enhanced:**")
                st.write(st.session_state.enhanced_transcription)
    
    # Transliteration (for Indic languages)
    if st.session_state.transliterated_text:
        st.text_area(
            "🔤 Transliterated Text (Roman):",
            st.session_state.transliterated_text,
            height=100,
            key="transliterated_text"
        )
    
    # Download options
    st.subheader("💾 Download Options")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.session_state.transcription:
            st.download_button(
                label="📄 Download Original",
                data=st.session_state.transcription,
                file_name="original_transcription.txt",
                mime="text/plain"
            )
    
    with col2:
        if st.session_state.enhanced_transcription:
            st.download_button(
                label="🤖 Download Enhanced",
                data=st.session_state.enhanced_transcription,
                file_name="enhanced_transcription.txt",
                mime="text/plain"
            )
    
    with col3:
        if st.session_state.transliterated_text:
            st.download_button(
                label="🔤 Download Transliterated",
                data=st.session_state.transliterated_text,
                file_name="transliterated_text.txt",
                mime="text/plain"
            )

# Instructions and tips
st.subheader("📋 Instructions & Tips")

tab1, tab2, tab3 = st.tabs(["🚀 Quick Start", "🎯 Best Practices", "🔧 Troubleshooting"])

with tab1:
    st.markdown("""
    ### Quick Start Guide:
    
    1. **Upload Audio**: Choose a WAV, MP3, or other supported audio file
    2. **Select Mode**: Auto-detect language or manually select
    3. **Enable AI Enhancement**: Toggle OpenAI enhancement for better results
    4. **Transcribe**: Click "Start Transcription" 
    5. **Review Results**: Check original, enhanced, and transliterated outputs
    6. **Download**: Save your preferred version
    
    ### Supported Languages:
    - **English**: US, UK, India variants
    - **Indic Languages**: Hindi, Tamil, Telugu, Bengali, Marathi, Gujarati, Kannada, Malayalam, Punjabi, Urdu, Odia, Assamese, Sanskrit
    """)

with tab2:
    st.markdown("""
    ### For Best Results:
    
    **Audio Quality:**
    - Use clear, high-quality recordings
    - Minimize background noise
    - Ensure good microphone placement
    - Avoid echoing environments
    
    **Speaking Tips:**
    - Speak at normal pace (AI will handle fast speech)
    - Use natural speech patterns
    - Pause between sentences
    - Speak clearly and distinctly
    
    **File Formats:**
    - WAV: Best quality and compatibility
    - MP3: Good compression, widely supported
    - FLAC: High quality, lossless compression
    - M4A: Good for mobile recordings
    
    **Language Mixing:**
    - Code-switching between languages is supported
    - AI enhancement preserves natural language mixing
    - Transliteration available for Indic scripts
    """)

with tab3:
    st.markdown("""
    ### Common Issues & Solutions:
    
    **"Could not understand audio":**
    - Check audio quality and volume
    - Try manual language selection
    - Ensure minimal background noise
    - Re-record with better microphone
    
    **Poor transcription quality:**
    - Enable AI enhancement
    - Try different language settings
    - Check if audio format is supported
    - Ensure clear pronunciation
    
    **Transliteration not working:**
    - Only available for Indic languages
    - Requires proper script detection
    - Works best with clear Indic text
    
    **OpenAI enhancement fails:**
    - Check internet connection
    - Try again after a moment
    - Original transcription still available
    - Enhancement is optional
    """)

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center'>
    <p><strong>AI-Enhanced Speech-to-Text Converter</strong></p>
    <p>Built with ❤️ using Streamlit, SpeechRecognition, and OpenAI</p>
    <p><em>Specialized for English and Indic languages with intelligent enhancement</em></p>
</div>
""", unsafe_allow_html=True)

# Cleanup function
def cleanup_temp_files():
    if st.session_state.uploaded_audio and os.path.exists(st.session_state.uploaded_audio):
        try:
            os.unlink(st.session_state.uploaded_audio)
        except:
            pass

import atexit
atexit.register(cleanup_temp_files), '', enhanced_text)
        
        return enhanced_text
        
    except Exception as e:
        st.warning(f"OpenAI enhancement failed: {str(e)}. Using original transcription.")
        return text

def process_uploaded_audio(uploaded_file):
    """Process uploaded audio file and convert if needed"""
    try:
        file_extension = uploaded_file.name.split('.')[-1].lower()
        
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{file_extension}') as temp_input:
            temp_input.write(uploaded_file.read())
            temp_input_path = temp_input.name

        # Convert to WAV if needed and pydub is available
        if PYDUB_AVAILABLE and file_extension in ['mp3', 'm4a', 'ogg', 'flac']:
            try:
                if file_extension == 'mp3':
                    audio = AudioSegment.from_mp3(temp_input_path)
                elif file_extension == 'm4a':
                    audio = AudioSegment.from_file(temp_input_path, format='m4a')
                elif file_extension == 'ogg':
                    audio = AudioSegment.from_ogg(temp_input_path)
                elif file_extension == 'flac':
                    audio = AudioSegment.from_file(temp_input_path, format='flac')
                
                # Export as WAV
                with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_wav:
                    audio.export(temp_wav.name, format='wav')
                    wav_path = temp_wav.name
                
                os.unlink(temp_input_path)  # Remove original temp file
                return wav_path
                
            except Exception as e:
                st.warning(f"Audio conversion failed: {str(e)}. Trying with original file.")
                return temp_input_path
        else:
            return temp_input_path
            
    except Exception as e:
        st.error(f"Error processing audio file: {str(e)}")
        return None

def transcribe_with_language_detection(audio_file_path) -> Tuple[str, str, str, float]:
    """Transcribe audio with automatic language detection"""
    try:
        r = sr.Recognizer()
        
        # Optimize recognizer settings for better accuracy
        r.energy_threshold = 300
        r.dynamic_energy_threshold = True
        r.pause_threshold = 0.8
        r.operation_timeout = None
        r.phrase_threshold = 0.3
        r.non_speaking_duration = 0.8
        
        with sr.AudioFile(audio_file_path) as source:
            # Adjust for ambient noise with longer duration for better results
            r.adjust_for_ambient_noise(source, duration=1)
            audio = r.record(source)
        
        best_transcription = ""
        best_language = ""
        best_confidence = 0.0
        
        # Try languages in priority order
        for lang_code in DETECTION_PRIORITY:
            try:
                text = r.recognize_google(audio, language=lang_code, show_all=False)
                if text and len(text.strip()) > 0:
                    # Calculate confidence based on text length and language match
                    confidence = min(len(text.strip()) / 100.0, 1.0)
                    
                    if confidence > best_confidence:
                        best_transcription = text
                        best_language = lang_code
                        best_confidence = confidence
                        
                        # If we get a good result, use it
                        if confidence > 0.7:
                            break
                            
            except sr.UnknownValueError:
                continue
            except sr.RequestError as e:
                st.warning(f"Recognition service error for {lang_code}: {str(e)}")
                continue
        
        # If no good result found, try with remaining languages
        if best_confidence < 0.5:
            remaining_languages = [lang for lang in LANGUAGES.values() if lang not in DETECTION_PRIORITY]
            for lang_code in remaining_languages:
                try:
                    text = r.recognize_google(audio, language=lang_code, show_all=False)
                    if text and len(text.strip()) > len(best_transcription):
                        best_transcription = text
                        best_language = lang_code
                        best_confidence = min(len(text.strip()) / 100.0, 1.0)
                        break
                except:
                    continue
        
        if not best_transcription:
            return "Could not understand the audio. Please ensure clear audio quality.", "", "Unknown", 0.0
            
        # Get language name
        lang_name = [k for k, v in LANGUAGES.items() if v == best_language]
        lang_name = lang_name[0] if lang_name else "Unknown"
        
        return best_transcription, best_language, lang_name, best_confidence
        
    except Exception as e:
        return f"Transcription error: {str(e)}", "", "Unknown", 0.0

def generate_transliteration(text: str, language_code: str) -> str:
    """Generate transliteration for Indic languages"""
    if not TRANSLITERATION_AVAILABLE or language_code not in INDIC_LANGUAGES:
        return ""
    
    try:
        if language_code == 'hi-IN':
            # Hindi to Roman transliteration
            return transliterate(text, sanscript.DEVANAGARI, sanscript.ITRANS)
        elif language_code in ['ta-IN', 'te-IN', 'kn-IN', 'ml-IN']:
            # Other Indic scripts to Roman
            script_map = {
                'ta-IN': sanscript.TAMIL,
                'te-IN': sanscript.TELUGU,
                'kn-IN': sanscript.KANNADA,
                'ml-IN': sanscript.MALAYALAM
            }
            source_script = script_map.get(language_code, sanscript.DEVANAGARI)
            return transliterate(text, source_script, sanscript.ITRANS)
    except Exception as e:
        st.warning(f"Transliteration failed: {str(e)}")
    
    return ""

# Sidebar for settings
st.sidebar.header("⚙️ Settings")

# Mode selection
mode = st.sidebar.selectbox(
    "Recognition Mode",
    ["Auto-detect Language", "Manual Language Selection"],
    index=0
)

selected_language_code = None
if mode == "Manual Language Selection":
    selected_language = st.sidebar.selectbox(
        "Select Language",
        list(LANGUAGES.keys()),
        index=0
    )
    selected_language_code = LANGUAGES[selected_language]

# OpenAI Enhancement toggle
use_openai = st.sidebar.checkbox(
    "🤖 Enable AI Enhancement",
    value=True,
    help="Use OpenAI to improve transcription quality, fix errors, and enhance readability"
)

# Audio quality settings
st.sidebar.subheader("Audio Settings")
audio_quality = st.sidebar.selectbox(
    "Expected Audio Quality",
    ["High Quality", "Medium Quality", "Low Quality/Noisy"],
    index=1
)

# Initialize OpenAI if enhancement is enabled
openai_ready = False
if use_openai:
    openai_ready = initialize_openai()
    if openai_ready:
        st.sidebar.success("✅ OpenAI enhancement ready")
    else:
        st.sidebar.error("❌ OpenAI enhancement unavailable")

# Main interface
st.subheader("📁 Upload Audio File")

# File upload with support for multiple formats
file_types = ['wav', 'flac']
if PYDUB_AVAILABLE:
    file_types.extend(['mp3', 'm4a', 'ogg'])

uploaded_file = st.file_uploader(
    "Choose an audio file to transcribe",
    type=file_types,
    help=f"Supported formats: {', '.join(file_types).upper()}"
)

# Process uploaded file
if uploaded_file is not None:
    with st.spinner("Processing audio file..."):
        processed_audio = process_uploaded_audio(uploaded_file)
        if processed_audio:
            st.session_state.uploaded_audio = processed_audio
            st.success("✅ Audio file processed successfully!")
            
            # Show audio player
            try:
                with open(processed_audio, 'rb') as f:
                    st.audio(f.read(), format='audio/wav')
            except:
                # Fallback to original file
                st.audio(uploaded_file.read(), format=f'audio/{uploaded_file.name.split(".")[-1]}')

# Recording instructions
with st.expander("🎙️ How to Record Audio"):
    st.markdown("""
    **For Best Results:**
    
    **Option 1: Online Voice Recorder**
    1. Visit: https://online-voice-recorder.com/
    2. Click "Record" and speak clearly
    3. Download as WAV or MP3
    4. Upload here
    
    **Option 2: Mobile Recording**
    1. Use your phone's voice recorder
    2. Record in a quiet environment
    3. Save as high-quality audio
    4. Transfer and upload here
    
    **Option 3: Computer Recording**
    1. Use Windows Voice Recorder or Mac Voice Memos
    2. Ensure good microphone quality
    3. Record in WAV format if possible
    
    **Tips for Better Recognition:**
    - Speak clearly and at normal pace
    - Minimize background noise
    - Use a good quality microphone
    - Avoid very fast speech (the AI will help correct it)
    - For Indic languages, natural speech patterns work best
    """)

# Transcription section
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("🔄 Transcription")
    
    # Transcribe button
    if st.button("🎯 Start Transcription", disabled=not st.session_state.uploaded_audio):
        if st.session_state.uploaded_audio:
            with st.spinner("Transcribing audio... This may take a moment."):
                
                if mode == "Auto-detect Language":
                    # Auto-detect language
                    transcription, detected_lang_code, detected_lang_name, confidence = transcribe_with_language_detection(
                        st.session_state.uploaded_audio
                    )
                    st.session_state.detected_language = detected_lang_name
                else:
                    # Use manually selected language
                    try:
                        r = sr.Recognizer()
                        r.energy_threshold = 300
                        r.dynamic_energy_threshold = True
                        
                        with sr.AudioFile(st.session_state.uploaded_audio) as source:
                            r.adjust_for_ambient_noise(source, duration=1)
                            audio = r.record(source)
                        
                        transcription = r.recognize_google(audio, language=selected_language_code)
                        detected_lang_code = selected_language_code
                        st.session_state.detected_language = selected_language
                        confidence = 0.8  # Assume good confidence for manual selection
                        
                    except sr.UnknownValueError:
                        transcription = "Could not understand the audio in the selected language."
                        detected_lang_code = selected_language_code
                        confidence = 0.0
                    except Exception as e:
                        transcription = f"Error: {str(e)}"
                        detected_lang_code = selected_language_code
                        confidence = 0.0
                
                st.session_state.transcription = transcription
                st.session_state.confidence_score = confidence
                
                # Generate transliteration for Indic languages
                if detected_lang_code in INDIC_LANGUAGES and transcription:
                    transliterated = generate_transliteration(transcription, detected_lang_code)
                    st.session_state.transliterated_text = transliterated
                else:
                    st.session_state.transliterated_text = ""
                
                # Enhance with OpenAI if enabled and available
                if use_openai and openai_ready and transcription and not transcription.startswith("Error") and not transcription.startswith("Could not"):
                    with st.spinner("🤖 Enhancing transcription with AI..."):
                        enhanced = enhance_transcription_with_openai(transcription, detected_lang_code)
                        st.session_state.enhanced_transcription = enhanced
                else:
                    st.session_state.enhanced_transcription = ""

with col2:
    st.subheader("⚙️ Transcription Details")
    
    if st.session_state.detected_language:
        st.info(f"**Detected Language:** {st.session_state.detected_language}")
    
    if st.session_state.confidence_score > 0:
        confidence_color = "🟢" if st.session_state.confidence_score > 0.7 else "🟡" if st.session_state.confidence_score > 0.4 else "🔴"
        st.info(f"**Confidence:** {confidence_color} {st.session_state.confidence_score:.1%}")

# Results section
if st.session_state.transcription:
    st.subheader("📝 Transcription Results")
    
    # Original transcription
    st.text_area(
        "Original Transcription:",
        st.session_state.transcription,
        height=120,
        key="original_transcription"
    )
    
    # Enhanced transcription (if available)
    if st.session_state.enhanced_transcription:
        st.text_area(
            "🤖 AI-Enhanced Transcription:",
            st.session_state.enhanced_transcription,
            height=120,
            key="enhanced_transcription"
        )
        
        # Comparison
        with st.expander("📊 Compare Original vs Enhanced"):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Original:**")
                st.write(st.session_state.transcription)
            with col2:
                st.markdown("**Enhanced:**")
                st.write(st.session_state.enhanced_transcription)
    
    # Transliteration (for Indic languages)
    if st.session_state.transliterated_text:
        st.text_area(
            "🔤 Transliterated Text (Roman):",
            st.session_state.transliterated_text,
            height=100,
            key="transliterated_text"
        )
    
    # Download options
    st.subheader("💾 Download Options")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.session_state.transcription:
            st.download_button(
                label="📄 Download Original",
                data=st.session_state.transcription,
                file_name="original_transcription.txt",
                mime="text/plain"
            )
    
    with col2:
        if st.session_state.enhanced_transcription:
            st.download_button(
                label="🤖 Download Enhanced",
                data=st.session_state.enhanced_transcription,
                file_name="enhanced_transcription.txt",
                mime="text/plain"
            )
    
    with col3:
        if st.session_state.transliterated_text:
            st.download_button(
                label="🔤 Download Transliterated",
                data=st.session_state.transliterated_text,
                file_name="transliterated_text.txt",
                mime="text/plain"
            )

# Instructions and tips
st.subheader("📋 Instructions & Tips")

tab1, tab2, tab3 = st.tabs(["🚀 Quick Start", "🎯 Best Practices", "🔧 Troubleshooting"])

with tab1:
    st.markdown("""
    ### Quick Start Guide:
    
    1. **Upload Audio**: Choose a WAV, MP3, or other supported audio file
    2. **Select Mode**: Auto-detect language or manually select
    3. **Enable AI Enhancement**: Toggle OpenAI enhancement for better results
    4. **Transcribe**: Click "Start Transcription" 
    5. **Review Results**: Check original, enhanced, and transliterated outputs
    6. **Download**: Save your preferred version
    
    ### Supported Languages:
    - **English**: US, UK, India variants
    - **Indic Languages**: Hindi, Tamil, Telugu, Bengali, Marathi, Gujarati, Kannada, Malayalam, Punjabi, Urdu, Odia, Assamese, Sanskrit
    """)

with tab2:
    st.markdown("""
    ### For Best Results:
    
    **Audio Quality:**
    - Use clear, high-quality recordings
    - Minimize background noise
    - Ensure good microphone placement
    - Avoid echoing environments
    
    **Speaking Tips:**
    - Speak at normal pace (AI will handle fast speech)
    - Use natural speech patterns
    - Pause between sentences
    - Speak clearly and distinctly
    
    **File Formats:**
    - WAV: Best quality and compatibility
    - MP3: Good compression, widely supported
    - FLAC: High quality, lossless compression
    - M4A: Good for mobile recordings
    
    **Language Mixing:**
    - Code-switching between languages is supported
    - AI enhancement preserves natural language mixing
    - Transliteration available for Indic scripts
    """)

with tab3:
    st.markdown("""
    ### Common Issues & Solutions:
    
    **"Could not understand audio":**
    - Check audio quality and volume
    - Try manual language selection
    - Ensure minimal background noise
    - Re-record with better microphone
    
    **Poor transcription quality:**
    - Enable AI enhancement
    - Try different language settings
    - Check if audio format is supported
    - Ensure clear pronunciation
    
    **Transliteration not working:**
    - Only available for Indic languages
    - Requires proper script detection
    - Works best with clear Indic text
    
    **OpenAI enhancement fails:**
    - Check internet connection
    - Try again after a moment
    - Original transcription still available
    - Enhancement is optional
    """)

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center'>
    <p><strong>AI-Enhanced Speech-to-Text Converter</strong></p>
    <p>Built with ❤️ using Streamlit, SpeechRecognition, and OpenAI</p>
    <p><em>Specialized for English and Indic languages with intelligent enhancement</em></p>
</div>
""", unsafe_allow_html=True)

# Cleanup function
def cleanup_temp_files():
    if st.session_state.uploaded_audio and os.path.exists(st.session_state.uploaded_audio):
        try:
            os.unlink(st.session_state.uploaded_audio)
        except:
            pass

import atexit
atexit.register(cleanup_temp_files)
