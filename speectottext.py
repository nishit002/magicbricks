import streamlit as st
import speech_recognition as sr
import tempfile
import os
from io import BytesIO
import time
from pydub import AudioSegment
from pydub.utils import make_chunks

# Configure page
st.set_page_config(
    page_title="Speech-to-Text Converter",
    page_icon="🎤",
    layout="wide"
)

# Title and description
st.title("🎤 Speech-to-Text Converter")
st.markdown("Record your voice and convert it to text in multiple languages!")

# Language options
LANGUAGES = {
    'English (US)': 'en-US',
    'English (UK)': 'en-GB',
    'Spanish': 'es-ES',
    'French': 'fr-FR',
    'German': 'de-DE',
    'Italian': 'it-IT',
    'Portuguese': 'pt-PT',
    'Russian': 'ru-RU',
    'Japanese': 'ja-JP',
    'Korean': 'ko-KR',
    'Chinese (Mandarin)': 'zh-CN',
    'Hindi': 'hi-IN',
    'Arabic': 'ar-SA'
}

# Initialize session state
if 'transcription' not in st.session_state:
    st.session_state.transcription = ""
if 'uploaded_audio' not in st.session_state:
    st.session_state.uploaded_audio = None

# Sidebar for settings
st.sidebar.header("Settings")
selected_language = st.sidebar.selectbox(
    "Select Language",
    list(LANGUAGES.keys()),
    index=0
)

recognition_engine = st.sidebar.selectbox(
    "Recognition Engine",
    ["Google", "Sphinx (Offline)"],
    index=0
)

# Audio recording parameters - Using browser's built-in recorder
def process_uploaded_audio(uploaded_file):
    """Process uploaded audio file and convert to WAV if needed"""
    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{uploaded_file.name.split(".")[-1]}') as tmp_file:
            tmp_file.write(uploaded_file.read())
            temp_path = tmp_file.name
        
        # Convert to WAV if needed using pydub
        file_extension = uploaded_file.name.split('.')[-1].lower()
        if file_extension != 'wav':
            audio = AudioSegment.from_file(temp_path)
            wav_path = temp_path.replace(f'.{file_extension}', '.wav')
            audio.export(wav_path, format='wav')
            os.unlink(temp_path)  # Remove original
            return wav_path
        
        return temp_path
        
    except Exception as e:
        st.error(f"Error processing audio file: {str(e)}")
        return None

def transcribe_audio(audio_file_path, language='en-US', engine='Google'):
    """Transcribe audio file to text"""
    try:
        r = sr.Recognizer()
        
        with sr.AudioFile(audio_file_path) as source:
            # Adjust for ambient noise
            r.adjust_for_ambient_noise(source)
            audio = r.record(source)
        
        if engine == 'Google':
            # Using Google Speech Recognition (free tier)
            text = r.recognize_google(audio, language=language)
        else:
            # Using offline Sphinx
            text = r.recognize_sphinx(audio, language=language)
            
        return text
        
    except sr.UnknownValueError:
        return "Could not understand the audio. Please try again."
    except sr.RequestError as e:
        return f"Error with the recognition service: {str(e)}"
    except Exception as e:
        return f"An error occurred: {str(e)}"

# Main interface
st.subheader("📁 Upload Audio File")

# File upload option
uploaded_file = st.file_uploader(
    "Choose an audio file to transcribe",
    type=['wav', 'mp3', 'flac', 'm4a', 'ogg', 'aac'],
    help="Supported formats: WAV, MP3, FLAC, M4A, OGG, AAC"
)

if uploaded_file is not None:
    with st.spinner("Processing audio file..."):
        processed_audio = process_uploaded_audio(uploaded_file)
        if processed_audio:
            st.session_state.uploaded_audio = processed_audio
            st.success("✅ Audio file processed successfully!")
            
            # Show audio player
            st.audio(uploaded_file.read(), format=f'audio/{uploaded_file.name.split(".")[-1]}')

# Browser-based recording option
st.subheader("🎙️ Record Audio (Browser)")
st.info("💡 Use your browser's built-in recording capabilities:")

# Instructions for browser recording
with st.expander("How to record audio in your browser"):
    st.markdown("""
    **Option 1: Use Online Voice Recorder**
    1. Visit: https://online-voice-recorder.com/
    2. Click "Record" and speak
    3. Download the audio file
    4. Upload it here
    
    **Option 2: Browser Extensions**
    - Chrome: "Voice Recorder" extension
    - Firefox: "Audio Recorder" extension
    
    **Option 3: Mobile Device**
    1. Use your phone's voice recorder app
    2. Save as audio file
    3. Upload here
    """)

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("⚙️ Transcription Settings")
    
    # Advanced options
    with st.expander("Advanced Options"):
        chunk_duration = st.slider("Process audio in chunks (seconds)", 10, 60, 30)
        show_confidence = st.checkbox("Show confidence scores (when available)")

with col2:
    st.subheader("📝 Transcription")
    
    # Transcribe button
    if st.button("🔄 Transcribe Audio", disabled=not st.session_state.uploaded_audio):
        if st.session_state.uploaded_audio:
            with st.spinner("Transcribing audio... This may take a moment."):
                language_code = LANGUAGES[selected_language]
                transcription = transcribe_audio(
                    st.session_state.uploaded_audio,
                    language_code,
                    recognition_engine
                )
                st.session_state.transcription = transcription
    
    # Display transcription
    if st.session_state.transcription:
        st.text_area(
            "Transcribed Text:",
            st.session_state.transcription,
            height=200,
            key="transcription_display"
        )
        
        # Copy to clipboard button
        if st.button("📋 Copy to Clipboard"):
            st.write("Text copied! (Use Ctrl+A, Ctrl+C to copy from the text area)")
        
        # Download transcription
        st.download_button(
            label="💾 Download Transcription",
            data=st.session_state.transcription,
            file_name="transcription.txt",
            mime="text/plain"
        )

# Audio player
if st.session_state.uploaded_audio:
    st.subheader("🔊 Processed Audio")
    try:
        with open(st.session_state.uploaded_audio, 'rb') as audio_file:
            audio_bytes = audio_file.read()
            st.audio(audio_bytes, format='audio/wav')
    except Exception as e:
        st.error(f"Error playing audio: {str(e)}")

# Instructions
st.subheader("📋 Instructions")
st.markdown("""
1. **Select Language**: Choose your preferred language from the sidebar
2. **Choose Recognition Engine**: 
   - Google: More accurate, requires internet
   - Sphinx: Works offline, less accurate
3. **Upload Audio**: Upload an audio file (WAV, MP3, FLAC, M4A, OGG, AAC)
4. **Or Record**: Use browser-based recording methods (see instructions above)
5. **Transcribe**: Click "Transcribe Audio" to convert speech to text
6. **Copy/Download**: Use the transcribed text as needed

**Tips for better results:**
- Ensure clear audio quality with minimal background noise
- Use supported audio formats
- For long audio files, the app will process them in chunks
- Google recognition requires internet but is more accurate
- Sphinx works offline but may be less accurate

**Supported Audio Formats:**
- WAV (recommended)
- MP3
- FLAC  
- M4A
- OGG
- AAC
""")

# Footer
st.markdown("---")
st.markdown("Built with ❤️ using Streamlit and SpeechRecognition")

# Cleanup temporary files on app restart
def cleanup_temp_files():
    if st.session_state.uploaded_audio and os.path.exists(st.session_state.uploaded_audio):
        try:
            os.unlink(st.session_state.uploaded_audio)
        except:
            pass

# Register cleanup function
import atexit
atexit.register(cleanup_temp_files)
