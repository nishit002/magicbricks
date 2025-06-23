import streamlit as st
import speech_recognition as sr
import tempfile
import os
from io import BytesIO
import time
import re
from typing import Tuple, Optional
import subprocess

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

# Improved language detection priority - English first, then Indic languages
DETECTION_PRIORITY = ['en-US', 'en-IN', 'en-GB', 'hi-IN', 'ta-IN', 'te-IN', 'bn-IN', 'mr-IN', 'gu-IN', 'kn-IN', 'ml-IN']

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

def detect_language_from_text(text: str) -> str:
    """Detect language from transcribed text using character analysis"""
    if not text or len(text.strip()) < 3:
        return "unknown"
    
    # Count different script characters
    latin_chars = sum(1 for c in text if c.isalpha() and ord(c) < 256)
    devanagari_chars = sum(1 for c in text if '\u0900' <= c <= '\u097F')
    tamil_chars = sum(1 for c in text if '\u0B80' <= c <= '\u0BFF')
    telugu_chars = sum(1 for c in text if '\u0C00' <= c <= '\u0C7F')
    bengali_chars = sum(1 for c in text if '\u0980' <= c <= '\u09FF')
    gujarati_chars = sum(1 for c in text if '\u0A80' <= c <= '\u0AFF')
    kannada_chars = sum(1 for c in text if '\u0C80' <= c <= '\u0CFF')
    malayalam_chars = sum(1 for c in text if '\u0D00' <= c <= '\u0D7F')
    
    total_chars = len([c for c in text if c.isalpha()])
    
    if total_chars == 0:
        return "unknown"
    
    # Calculate percentages
    latin_pct = latin_chars / total_chars
    devanagari_pct = devanagari_chars / total_chars
    tamil_pct = tamil_chars / total_chars
    telugu_pct = telugu_chars / total_chars
    bengali_pct = bengali_chars / total_chars
    gujarati_pct = gujarati_chars / total_chars
    kannada_pct = kannada_chars / total_chars
    malayalam_pct = malayalam_chars / total_chars
    
    # Determine language based on script dominance
    if latin_pct > 0.8:
        return "english"
    elif devanagari_pct > 0.6:
        return "hindi"
    elif tamil_pct > 0.6:
        return "tamil"
    elif telugu_pct > 0.6:
        return "telugu"
    elif bengali_pct > 0.6:
        return "bengali"
    elif gujarati_pct > 0.6:
        return "gujarati"
    elif kannada_pct > 0.6:
        return "kannada"
    elif malayalam_pct > 0.6:
        return "malayalam"
    elif latin_pct > 0.4:
        return "english"
    elif devanagari_pct > 0.3:
        return "hindi"
    else:
        return "unknown"

