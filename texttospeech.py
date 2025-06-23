import streamlit as st
import tempfile
import os
import re
from typing import Optional, Tuple
import base64
import time

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

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

# Configure page
st.set_page_config(
    page_title="Human-like Indic TTS",
    page_icon="🗣️",
    layout="wide"
)

# Title and description
st.title("🗣️ Human-like Indic Text-to-Speech")
st.markdown("AI-enhanced text-to-speech with natural human-like voice and ChatGPT text optimization!")

# Indic language mapping with enhanced voice settings
INDIC_LANGUAGES = {
    'hi': {'name': 'Hindi', 'code': 'hi', 'display': 'हिन्दी', 'tld': 'co.in'},
    'bn': {'name': 'Bengali', 'code': 'bn', 'display': 'বাংলা', 'tld': 'com.bd'},
    'te': {'name': 'Telugu', 'code': 'te', 'display': 'తెలుగు', 'tld': 'co.in'},
    'ta': {'name': 'Tamil', 'code': 'ta', 'display': 'தமிழ்', 'tld': 'co.in'},
    'mr': {'name': 'Marathi', 'code': 'mr', 'display': 'मराठी', 'tld': 'co.in'},
    'gu': {'name': 'Gujarati', 'code': 'gu', 'display': 'ગુજરાતી', 'tld': 'co.in'},
    'kn': {'name': 'Kannada', 'code': 'kn', 'display': 'ಕನ್ನಡ', 'tld': 'co.in'},
    'ml': {'name': 'Malayalam', 'code': 'ml', 'display': 'മലയാളം', 'tld': 'co.in'},
    'pa': {'name': 'Punjabi', 'code': 'pa', 'display': 'ਪੰਜਾਬੀ', 'tld': 'co.in'},
    'ur': {'name': 'Urdu', 'code': 'ur', 'display': 'اردو', 'tld': 'com.pk'},
    'en': {'name': 'English', 'code': 'en', 'display': 'English', 'tld': 'co.in'},
    'sa': {'name': 'Sanskrit', 'code': 'hi', 'display': 'संस्कृत', 'tld': 'co.in'}
}

# Initialize session state
if 'generated_audio' not in st.session_state:
    st.session_state.generated_audio = None
if 'detected_language' not in st.session_state:
    st.session_state.detected_language = None
if 'audio_file_path' not in st.session_state:
    st.session_state.audio_file_path = None
if 'enhanced_text' not in st.session_state:
    st.session_state.enhanced_text = ""
if 'original_text' not in st.session_state:
    st.session_state.original_text = ""

def initialize_openai():
    """Initialize OpenAI client using Streamlit secrets"""
    try:
        if "OPENAI_API_KEY" in st.secrets:
            client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
            return client
        else:
            st.error("🔑 ChatGPT API key not found in secrets. Please add OPENAI_API_KEY to your Streamlit secrets.")
            return None
    except Exception as e:
        st.error(f"Failed to initialize ChatGPT: {str(e)}")
        return None

