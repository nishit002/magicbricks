import streamlit as st
import yt_dlp
import requests
import urllib.parse
import time
from youtube_transcript_api import YouTubeTranscriptApi
from openai import OpenAI
from urllib.parse import urlparse, parse_qs
import json
import os
import tempfile

# Page configuration
st.set_page_config(
    page_title="YouTube Video Analyzer",
    page_icon="🎥",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Initialize OpenAI client with secrets
@st.cache_resource
def init_openai_client():
    try:
        return OpenAI(api_key=st.secrets["OPENAI"]["API_KEY"], base_url="https://api.x.ai/v1")
    except KeyError:
        st.error("OpenAI API key is missing in secrets. Please configure it in .streamlit/secrets.toml.")
        st.stop()

client = init_openai_client()
GROQ_MODEL = 'grok-3-mini-beta'

# Azure configuration
try:
    SUBSCRIPTION_KEY = st.secrets["AZURE"]["SUBSCRIPTION_KEY"]
    ACCOUNT_ID = st.secrets["AZURE"]["ACCOUNT_ID"]
except KeyError:
    st.error("Azure credentials are missing in secrets. Please configure SUBSCRIPTION_KEY and ACCOUNT_ID in .streamlit/secrets.toml.")
    st.stop()

LOCATION = "trial"

def check_openai_api():
    """Checks if the OpenAI (Grok) API is working."""
    try:
        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": "Test API connectivity."}],
            model=GROQ_MODEL,
            temperature=0.1,
            max_tokens=50
        )
        return True, "OpenAI (Grok) API is working."
    except Exception as e:
        return False, f"OpenAI (Grok) API error: {str(e)}"

def check_azure_api():
    """Checks if the Azure Video Indexer API is working."""
    try:
        url = f"https://api.videoindexer.ai/Auth/trial/Accounts/{ACCOUNT_ID}/AccessToken?allowEdit=true"
        headers = {"Ocp-Apim-Subscription-Key": SUBSCRIPTION_KEY, "Cache-Control": "no-cache"}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return True, "Azure Video Indexer API is working."
    except Exception as e:
        return False, f"Azure Video Indexer API error: {str(e)}"

def extract_video_id(youtube_url):
    """Extracts the video ID from a YouTube URL."""
    try:
        url_data = urlparse(youtube_url)
        if url_data.hostname == 'youtu.be':
            return url_data.path[1:]
        elif url_data.hostname in ('www.youtube.com', 'youtube.com'):
            query = parse_qs(url_data.query)
            return query.get('v', [None])[0]
        return None
    except Exception as e:
        st.error(f"Error extracting video ID: {e}")
        return None

def get_youtube_transcript(video_id):
    """Fetches the transcript for a given YouTube video ID."""
    try:
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        transcript = ' '.join([entry['text'] for entry in transcript_list])
        return transcript
    except Exception as e:
        st.warning(f"Could not fetch transcript: {e}")
        return None