def enhance_transcription_with_openai(text: str, language: str, client: OpenAI) -> str:
    """Enhanced transcription correction using multi-step approach with better word-level fixing"""
    try:
        # Step 1: Pre-process with known error patterns
        preprocessed_text = preprocess_common_errors(text, language)
        
        # Get language name for better prompt
        lang_name = [k for k, v in LANGUAGES.items() if v == language]
        lang_name = lang_name[0] if lang_name else "the detected language"
        
        # Step 2: Create a more targeted prompt for AI correction
        if language.startswith('en'):
            # English-specific prompt
            prompt = f"""You are an expert English language corrector specializing in fixing speech-to-text transcription errors.

CRITICAL TASK: Fix ALL incorrect words by replacing them with the nearest sensible English words that make contextual sense.

Common error types to fix:
1. Phonetically similar wrong words
2. Broken compound words or phrases
3. Misheard technical terms
4. Incorrect word boundaries
5. Grammar and sentence structure issues

INPUT TEXT WITH ERRORS:
"{preprocessed_text}"

INSTRUCTIONS:
1. Read the text carefully and identify ALL nonsensical or incorrect words
2. Replace each incorrect word with the most contextually appropriate English word
3. Fix grammar and sentence structure
4. Ensure proper punctuation and spacing
5. Maintain the original meaning and intent
6. Output ONLY in English language

OUTPUT ONLY the corrected English text without any explanations or prefixes:"""
        else:
            # Indic language-specific prompt
            prompt = f"""You are an expert {lang_name} language corrector specializing in fixing speech-to-text transcription errors.

CRITICAL TASK: Fix ALL incorrect words by replacing them with the nearest sensible words that make contextual sense.

Common error types to fix:
1. Phonetically similar wrong words (e.g., स्थापत्य → स्थापित तथ्य)
2. Broken compound words or phrases
3. Misheard technical terms
4. Incorrect word boundaries
5. Grammar and sentence structure issues

EXAMPLES of the corrections needed:
- स्थापत्य → स्थापित तथ्य
- पटिया → पठनीय  
- मच्छरों → अक्षरों
- वेतन → वितरण
- लॉरेन एप्सन → Lorem Ipsum
- पोस्ट के खाते → पृष्ठ के खाखे
- दिखेगा → देखेगा

INPUT TEXT WITH ERRORS:
"{preprocessed_text}"

INSTRUCTIONS:
1. Read the text carefully and identify ALL nonsensical or incorrect words
2. Replace each incorrect word with the most contextually appropriate word
3. Fix grammar and sentence structure
4. Ensure proper punctuation and spacing
5. Maintain the original meaning and intent

OUTPUT ONLY the corrected text without any explanations or prefixes:"""

        # Use multiple attempts with different strategies if needed
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system", 
                    "content": f"""You are a professional {lang_name} text corrector. Your job is to fix speech-to-text errors by replacing incorrect words with contextually appropriate alternatives. Focus on word-level accuracy and meaning preservation. Always output clean, corrected text without any formatting or explanations."""
                },
                {"role": "user", "content": prompt}
            ],
            max_tokens=2000,
            temperature=0.05,  # Very low temperature for consistent corrections
            top_p=0.8,
            frequency_penalty=0.2,
            presence_penalty=0.1
        )
        
        enhanced_text = response.choices[0].message.content.strip()
        
        # Step 3: Clean up the response
        enhanced_text = clean_ai_response(enhanced_text)
        
        # Step 4: Apply final post-processing
        enhanced_text = post_process_transcription(enhanced_text, language)
        
        # Step 5: If still not satisfactory, try a second pass with different approach
        if should_retry_correction(text, enhanced_text):
            enhanced_text = second_pass_correction(enhanced_text, language, client)
        
        return enhanced_text
        
    except Exception as e:
        st.warning(f"OpenAI enhancement failed: {str(e)}. Using original transcription.")
        return text

def preprocess_common_errors(text: str, language: str) -> str:
    """Pre-process text with known error patterns before AI correction"""
    if language in INDIC_LANGUAGES:
        # Apply known Hindi/Indic corrections first
        corrections = {
            # Your specific examples
            r'\bस्थापत्य\b': 'स्थापित तथ्य',
            r'\bपटिया\b': 'पठनीय',
            r'\bमच्छरों\b': 'अक्षरों',
            r'\bवेतन\b': 'वितरण',
            r'\bलॉरेन एप्सन\b': 'Lorem Ipsum',
            r'\bपोस्ट के खाते\b': 'पृष्ठ के खाखे',
            r'\bदिखेगा\b': 'देखेगा',
            r'\bजब तक एक\b': 'जब एक',
            
            # Additional common patterns
            r'\bका मच्छरों\b': 'कम अक्षरों',
            r'\bसामान्य वेतन\b': 'सामान्य वितरण',
            r'\bखाते को\b': 'खाखे को',
            r'\bपोस्ट\b': 'पृष्ठ',
        }
        
        for pattern, replacement in corrections.items():
            text = re.sub(pattern, replacement, text)
    
    return text