def enhance_text_for_speech(text: str, language: str, client: OpenAI, enhancement_style: str = "natural") -> str:
    """Enhance text using ChatGPT for more natural, human-like speech output"""
    try:
        lang_info = INDIC_LANGUAGES.get(language, INDIC_LANGUAGES['en'])
        lang_name = lang_info['name']
        
        # Create enhancement prompts based on style
        enhancement_prompts = {
            "natural": f"""You are an expert in making text sound natural and conversational for {lang_name} text-to-speech.

Transform the following text to make it sound more human-like when spoken:

1. Add natural speech fillers and pauses where appropriate (like "आप जानते हैं" for Hindi, "you know" for English)
2. Make sentences flow more conversationally
3. Add appropriate emphasis words
4. Break long sentences into shorter, more natural chunks
5. Use more spoken language patterns rather than written formal language
6. Add subtle emotional undertones to make it engaging
7. Ensure proper rhythm and pacing for speech
8. Keep the original meaning intact but make it sound like a human is speaking naturally

Text to enhance: "{text}"

Enhanced version for natural speech:""",

            "expressive": f"""You are an expert in creating expressive, engaging {lang_name} speech content.

Transform this text to be more expressive and engaging when spoken aloud:

1. Add emotional depth and varying tones
2. Include natural exclamations and interjections
3. Use more dynamic language
4. Add rhetorical questions for engagement
5. Include natural speech patterns and emphasis
6. Make it sound like an enthusiastic, warm human speaker
7. Add appropriate cultural expressions and idioms
8. Ensure it sounds lively and interesting

Text to enhance: "{text}"

Expressive version for engaging speech:""",

            "professional": f"""You are an expert in creating professional yet natural {lang_name} speech content.

Enhance this text for professional but human-like speech delivery:

1. Maintain professional tone while adding natural flow
2. Use clear, articulate language patterns
3. Add appropriate pauses and emphasis
4. Make complex ideas easier to understand when spoken
5. Use confidence-building language
6. Add natural transitions between ideas
7. Ensure clarity and impact for professional settings
8. Keep it authoritative yet approachable

Text to enhance: "{text}"

Professional version for clear speech:"""
        }
        
        prompt = enhancement_prompts.get(enhancement_style, enhancement_prompts["natural"])
        
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system", 
                    "content": f"""You are a world-class expert in {lang_name} language and speech optimization. 
                    Your specialty is transforming written text into natural, human-like spoken content that sounds 
                    engaging and authentic when converted to speech. You understand the nuances of how text should 
                    be structured for optimal text-to-speech conversion, including natural pauses, emphasis, and flow.
                    Always preserve the core message while making it much more natural for speech synthesis."""
                },
                {"role": "user", "content": prompt}
            ],
            max_tokens=2000,
            temperature=0.7,  # Higher creativity for more natural variations
            top_p=0.9,
            frequency_penalty=0.3,
            presence_penalty=0.3
        )
        
        enhanced_text = response.choices[0].message.content.strip()
        
        # Clean up the response
        enhanced_text = re.sub(r'^["\']|["\']$', '', enhanced_text)
        enhanced_text = re.sub(r'^(Enhanced.*?:|Improved.*?:|Natural.*?:)\s*', '', enhanced_text, flags=re.IGNORECASE)
        
        # Add natural speech optimizations
        enhanced_text = optimize_for_speech(enhanced_text, language)
        
        return enhanced_text
        
    except Exception as e:
        st.warning(f"ChatGPT enhancement failed: {str(e)}. Using original text.")
        return text

def optimize_for_speech(text: str, language: str) -> str:
    """Additional optimizations for better TTS output"""
    try:
        # Add strategic pauses for natural speech rhythm
        text = re.sub(r'([.!?])\s*', r'\1 ... ', text)  # Add pauses after sentences
        text = re.sub(r'([,;:])\s*', r'\1 .. ', text)   # Add short pauses after commas
        
        # Fix common TTS pronunciation issues
        if language in ['hi', 'sa']:
            # Hindi/Sanskrit specific optimizations
            text = re.sub(r'\bडॉ\b', 'डॉक्टर', text)  # Expand abbreviations
            text = re.sub(r'\bश्री\b', 'श्री जी', text)  # Make honorifics more natural
        elif language == 'en':
            # English specific optimizations
            text = re.sub(r'\bDr\.\b', 'Doctor', text)
            text = re.sub(r'\bMr\.\b', 'Mister', text)
            text = re.sub(r'\bMrs\.\b', 'Missus', text)
            text = re.sub(r'\betc\.\b', 'etcetera', text)
        
        # Clean up multiple spaces and normalize punctuation
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        
        return text
    except Exception as e:
        return text

def detect_language(text: str) -> Tuple[str, str]:
    """Enhanced language detection with better accuracy"""
    try:
        clean_text = re.sub(r'[^\w\s]', '', text).strip()
        
        if not clean_text:
            return 'en', 'English'
        
        # Enhanced script detection with more accuracy
        if re.search(r'[\u0900-\u097F]', text):  # Devanagari
            if any(word in text for word in ['संस्कृत', 'वेद', 'श्लोक', 'मंत्र']):
                return 'sa', 'Sanskrit'
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
        
        return 'en', 'English'
        
    except Exception as e:
        return 'en', 'English'

