import streamlit as st
import speech_recognition as sr
import tempfile
import os
from indic_transliteration import sanscript
from indic_transliteration.sanscript import transliterate
from pydub import AudioSegment

# Configure page
st.set_page_config(page_title="Speech-to-Text", page_icon="🎤")

# Title
st.title("🎤 Speech-to-Text Converter")

# Indian language options
LANGUAGES = {
    'Hindi': 'hi-IN',
    'English (India)': 'en-IN',
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
if 'transliterated_text' not in st.session_state:
    st.session_state.transliterated_text = ""

# Process uploaded audio (WAV or MP3)
def process_uploaded_audio(uploaded_file):
    try:
        file_extension = uploaded_file.name.split('.')[-1].lower()
        temp_input = tempfile.NamedTemporaryFile(delete=False, suffix=f'.{file_extension}')
        temp_input.write(uploaded_file.read())
        temp_input.close()

        # Convert MP3 to WAV if needed
        if file_extension == 'mp3':
            audio = AudioSegment.from_mp3(temp_input.name)
            temp_wav = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
            audio.export(temp_wav.name, format='wav')
            temp_path = temp_wav.name
            os.unlink(temp_input.name)  # Remove MP3 temp file
        else:
            temp_path = temp_input.name

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
        
        # Prioritize Hindi, then try other languages
        for lang_name, lang_code in LANGUAGES.items():
            try:
                text = r.recognize_google(audio, language=lang_code)
                transliterated_text = transliterate(text, sanscript.DEVANAGARI, sanscript.ITRANS) if lang_code == 'hi-IN' else text
                return text, transliterated_text, lang_name
            except sr.UnknownValueError:
                continue
            except sr.RequestError as e:
                return f"Error with recognition service: {str(e)}", "", None
        
        # Retry with Hindi as fallback
        try:
            text = r.recognize_google(audio, language='hi-IN')
            transliterated_text = transliterate(text, sanscript.DEVANAGARI, sanscript.ITRANS)
            return text, transliterated_text, 'Hindi'
        except:
            return "Could not understand the audio.", "", None
    
    except Exception as e:
        return f"An error occurred: {str(e)}", "", None

# File upload
st.subheader("📁 Upload Audio")
st.markdown("Upload MP3 or WAV. MP3 will be converted to WAV automatically. Language will be detected for Indian languages.")
uploaded_file = st.file_uploader("Choose an audio file", type=['wav', 'mp3'])

if uploaded_file is not None:
    with st.spinner("Processing audio..."):
        processed_audio = process_uploaded_audio(uploaded_file)
        if processed_audio:
            st.session_state.uploaded_audio = processed_audio
            st.success("Audio processed successfully!")
            with open(processed_audio, 'rb') as f:
                st.audio(f.read(), format='audio/wav')

# Transcribe button
if st.button("🔄 Transcribe", disabled=not st.session_state.uploaded_audio):
    if st.session_state.uploaded_audio:
        with st.spinner("Transcribing with automatic language detection..."):
            transcription, transliterated_text, detected_language = transcribe_audio(st.session_state.uploaded_audio)
            st.session_state.transcription = transcription
            st.session_state.transliterated_text = transliterated_text
            st.session_state.detected_language = detected_language if detected_language else "Unknown"

# Display transcription
if st.session_state.transcription:
    st.subheader("📝 Transcription")
    if st.session_state.detected_language != "Unknown":
        st.write(f"Detected Language: {st.session_state.detected_language}")
    st.text_area("Transcribed Text (Native Script):", st.session_state.transcription, height=150)
    if st.session_state.transliterated_text and st.session_state.detected_language == "Hindi":
        st.text_area("Transcribed Text (Transliterated English):", st.session_state.transliterated_text, height=150)
    st.download_button(
        label="💾 Download Transcription",
        data=st.session_state.transcription,
        file_name="transcription.txt",
        mime="text/plain"
    )

# Instructions
st.subheader("📋 Instructions")
st.markdown("""
1. Upload an MP3 or WAV audio file.
2. Click "Transcribe" to convert speech to text.
3. The app will automatically detect the Indian language (Hindi prioritized).
4. View the transcription in native script and transliterated English (for Hindi).
5. Download the transcribed text if needed.

**Tips for Better Results:**
- Use high-quality MP3 or WAV audio.
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