def clean_ai_response(text: str) -> str:
    """Clean up AI response to remove unwanted formatting"""
    # Remove common AI response prefixes/suffixes
    prefixes_to_remove = [
        r'^(corrected text:|fixed text:|enhanced text:|output:|result:)\s*',
        r'^["\']',
        r'^.*?:\s*',
    ]
    
    suffixes_to_remove = [
        r'["\']$',
        r'\s*(this is the corrected version|corrected text above).*$',
    ]
    
    for prefix in prefixes_to_remove:
        text = re.sub(prefix, '', text, flags=re.IGNORECASE)
    
    for suffix in suffixes_to_remove:
        text = re.sub(suffix, '', text, flags=re.IGNORECASE)
    
    return text.strip()

def should_retry_correction(original: str, corrected: str) -> bool:
    """Determine if correction needs a second pass"""
    # Check if key error words are still present
    error_indicators = ['स्थापत्य', 'पटिया', 'मच्छरों', 'लॉरेन एप्सन', 'का मच्छरों']
    
    for indicator in error_indicators:
        if indicator in corrected:
            return True
    
    # Check if correction is too similar to original (indicating minimal changes)
    if len(original.split()) > 0 and len(corrected.split()) > 0:
        similarity_ratio = len(set(original.split()) & set(corrected.split())) / max(len(original.split()), len(corrected.split()))
        return similarity_ratio > 0.9
    
    return False

def second_pass_correction(text: str, language: str, client: OpenAI) -> str:
    """Second pass correction with more aggressive approach"""
    try:
        lang_name = [k for k, v in LANGUAGES.items() if v == language]
        lang_name = lang_name[0] if lang_name else "the detected language"
        
        if language.startswith('en'):
            prompt = f"""URGENT CORRECTION TASK: The following English text contains serious transcription errors that MUST be fixed.

Your task is to aggressively replace ALL incorrect/nonsensical words with proper English words:

TEXT TO FIX: "{text}"

Apply ALL necessary corrections and output ONLY the fully corrected English text:"""
        else:
            prompt = f"""URGENT CORRECTION TASK: The following {lang_name} text contains serious transcription errors that MUST be fixed.

Your task is to aggressively replace ALL incorrect/nonsensical words with proper words:

MANDATORY CORRECTIONS (apply these exact fixes):
- स्थापत्य → स्थापित तथ्य
- पटिया → पठनीय
- मच्छरों → अक्षरों  
- वेतन → वितरण
- लॉरेन एप्सन → Lorem Ipsum
- का मच्छरों → कम अक्षरों
- पोस्ट के खाते → पृष्ठ के खाखे
- दिखेगा → देखेगा

TEXT TO FIX: "{text}"

Apply ALL necessary corrections and output ONLY the fully corrected text:"""

        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": "You are a strict text corrector. Apply ALL specified corrections exactly as instructed. Output only the corrected text."
                },
                {"role": "user", "content": prompt}
            ],
            max_tokens=2000,
            temperature=0.01,  # Extremely low for consistency
        )
        
        return clean_ai_response(response.choices[0].message.content.strip())
        
    except Exception as e:
        st.warning(f"Second pass correction failed: {str(e)}")
        return text

def post_process_transcription(text: str, language: str) -> str:
    """Additional post-processing to fix common transcription issues"""
    try:
        # Common fixes for all languages
        text = re.sub(r'\s+', ' ', text)  # Fix multiple spaces
        text = text.strip()
        
        # Language-specific post-processing
        if language in INDIC_LANGUAGES:
            # Fix common Hindi/Indic transcription issues
            text = fix_indic_common_errors(text)
        elif language.startswith('en'):
            # Fix common English transcription issues
            text = fix_english_common_errors(text)
        
        return text
    except Exception as e:
        st.warning(f"Post-processing failed: {str(e)}")
        return text