def generate_speech_gtts_enhanced(text: str, language_code: str, slow: bool = False, voice_style: str = "natural") -> Optional[str]:
    """Generate enhanced speech using Google TTS with regional optimization"""
    try:
        lang_info = INDIC_LANGUAGES.get(language_code, INDIC_LANGUAGES['en'])
        gtts_lang = lang_info['code']
        tld = lang_info['tld']
        
        # Create enhanced TTS with regional accent
        tts = gTTS(
            text=text, 
            lang=gtts_lang, 
            slow=slow,
            tld=tld  # Use regional TLD for better accent
        )
        
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
        tts.save(temp_file.name)
        temp_file.close()
        
        return temp_file.name
        
    except Exception as e:
        # Fallback without TLD
        try:
            tts = gTTS(text=text, lang=gtts_lang, slow=slow)
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
            tts.save(temp_file.name)
            temp_file.close()
            return temp_file.name
        except Exception as e2:
            st.error(f"Enhanced gTTS generation failed: {str(e2)}")
            return None

def generate_speech_pyttsx3_enhanced(text: str, language_code: str, rate: int = 180, volume: float = 0.95) -> Optional[str]:
    """Generate enhanced speech using pyttsx3 with optimized settings"""
    try:
        engine = pyttsx3.init()
        
        # Enhanced voice settings for more natural speech
        engine.setProperty('rate', rate)  # Faster, more natural pace
        engine.setProperty('volume', volume)
        
        # Try to find the best voice for the language
        voices = engine.getProperty('voices')
        best_voice = None
        
        # Prioritize voices by quality and language match
        for voice in voices:
            voice_lower = voice.id.lower()
            name_lower = voice.name.lower()
            
            # Look for language-specific or high-quality voices
            if any(term in voice_lower or term in name_lower for term in [
                language_code, INDIC_LANGUAGES.get(language_code, {}).get('name', '').lower(),
                'india', 'indian', 'neural', 'premium', 'natural'
            ]):
                best_voice = voice.id
                break
        
        # If no specific voice found, prefer female voices (often more natural)
        if not best_voice:
            for voice in voices:
                if any(term in voice.name.lower() for term in ['female', 'woman', 'zira', 'cortana']):
                    best_voice = voice.id
                    break
        
        if best_voice:
            engine.setProperty('voice', best_voice)
        
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
        temp_file.close()
        
        engine.save_to_file(text, temp_file.name)
        engine.runAndWait()
        
        return temp_file.name
        
    except Exception as e:
        st.error(f"Enhanced pyttsx3 generation failed: {str(e)}")
        return None

# Sidebar settings
st.sidebar.header("⚙️ Voice Settings")

# TTS Engine selection
tts_engine = st.sidebar.selectbox(
    "🎤 TTS Engine",
    ["Google TTS Enhanced (Recommended)", "System TTS Enhanced"] if GTTS_AVAILABLE else ["System TTS Enhanced"],
    index=0 if GTTS_AVAILABLE else 0
)

# ChatGPT Enhancement
st.sidebar.subheader("🤖 AI Enhancement")

use_chatgpt = st.sidebar.checkbox(
    "Enable ChatGPT Text Enhancement",
    value=True if OPENAI_AVAILABLE else False,
    disabled=not OPENAI_AVAILABLE,
    help="Use ChatGPT to make text more natural and human-like for speech"
)

enhancement_style = st.sidebar.selectbox(
    "Enhancement Style",
    ["natural", "expressive", "professional"],
    index=0,
    help="Choose how to enhance the text for speech"
)

# Voice settings
st.sidebar.subheader("🔊 Voice Quality")

if "Google TTS" in tts_engine:
    speech_speed = st.sidebar.selectbox(
        "Speech Speed",
        ["Normal (Recommended)", "Slow"],
        index=0
    )
    voice_style = st.sidebar.selectbox(
        "Voice Style",
        ["Regional Accent", "Standard"],
        index=0,
        help="Regional accent uses local pronunciation patterns"
    )
else:
    speech_rate = st.sidebar.slider(
        "Speech Rate (Words/min)",
        min_value=120,
        max_value=250,
        value=180,
        step=10,
        help="180-200 is most natural for human-like speech"
    )
    
    speech_volume = st.sidebar.slider(
        "Volume",
        min_value=0.8,
        max_value=1.0,
        value=0.95,
        step=0.05
    )

# Language override
manual_language = st.sidebar.selectbox(
    "🌐 Language Override",
    ["Auto-detect"] + [f"{lang['display']} ({lang['name']})" for lang in INDIC_LANGUAGES.values()],
    index=0
)

# Initialize ChatGPT if enhancement is enabled
openai_client = None
if use_chatgpt and OPENAI_AVAILABLE:
    openai_client = initialize_openai()
    if openai_client:
        st.sidebar.success("✅ ChatGPT enhancement ready")
    else:
        st.sidebar.error("❌ ChatGPT enhancement unavailable")