def get_grok_insights(transcript):
    """Sends the transcript to the Groq API for insights."""
    if not transcript:
        return None
    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": """
                    You are a smart YouTube transcript summarizer. Your job is to read the full transcript of a video and return:

                    1. A short summary of the overall video (5-6 sentences).
                    2. Bullet-pointed highlights of key takeaways, structured and concise.
                    3. (Optional) Timestamps if they are included in the transcript.
                    4. Sentiment analysis of the summary.

                    Guidelines:
                    - Focus on clarity and information value such as numbers and statistics.
                    - Ignore filler, repetition, or casual phrases.
                    - Highlight important ideas, tips, steps, or arguments.
                    - If the transcript is long, break it into parts and summarize each before merging.
                    - For sentiment, classify as Positive, Negative, or Neutral with a brief explanation.

                    NEVER summarize the YouTube title or guess content — only work from the transcript provided.
                    """
                },
                {
                    "role": "user",
                    "content": "Give me the summary of this transcript: " + transcript
                }
            ],
            model=GROQ_MODEL,
            temperature=0.1,
            max_tokens=2000
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        st.error(f"Error calling Groq API: {e}")
        return None

def download_youtube_video(youtube_url, folder):
    """Downloads a YouTube video to a temporary folder."""
    ydl_opts = {
        'format': '18/best[height<=480]',
        'merge_output_format': 'mp4',
        'outtmpl': f'{folder}/%(title)s.%(ext)s',
        'quiet': True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(youtube_url, download=True)
            title = info['title']
            # Clean filename for cross-platform compatibility
            safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
            return f"{folder}/{safe_title}.mp4", safe_title
    except Exception as e:
        st.error(f"Error downloading video: {e}")
        return None, None

@st.cache_data(ttl=3600)  # Cache for 1 hour
def get_account_access_token():
    """Gets the Azure Video Indexer access token."""
    url = f"https://api.videoindexer.ai/Auth/trial/Accounts/{ACCOUNT_ID}/AccessToken?allowEdit=true"
    headers = {"Ocp-Apim-Subscription-Key": SUBSCRIPTION_KEY, "Cache-Control": "no-cache"}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error getting access token: {e}")
        return None

def upload_video(file_path, video_name):
    """Uploads a video to Azure Video Indexer."""
    access_token = get_account_access_token()
    if not access_token:
        return None
        
    upload_url = (
        f"https://api.videoindexer.ai/{LOCATION}/Accounts/{ACCOUNT_ID}/Videos"
        f"?accessToken={access_token}&name={video_name}&privacy=Private&language=English"
    )
    try:
        with open(file_path, 'rb') as f:
            files = {'file': (os.path.basename(file_path), f)}
            response = requests.post(upload_url, files=files, timeout=300)
            response.raise_for_status()
            return response.json()["id"]
    except Exception as e:
        st.error(f"Error uploading video: {e}")
        return None

def wait_for_indexing(video_id, progress_bar=None):
    """Polls until video indexing is complete."""
    access_token = get_account_access_token()
    if not access_token:
        return False
        
    status_url = (
        f"https://api.videoindexer.ai/{LOCATION}/Accounts/{ACCOUNT_ID}/Videos/{video_id}/Index"
        f"?accessToken={access_token}"
    )
    
    max_attempts = 60  # 10 minutes max
    attempt = 0
    
    while attempt < max_attempts:
        try:
            response = requests.get(status_url, timeout=10)
            response.raise_for_status()
            state = response.json().get("state")
            
            if progress_bar:
                progress_bar.progress(min(attempt / max_attempts, 0.9))
            
            if state == "Processed":
                if progress_bar:
                    progress_bar.progress(1.0)
                return True
            elif state == "Failed":
                st.error("Video processing failed.")
                return False
                
            time.sleep(10)
            attempt += 1
            
        except Exception as e:
            st.error(f"Error checking indexing status: {e}")
            return False
    
    st.error("Video indexing timed out.")
    return False

def get_insights(video_id):
    """Fetches insights from Azure Video Indexer."""
    access_token = get_account_access_token()
    if not access_token:
        return None
        
    insights_url = (
        f"https://api.videoindexer.ai/{LOCATION}/Accounts/{ACCOUNT_ID}/Videos/{video_id}/Index"
        f"?accessToken={access_token}"
    )
    try:
        response = requests.get(insights_url, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error fetching insights: {e}")
        return None

def display_azure_insights(insights):
    """Displays Azure Video Indexer insights in a structured format."""
    if not insights or "videos" not in insights:
        st.warning("No Azure insights available.")
        return

    insights_data = insights["videos"][0]["insights"]
    
    # Create tabs for different types of insights
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📝 Keywords", "🏷️ Topics", "🔖 Labels", "🎬 Scenes", "📊 Stats"])
    
    with tab1:
        st.subheader("Keywords")
        keywords = insights_data.get("keywords", [])
        if keywords:
            # Display top keywords with confidence scores
            keyword_data = []
            for k in keywords[:20]:  # Limit to top 20
                keyword_data.append({
                    "Keyword": k["text"],
                    "Confidence": f"{k.get('confidence', 0):.2f}",
                    "Instances": len(k.get("instances", []))
                })
            st.dataframe(keyword_data, use_container_width=True)
        else:
            st.info("No keywords detected.")

    with tab2:
        st.subheader("Topics")
        topics = insights_data.get("topics", [])
        if topics:
            topic_data = []
            for t in topics:
                topic_data.append({
                    "Topic": t["name"],
                    "Confidence": f"{t.get('confidence', 0):.2f}",
                    "Language": t.get("language", "N/A")
                })
            st.dataframe(topic_data, use_container_width=True)
        else:
            st.info("No topics detected.")

    with tab3:
        st.subheader("Labels")
        labels = insights_data.get("labels", [])
        if labels:
            label_data = []
            for l in labels[:15]:  # Limit to top 15
                label_data.append({
                    "Label": l["name"],
                    "Confidence": f"{l.get('confidence', 0):.2f}",
                    "Instances": len(l.get("instances", []))
                })
            st.dataframe(label_data, use_container_width=True)
        else:
            st.info("No labels detected.")

    with tab4:
        st.subheader("Key Scenes")
        scenes = insights_data.get("scenes", [])
        if scenes:
            for i, scene in enumerate(scenes[:10]):  # Limit to first 10 scenes
                with st.expander(f"Scene {i+1}: {scene.get('start', '0:00')} - {scene.get('end', '0:00')}"):
                    st.write(scene.get("description", "No description available."))
                    
                    # Show keyframes if available
                    if "keyFrames" in scene:
                        st.write("**Key Moments:**")
                        for kf in scene["keyFrames"][:3]:  # Show first 3 keyframes
                            st.write(f"- At {kf.get('start', '0:00')}")
        else:
            st.info("No key scenes detected.")
    
    with tab5:
        st.subheader("Video Statistics")
        duration = insights_data.get("duration", {})
        stats_data = {
            "Duration": f"{duration.get('seconds', 0)} seconds",
            "Keywords Found": len(insights_data.get("keywords", [])),
            "Topics Found": len(insights_data.get("topics", [])),
            "Labels Found": len(insights_data.get("labels", [])),
            "Scenes Found": len(insights_data.get("scenes", [])),
            "Transcript Available": "Yes" if insights_data.get("transcript") else "No"
        }
        
        col1, col2 = st.columns(2)
        for i, (key, value) in enumerate(stats_data.items()):
            if i % 2 == 0:
                col1.metric(key, value)
            else:
                col2.metric(key, value)

# Main Streamlit UI
def main():
    st.title("🎥 YouTube Video Analyzer")
    st.markdown("Enter a YouTube URL to get AI-powered summaries and detailed video insights.")

    # Sidebar for API status
    with st.sidebar:
        st.header("🔧 API Status")
        
        # Check APIs
        openai_status, openai_message = check_openai_api()
        azure_status, azure_message = check_azure_api()
        
        if openai_status:
            st.success("✅ Grok API Connected")
        else:
            st.error("❌ Grok API Error")
            st.error(openai_message)
        
        if azure_status:
            st.success("✅ Azure API Connected")
        else:
            st.error("❌ Azure API Error")
            st.error(azure_message)
        
        st.markdown("---")
        st.markdown("**Features:**")
        st.markdown("- 🤖 AI-powered summaries")
        st.markdown("- 🔍 Keyword extraction")
        st.markdown("- 📊 Sentiment analysis")
        st.markdown("- 🎬 Scene detection")
        st.markdown("- 🏷️ Topic modeling")

    # Main content area
    youtube_url = st.text_input(
        "YouTube Video URL", 
        placeholder="https://www.youtube.com/watch?v=...",
        help="Paste any YouTube video URL here"
    )

    if st.button("🚀 Analyze Video", type="primary", use_container_width=True):
        if not youtube_url:
            st.error("Please enter a valid YouTube URL.")
            return
            
        if not (openai_status and azure_status):
            st.error("Cannot proceed - API connections failed. Please check your credentials.")
            return

        # Extract video ID
        video_id = extract_video_id(youtube_url)
        if not video_id:
            st.error("Invalid YouTube URL. Please check the URL and try again.")
            return

        # Create progress tracking
        progress_container = st.container()
        
        with progress_container:
            st.info("🔄 Starting analysis...")
            progress_bar = st.progress(0)
            status_text = st.empty()

        try:
            # Step 1: Get transcript and Grok summary
            status_text.text("📝 Fetching transcript...")
            progress_bar.progress(0.1)
            
            transcript = get_youtube_transcript(video_id)
            if transcript:
                status_text.text("🤖 Generating AI summary...")
                progress_bar.progress(0.2)
                
                grok_summary = get_grok_insights(transcript)
            else:
                grok_summary = None

            # Step 2: Download video
            status_text.text("⬇️ Downloading video...")
            progress_bar.progress(0.3)
            
            with tempfile.TemporaryDirectory() as temp_dir:
                video_path, video_title = download_youtube_video(youtube_url, temp_dir)
                
                if video_path and os.path.exists(video_path):
                    # Step 3: Upload to Azure
                    status_text.text("☁️ Uploading to Azure...")
                    progress_bar.progress(0.4)
                    
                    azure_video_id = upload_video(video_path, video_title or "YouTube Video")
                    
                    if azure_video_id:
                        # Step 4: Wait for indexing
                        status_text.text("🔍 Processing video (this may take a few minutes)...")
                        
                        if wait_for_indexing(azure_video_id, progress_bar):
                            # Step 5: Get insights
                            status_text.text("📊 Fetching insights...")
                            azure_insights = get_insights(azure_video_id)
                        else:
                            azure_insights = None
                    else:
                        azure_insights = None
                else:
                    azure_insights = None

            # Clear progress indicators
            progress_container.empty()

            # Display results
            st.success("✅ Analysis complete!")
            
            # Create two columns for results
            col1, col2 = st.columns([1, 1])
            
            with col1:
                st.header("🤖 AI Summary (Grok)")
                if grok_summary:
                    st.markdown(grok_summary)
                else:
                    st.warning("Could not generate AI summary. This might be due to transcript unavailability or API issues.")
            
            with col2:
                st.header("☁️ Azure Video Insights")
                if azure_insights:
                    display_azure_insights(azure_insights)
                else:
                    st.warning("Could not get Azure insights. This might be due to upload or processing issues.")

        except Exception as e:
            progress_container.empty()
            st.error(f"An error occurred during analysis: {str(e)}")

if __name__ == "__main__":
    main()