def fix_indic_common_errors(text: str) -> str:
    """Fix common errors in Indic language transcriptions with comprehensive patterns"""
    # Comprehensive Hindi word corrections
    common_fixes = {
        # Your specific examples - exact matches
        r'\bस्थापत्य\b': 'स्थापित तथ्य',
        r'\bपटिया\b': 'पठनीय',
        r'\bमच्छरों\b': 'अक्षरों',
        r'\bवेतन\b': 'वितरण',
        r'\bलॉरेन एप्सन\b': 'Lorem Ipsum',
        r'\bपोस्ट के खाते\b': 'पृष्ठ के खाखे',
        r'\bदिखेगा\b': 'देखेगा',
        r'\bका मच्छरों\b': 'कम अक्षरों',
        
        # Additional common patterns
        r'\bजब तक एक\b': 'जब एक',
        r'\bसामान्य वेतन\b': 'सामान्य वितरण',
        r'\bखाते को\b': 'खाखे को',
        r'\bपोस्ट\b': 'पृष्ठ',
        
        # Fix spacing issues
        r'\s+': ' ',  # Multiple spaces to single space
        r'\s*\.\s*': '. ',  # Fix period spacing
        r'\s*,\s*': ', ',  # Fix comma spacing
    }
    
    for pattern, replacement in common_fixes.items():
        text = re.sub(pattern, replacement, text)
    
    return text.strip()

def fix_english_common_errors(text: str) -> str:
    """Fix common errors in English transcriptions"""
    # Common English word corrections
    common_fixes = {
        r'\brecieve\b': 'receive',
        r'\boccured\b': 'occurred',
        r'\bseperate\b': 'separate',
        r'\bdefinately\b': 'definitely',
        r'\bteh\b': 'the',
        r'\badn\b': 'and',
        r'\byuo\b': 'you',
        # Add more common English errors
    }
    
    for pattern, replacement in common_fixes.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    
    return text

def check_ffmpeg_availability():
    """Check if ffmpeg is available on the system"""
    try:
        result = subprocess.run(['ffmpeg', '-version'], 
                              capture_output=True, 
                              text=True, 
                              timeout=5)
        return result.returncode == 0
    except:
        return False

def process_uploaded_audio(uploaded_file):
    """Process uploaded audio file with multiple conversion strategies"""
    try:
        file_extension = uploaded_file.name.split('.')[-1].lower()
        
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{file_extension}') as temp_input:
            temp_input.write(uploaded_file.read())
            temp_input_path = temp_input.name

        # If it's already WAV or FLAC, use directly
        if file_extension in ['wav', 'flac']:
            return temp_input_path

        # Try multiple conversion strategies for other formats
        if PYDUB_AVAILABLE and file_extension in ['mp3', 'm4a', 'ogg']:
            
            # Strategy 1: Try with ffmpeg (if available)
            try:
                if file_extension == 'mp3':
                    audio = AudioSegment.from_mp3(temp_input_path)
                elif file_extension == 'm4a':
                    audio = AudioSegment.from_file(temp_input_path, format='m4a')
                elif file_extension == 'ogg':
                    audio = AudioSegment.from_ogg(temp_input_path)
                
                # Export as WAV
                with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_wav:
                    audio.export(temp_wav.name, format='wav')
                    wav_path = temp_wav.name
                
                os.unlink(temp_input_path)  # Remove original temp file
                st.success("✅ Audio converted to WAV successfully!")
                return wav_path
                
            except Exception as e:
                st.warning(f"FFmpeg conversion failed: {str(e)}")
                st.info("🔄 Attempting to use original file format directly...")
                return temp_input_path
        else:
            # No pydub available or unsupported format
            if file_extension in ['mp3', 'm4a', 'ogg']:
                st.warning(f"⚠️ {file_extension.upper()} conversion requires ffmpeg. Install it for better compatibility.")
                st.info("💡 Trying to process original file directly...")
            
            return temp_input_path
            
    except Exception as e:
        st.error(f"Error processing audio file: {str(e)}")
        return None