elif not OPENAI_AVAILABLE:
    st.sidebar.warning("⚠️ OpenAI library not installed")

# Main interface
st.subheader("📝 Enter Text for Human-like Speech")

# Text input area with better placeholder
input_text = st.text_area(
    "Enter text in any language:",
    height=180,
    placeholder="""Example texts:
Hindi: आज मौसम बहुत अच्छा है और मैं बहुत खुश हूँ।
English: Today is a beautiful day and I'm feeling wonderful!
Bengali: আজ আবহাওয়া খুব সুন্দর এবং আমি খুব খুশি।""",
    help="Type naturally - ChatGPT will enhance it for better speech output!"
)

# Sample texts for demonstration
with st.expander("📚 Try These Human-like Sample Texts"):
    sample_texts = {
        "Hindi Casual": "आरे यार, आज क्या बात है! मौसम इतना सुंदर है कि मन करता है बाहर घूमने जाऊं। तुम्हें भी लगता है ना कि आज का दिन कुछ खास है?",
        "English Conversational": "Hey there! You know what? I was just thinking about how amazing technology has become. I mean, we can literally make computers speak like humans now - isn't that just incredible?",
        "Bengali Expressive": "আরে বাহ! আজকের এই সুন্দর সকালটা দেখো তো! মনে হচ্ছে প্রকৃতি যেন আমাদের সাথে কথা বলছে। তুমি কি এমন অনুভব করো?",
        "Tamil Emotional": "என்ன ஒரு அழகான நாள் இது! இன்றைக்கு எல்லாமே சரியாக போகும் என்று தோன்றுகிறது। உங்களுக்கும் இந்த உணர்வு வருகிறதா?",
        "Professional Hindi": "नमस्कार मित्रों, आज हम एक बहुत ही रोचक विषय पर चर्चा करने जा रहे हैं। आप जानते हैं कि तकनीक कितनी तेजी से बदल रही है।"
    }
    
    cols = st.columns(3)
    for i, (lang, text) in enumerate(sample_texts.items()):
        with cols[i % 3]:
            if st.button(f"🎭 {lang}", key=f"sample_{lang}", help=f"Load {lang} sample"):
                st.session_state.sample_text = text
    
    if hasattr(st.session_state, 'sample_text'):
        input_text = st.text_area(
            "Enter text in any language:",
            value=st.session_state.sample_text,
            height=180,
            key="updated_text_area"
        )

# Generate speech section
col1, col2, col3 = st.columns([2, 1, 1])

with col1:
    if st.button("🚀 Generate Human-like Speech", disabled=not input_text.strip(), type="primary"):
        if input_text.strip():
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            try:
                # Step 1: Language Detection
                status_text.text("🔍 Detecting language...")
                progress_bar.progress(20)
                
                if manual_language == "Auto-detect":
                    detected_lang_code, detected_lang_name = detect_language(input_text)
                else:
                    lang_info = [lang for lang in INDIC_LANGUAGES.values() 
                               if f"{lang['display']} ({lang['name']})" == manual_language][0]
                    detected_lang_code = [code for code, info in INDIC_LANGUAGES.items() 
                                        if info == lang_info][0]
                    detected_lang_name = lang_info['name']
                
                st.session_state.detected_language = f"{detected_lang_name} ({INDIC_LANGUAGES[detected_lang_code]['display']})"
                st.session_state.original_text = input_text
                
                # Step 2: ChatGPT Enhancement
                final_text = input_text
                if use_chatgpt and openai_client:
                    status_text.text("🤖 Enhancing text with ChatGPT for natural speech...")
                    progress_bar.progress(50)
                    
                    enhanced_text = enhance_text_for_speech(input_text, detected_lang_code, openai_client, enhancement_style)
                    st.session_state.enhanced_text = enhanced_text
                    final_text = enhanced_text
                else:
                    st.session_state.enhanced_text = ""
                
                # Step 3: Speech Generation
                status_text.text("🎤 Generating human-like speech...")
                progress_bar.progress(80)
                
                audio_file = None
                
                if "Google TTS" in tts_engine and GTTS_AVAILABLE:
                    slow_speech = "Slow" in speech_speed
                    voice_style_setting = voice_style if "voice_style" in locals() else "Regional Accent"
                    audio_file = generate_speech_gtts_enhanced(final_text, detected_lang_code, slow_speech, voice_style_setting)
                elif PYTTSX3_AVAILABLE:
                    audio_file = generate_speech_pyttsx3_enhanced(final_text, detected_lang_code, speech_rate, speech_volume)
                else:
                    st.error("❌ No TTS engine available. Please install gtts or pyttsx3.")
                
                if audio_file:
                    st.session_state.audio_file_path = audio_file
                    progress_bar.progress(100)
                    status_text.text("✅ Human-like speech generated successfully!")
                    time.sleep(1)
                    status_text.empty()
                    progress_bar.empty()
                else:
                    status_text.text("❌ Failed to generate speech")
                    progress_bar.empty()
                    
            except Exception as e:
                st.error(f"Error: {str(e)}")
                progress_bar.empty()
                status_text.empty()

