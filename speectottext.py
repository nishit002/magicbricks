import streamlit as st
import speech_recognition as sr
import tempfile
import os

# Configure page
st.set_page_config(page_title="Speech-to-Text", page_icon="🎤")

# Title
st.title("🎤 Speech-to-Text Converter")

# Indian language options
LANGUAGES = {
    'English (India)': 'en-IN',
    'Hindi': 'hi-IN',
    'Tamil': 'ta-IN',
    'Telugu': 'te-IN',
    'Bengali': 'bn-IN',
    'Marathi': 'mr-IN',
    'Gujarati': 'gu-IN',
    'Kannada': 'kn-IN',
    'Malayalam': 'ml-IN',
    'Punjabi': 'pa-IN'
}

# Initialize session state
if 'transcription' not in st.session_state:
    st.session_state.transcription = ""
if 'uploaded_audio' not in st.session_state:
    st.session_state.uploaded_audio = None
if 'detected_language' not in st.session_state:
    st.session_state.detected_language = ""

# Process uploaded audio
def process_uploaded_audio(uploaded_file):
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp_file:
            tmp_file.write(uploaded_file.read())
            temp_path = tmp_file.name
        return temp_path
    except Exception as e:
        st.error(f"Error processing audio: {str(e)}")
        return None

# Transcribe audio with automatic language detection
def transcribe_audio(audio_file_path):
    try:
        r = sr.Recognizer()
        with sr.AudioFile(audio_file_path) as source:
            r.adjust_for_ambient_noise(source)
            audio = r.record(source)
        
        # Try each language until successful transcription
        for lang_name, lang_code in LANGUAGES.items():
            try:
                text = r.recognize_google(audio, language=lang_code)
                return text, lang_name
            except sr.UnknownValueError:
                continue  # Try next language
            except sr.RequestError as e:
                return f"Error with recognition service: {str(e)}", None
        
        return "Could not understand the audio.", None
    
    except Exception as e:
        return f"An error occurred: {str(e)}", None

# File upload
st.subheader("📁 Upload Audio")
st.markdown("Language will be detected automatically for Indian languages.")
uploaded_file = st.file_uploader("Choose a WAV audio file", type=['wav'])

if uploaded_file is not None:
    with st.spinner("Processing audio..."):
        processed_audio = process_uploaded_audio(uploaded_file)
        if processed_audio:
            st.session_state.uploaded_audio = processed_audio
            st.success("Audio processed successfully!")
            st.audio(uploaded_file.read(), format='audio/wav')

# Transcribe button
if st.button("🔄 Transcribe", disabled=not st.session_state.uploaded_audio):
    if st.session_state.uploaded_audio:
        with st.spinner("Transcribing with automatic language detection..."):
            transcription, detected_language = transcribe_audio(st.session_state.uploaded_audio)
            st.session_state.transcription = transcription
            st.session_state.detected_language = detected_language if detected_language else "Unknown"

# Display transcription
if st.session_state.transcription:
    st.subheader("📝 Transcription")
    if st.session_state.detected_language != "Unknown":
        st.write(f"Detected Language: {st.session_state.detected_language}")
    st.text_area("Transcribed Text:", st.session_state.transcription, height=150)
    st.download_button(
        label="💾 Download Transcription",
        data=st.session_state.transcription,
        file_name="transcription.txt",
        mime="text/plain"
    )

# Instructions
st.subheader("📋 Instructions")
st.markdown("""
1. Upload a WAV audio file.
2. Click "Transcribe" to convert speech to text.
3. The app will automatically detect the Indian language.
4. Download the transcribed text if needed.

**Tips for Better Results:**
- Use WAV format audio.
- Record in a quiet environment.
- Speak clearly at a normal pace.
- Ensure minimal background noise.
""")

# Cleanup temporary files
def cleanup_temp_files():
    if st.session_state.uploaded_audio and os.path.exists(st.session_state.uploaded_audio):
        try:
            os.unlink(st.session_state.uploaded_audio)
        except:
            pass

import atexit
atexit.register(cleanup_temp_files)