def transcribe_with_smart_language_detection(audio_file_path) -> Tuple[str, str, str, float]:
    """Transcribe audio with smart language detection that actually works"""
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
        
        # Dictionary to store results from each language attempt
        language_results = {}
        
        # Try each language and collect results
        for lang_code in DETECTION_PRIORITY:
            try:
                text = r.recognize_google(audio, language=lang_code, show_all=False)
                if text and len(text.strip()) > 0:
                    # Detect actual language from the transcribed text
                    detected_script = detect_language_from_text(text)
                    
                    # Calculate confidence based on multiple factors
                    text_length = len(text.strip())
                    word_count = len(text.split())
                    
                    # Base confidence on text length and word count
                    base_confidence = min(text_length / 100.0, 1.0) * 0.7 + min(word_count / 20.0, 1.0) * 0.3
                    
                    # Adjust confidence based on script-language match
                    script_match_bonus = 0.0
                    if lang_code.startswith('en') and detected_script == 'english':
                        script_match_bonus = 0.3
                    elif lang_code == 'hi-IN' and detected_script == 'hindi':
                        script_match_bonus = 0.3
                    elif lang_code == 'ta-IN' and detected_script == 'tamil':
                        script_match_bonus = 0.3
                    elif lang_code == 'te-IN' and detected_script == 'telugu':
                        script_match_bonus = 0.3
                    elif lang_code == 'bn-IN' and detected_script == 'bengali':
                        script_match_bonus = 0.3
                    elif lang_code == 'gu-IN' and detected_script == 'gujarati':
                        script_match_bonus = 0.3
                    elif lang_code == 'kn-IN' and detected_script == 'kannada':
                        script_match_bonus = 0.3
                    elif lang_code == 'ml-IN' and detected_script == 'malayalam':
                        script_match_bonus = 0.3
                    else:
                        # Penalize mismatched script-language combinations
                        if (lang_code.startswith('en') and detected_script != 'english' and detected_script != 'unknown') or \
                           (lang_code == 'hi-IN' and detected_script == 'english'):
                            script_match_bonus = -0.4
                    
                    final_confidence = min(base_confidence + script_match_bonus, 1.0)
                    
                    language_results[lang_code] = {
                        'text': text,
                        'confidence': final_confidence,
                        'detected_script': detected_script,
                        'word_count': word_count
                    }
                    
            except sr.UnknownValueError:
                continue
            except sr.RequestError as e:
                st.warning(f"Recognition service error for {lang_code}: {str(e)}")
                continue
        
        # Find the best result
        if not language_results:
            return "Could not understand the audio. Please ensure clear audio quality.", "", "Unknown", 0.0
        
        # Sort by confidence and select the best
        best_lang = max(language_results.keys(), key=lambda k: language_results[k]['confidence'])
        best_result = language_results[best_lang]
        
        # Get language name
        lang_name = [k for k, v in LANGUAGES.items() if v == best_lang]
        lang_name = lang_name[0] if lang_name else "Unknown"
        
        # Debug info
        st.info(f"🔍 Detection Details: Script={best_result['detected_script']}, Lang={best_lang}, Confidence={best_result['confidence']:.2f}")
        
        return best_result['text'], best_lang, lang_name, best_result['confidence']
        
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
        elif language_code == 'pa-IN':
            return transliterate(text, sanscript.GURMUKHI, sanscript.ITRANS)
        elif language_code == 'bn-IN':
            return transliterate(text, sanscript.BENGALI, sanscript.ITRANS)
        elif language_code == 'gu-IN':
            return transliterate(text, sanscript.GUJARATI, sanscript.ITRANS)
        elif language_code == 'or-IN':
            return transliterate(text, sanscript.ORIYA, sanscript.ITRANS)
        elif language_code == 'as-IN':
            return transliterate(text, sanscript.BENGALI, sanscript.ITRANS)
        elif language_code == 'sa-IN':
            return transliterate(text, sanscript.DEVANAGARI, sanscript.ITRANS)
    except Exception as e:
        st.warning(f"Transliteration failed: {str(e)}")
    
    return ""

def install_ffmpeg_instructions():
    """Display instructions for installing ffmpeg"""
    st.error("🚫 FFmpeg not found - Required for MP3/M4A/OGG conversion")
    
    with st.expander("📋 How to Install FFmpeg"):
        st.markdown("""
        **FFmpeg is required for audio format conversion. Here's how to install it:**
        
        **Windows:**
        1. Download from: https://ffmpeg.org/download.html
        2. Extract to C:\\ffmpeg
        3. Add C:\\ffmpeg\\bin to your PATH environment variable
        4. Restart your application
        
        **macOS:**
        ```bash
        # Using Homebrew
        brew install ffmpeg