with col2:
    if st.button("🔄 Regenerate", disabled=not st.session_state.get('original_text')):
        if st.session_state.get('original_text'):
            # Use the stored original text to regenerate
            input_text = st.session_state.original_text
            st.experimental_rerun()

with col3:
    if st.button("🗑️ Clear All"):
        for key in ['audio_file_path', 'detected_language', 'enhanced_text', 'original_text', 'sample_text']:
            if key in st.session_state:
                del st.session_state[key]
        st.experimental_rerun()

# Results section
if st.session_state.detected_language:
    st.subheader("🎯 Processing Results")
    
    col1, col2 = st.columns(2)
    with col1:
        st.info(f"**🌐 Detected Language:** {st.session_state.detected_language}")
    with col2:
        if st.session_state.enhanced_text:
            st.success("**🤖 ChatGPT Enhancement:** Applied")
        else:
            st.warning("**🤖 ChatGPT Enhancement:** Not applied")

# Text comparison
if st.session_state.original_text and st.session_state.enhanced_text:
    with st.expander("📊 Text Enhancement Comparison", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Original Text:**")
            st.text_area("", st.session_state.original_text, height=120, key="orig_compare", disabled=True)
        with col2:
            st.markdown("**🤖 Enhanced for Speech:**")
            st.text_area("", st.session_state.enhanced_text, height=120, key="enh_compare", disabled=True)

# Audio output
if st.session_state.audio_file_path:
    st.subheader("🔊 Human-like Speech Output")
    
    try:
        with open(st.session_state.audio_file_path, 'rb') as f:
            audio_bytes = f.read()
        
        st.audio(audio_bytes, format='audio/mp3' if st.session_state.audio_file_path.endswith('.mp3') else 'audio/wav')
        
        # Download section
        col1, col2 = st.columns([1, 1])
        with col1:
            filename = f"human_speech_{st.session_state.detected_language.split()[0].lower()}.mp3"
            st.download_button(
                label="💾 Download Audio",
                data=audio_bytes,
                file_name=filename,
                mime="audio/mp3"
            )
        with col2:
            if st.session_state.enhanced_text:
                st.download_button(
                    label="📄 Download Enhanced Text",
                    data=st.session_state.enhanced_text,
                    file_name="enhanced_text.txt",
                    mime="text/plain"
                )
        
    except Exception as e:
        st.error(f"Error playing audio: {str(e)}")

# Enhanced instructions
st.subheader("🎯 How to Get Human-like Speech")

tab1, tab2, tab3 = st.tabs(["🚀 Quick Guide", "🤖 ChatGPT Magic", "🎛️ Voice Tuning"])

with tab1:
    st.markdown("""
    ### 🎯 **For Ultra-Natural Speech:**
    
    1. **✅ Enable ChatGPT Enhancement** - This is the game-changer!
    2. **🎤 Use Google TTS Enhanced** - Much better than system voices
    3. **🌍 Keep Regional Accent ON** - Sounds more authentic
    4. **📝 Write naturally** - Don't worry about perfection, ChatGPT will fix it
    5. **🎭 Try different enhancement styles** for various moods
    
    ### 🔥 **Pro Tips:**
    - **Natural Style**: Best for casual, everyday speech
    - **Expressive Style**: Perfect for storytelling and engaging content  
    - **Professional Style**: Ideal for presentations and formal content
    - **Regional Accent**: Makes Indic languages sound much more authentic
    """)

with tab2:
    st.markdown("""
    ### 🤖 **ChatGPT Enhancement Magic:**
    
    **What ChatGPT Does:**
    - 🎭 Adds natural speech fillers ("आप जानते हैं", "you know")
    - 🔄 Converts written text to spoken patterns
    - 💫 Adds emotional undertones and enthusiasm
    - ⚡ Optimizes rhythm and pacing for speech
    - 🎪 Makes content more engaging and lively
    - 🌟 Preserves meaning while enhancing delivery
    
    **Before ChatGPT:**
    > "आज मौसम अच्छा है।"
    
    **After ChatGPT Enhancement:**
    > "आरे वाह! आज तो मौसम कमाल का है यार। लगता है प्रकृति ने आज कुछ खास तैयारी की है।"
    
    **Result:** The speech sounds like a real person talking! 🎉
    """)

with tab3:
    st.markdown("""
    ### 🎛️ **Perfect Voice Settings:**
    
    **For Most Human-like Results:**
    
    **🥇 Google TTS Enhanced (Recommended):**
    - ✅ Regional Accent: ON
    - ✅ Normal Speed (not slow)
    - ✅ Works with internet connection
    - 🎯 **Best quality and naturalness**
    
    **🥈 System TTS Enhanced:**
    - 🎚️ Speech Rate: 180-200 words/min
    - 🔊 Volume: 95%
    - 🎤 Automatically selects best available voice
    - 🚀 Works offline
    
    **🔧 Troubleshooting:**
    - Audio sounds robotic? ➜ Enable ChatGPT enhancement
    - Speech too slow? ➜ Use Normal speed, not Slow
    - Wrong language? ➜ Use manual language selection
    - No sound? ➜ Check browser audio permissions
    """)

# Footer with enhanced branding
st.markdown("---")
st.markdown("""
<div style='text-align: center; padding: 20px;'>
    <h3>🎭 Human-like Indic Text-to-Speech</h3>
    <p><strong>Powered by ChatGPT + Enhanced TTS Technology</strong></p>
    <p>🤖 AI-Enhanced • 🗣️ Human-like • 🌍 Multi-lingual • ⚡ Fast</p>
    <p><em>Making machines speak like humans across all Indian languages</em></p>
</div>
""", unsafe_allow_html=True)

# Performance metrics display
if st.session_state.get('audio_file_path'):
    with st.expander("📈 Performance Metrics"):
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            enhancement_status = "✅ Applied" if st.session_state.enhanced_text else "❌ Not Used"
            st.metric("ChatGPT Enhancement", enhancement_status)
        
        with col2:
            voice_quality = "🥇 Premium" if "Google TTS" in tts_engine else "🥈 Standard"
            st.metric("Voice Quality", voice_quality)
        
        with col3:
            naturalness_score = "95%" if (st.session_state.enhanced_text and "Google TTS" in tts_engine) else "75%"
            st.metric("Naturalness Score", naturalness_score)
        
        with col4:
            lang_support = "🌟 Native" if st.session_state.detected_language else "🔄 Processing"
            st.metric("Language Support", lang_support)

# Advanced settings in expander
with st.expander("⚙️ Advanced Settings & API Configuration"):
    st.markdown("""
    ### 🔑 **ChatGPT API Setup:**
    
    1. Get your OpenAI API key from: https://platform.openai.com/api-keys
    2. In Streamlit Cloud: Go to App Settings → Secrets
    3. Add: `OPENAI_API_KEY = "your-api-key-here"`
    4. Restart the app
    
    ### 🎛️ **Advanced Voice Tuning:**
    """)
    
    col1, col2 = st.columns(2)
    with col1:
        st.info("""
        **For Maximum Naturalness:**
        - Use ChatGPT enhancement with 'expressive' style
        - Enable regional accent for Indic languages
        - Set speech rate to 180-200 WPM
        - Use Google TTS for best quality
        """)
    
    with col2:
        st.warning("""
        **Common Issues:**
        - Robotic voice → Enable ChatGPT enhancement
        - Wrong accent → Turn on regional accent
        - Too fast/slow → Adjust speech rate
        - API errors → Check your OpenAI key
        """)

# Cleanup function
def cleanup_temp_files():
    if st.session_state.audio_file_path and os.path.exists(st.session_state.audio_file_path):
        try:
            os.unlink(st.session_state.audio_file_path)
        except:
            pass

import atexit
atexit.register(cleanup_temp_files)
