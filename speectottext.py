import streamlit as st
import speech_recognition as sr
import pyaudio
import wave
import tempfile
import os
from io import BytesIO
import time

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
if 'recording' not in st.session_state:
    st.session_state.recording = False
if 'recorded_audio' not in st.session_state:
    st.session_state.recorded_audio = None
if 'transcription' not in st.session_state:
    st.session_state.transcription = ""

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

# Audio recording parameters
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100

def record_audio(duration=5):
    """Record audio for specified duration"""
    try:
        p = pyaudio.PyAudio()
        
        stream = p.open(format=FORMAT,
                       channels=CHANNELS,
                       rate=RATE,
                       input=True,
                       frames_per_buffer=CHUNK)
        
        st.info(f"🔴 Recording for {duration} seconds...")
        
        frames = []
        for i in range(0, int(RATE / CHUNK * duration)):
            data = stream.read(CHUNK)
            frames.append(data)
        
        stream.stop_stream()
        stream.close()
        p.terminate()
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp_file:
            wf = wave.open(tmp_file.name, 'wb')
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(p.get_sample_size(FORMAT))
            wf.setframerate(RATE)
            wf.writeframes(b''.join(frames))
            wf.close()
            
            return tmp_file.name
            
    except Exception as e:
        st.error(f"Error recording audio: {str(e)}")
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
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("🎙️ Record Audio")
    
    # Recording duration slider
    duration = st.slider("Recording Duration (seconds)", 1, 30, 5)
    
    # Record button
    if st.button("🔴 Start Recording", disabled=st.session_state.recording):
        st.session_state.recording = True
        audio_file = record_audio(duration)
        
        if audio_file:
            st.session_state.recorded_audio = audio_file
            st.success("✅ Recording completed!")
        
        st.session_state.recording = False
    
    # File upload option
    st.subheader("📁 Or Upload Audio File")
    uploaded_file = st.file_uploader(
        "Choose an audio file",
        type=['wav', 'mp3', 'flac', 'm4a'],
        help="Supported formats: WAV, MP3, FLAC, M4A"
    )
    
    if uploaded_file is not None:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{uploaded_file.name.split(".")[-1]}') as tmp_file:
            tmp_file.write(uploaded_file.read())
            st.session_state.recorded_audio = tmp_file.name
        st.success("✅ File uploaded successfully!")

with col2:
    st.subheader("📝 Transcription")
    
    # Transcribe button
    if st.button("🔄 Transcribe Audio", disabled=not st.session_state.recorded_audio):
        if st.session_state.recorded_audio:
            with st.spinner("Transcribing audio..."):
                language_code = LANGUAGES[selected_language]
                transcription = transcribe_audio(
                    st.session_state.recorded_audio,
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
if st.session_state.recorded_audio:
    st.subheader("🔊 Recorded Audio")
    try:
        with open(st.session_state.recorded_audio, 'rb') as audio_file:
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
3. **Record Audio**: Click "Start Recording" and speak clearly
4. **Or Upload File**: Upload an existing audio file
5. **Transcribe**: Click "Transcribe Audio" to convert speech to text
6. **Copy/Download**: Use the transcribed text as needed

**Tips for better results:**
- Speak clearly and at a moderate pace
- Minimize background noise
- Use a good quality microphone
- Keep recordings under 1 minute for better accuracy
""")

# Footer
st.markdown("---")
st.markdown("Built with ❤️ using Streamlit and SpeechRecognition")

# Cleanup temporary files on app restart
def cleanup_temp_files():
    if st.session_state.recorded_audio and os.path.exists(st.session_state.recorded_audio):
        try:
            os.unlink(st.session_state.recorded_audio)
        except:
            pass

# Register cleanup function
import atexit
atexit.register(cleanup_temp_files)
