import streamlit as st
import yt_dlp
import requests
import urllib.parse
import time
from youtube_transcript_api import YouTubeTranscriptApi
from urllib.parse import urlparse, parse_qs
import json
import os
import tempfile
import uuid

# Page configuration
st.set_page_config(
    page_title="YouTube Video Analyzer",
    page_icon="🎥",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Grok API configuration
GROK_MODEL = 'grok-3-mini-beta'
GROK_BASE_URL = "https://api.x.ai/v1"

# Azure configuration
try:
    SUBSCRIPTION_KEY = st.secrets["AZURE"]["SUBSCRIPTION_KEY"]
    ACCOUNT_ID = st.secrets["AZURE"]["ACCOUNT_ID"]
except KeyError:
    st.error("Azure credentials are missing in secrets. Please configure SUBSCRIPTION_KEY and ACCOUNT_ID in .streamlit/secrets.toml.")
    st.stop()

# YouTube API configuration
def get_youtube_api_key():
    """Get YouTube API key from secrets"""
    try:
        return st.secrets["YOUTUBE"]["API_KEY"]
    except KeyError:
        return None

LOCATION = "trial"

def get_grok_api_key():
    """Get Grok API key from secrets"""
    try:
        return st.secrets["GROK"]["API_KEY"]
    except KeyError:
        return None

def check_grok_api():
    """Checks if the Grok API is working."""
    try:
        api_key = get_grok_api_key()
        if not api_key:
            return False, "Grok API key not found in secrets"
            
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": GROK_MODEL,
            "messages": [{"role": "user", "content": "Test"}],
            "temperature": 0.1,
            "max_tokens": 10
        }
        
        response = requests.post(
            f"{GROK_BASE_URL}/chat/completions",
            headers=headers,
            json=payload,
            timeout=10
        )
        
        if response.status_code == 200:
            return True, "Grok API is working."
        else:
            return False, f"Grok API error: {response.status_code}"
            
    except Exception as e:
        return False, f"Grok API error: {str(e)}"

def check_youtube_api():
    """Checks if the YouTube Data API is working."""
    try:
        api_key = get_youtube_api_key()
        if not api_key:
            return False, "YouTube API key not found in secrets"
            
        url = f"https://www.googleapis.com/youtube/v3/videos?part=snippet&id=dQw4w9WgXcQ&key={api_key}"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            return True, "YouTube API is working."
        else:
            return False, f"YouTube API error: {response.status_code}"
            
    except Exception as e:
        return False, f"YouTube API error: {str(e)}"

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

def get_youtube_video_info(video_id):
    """Get detailed video information from YouTube Data API."""
    try:
        api_key = get_youtube_api_key()
        if not api_key:
            return None
            
        url = f"https://www.googleapis.com/youtube/v3/videos"
        params = {
            'part': 'snippet,statistics,contentDetails',
            'id': video_id,
            'key': api_key
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data['items']:
                video_info = data['items'][0]
                return {
                    'title': video_info['snippet']['title'],
                    'description': video_info['snippet']['description'],
                    'channel_title': video_info['snippet']['channelTitle'],
                    'published_at': video_info['snippet']['publishedAt'],
                    'view_count': video_info['statistics'].get('viewCount', 'N/A'),
                    'like_count': video_info['statistics'].get('likeCount', 'N/A'),
                    'comment_count': video_info['statistics'].get('commentCount', 'N/A'),
                    'duration': video_info['contentDetails']['duration'],
                    'tags': video_info['snippet'].get('tags', []),
                    'category_id': video_info['snippet']['categoryId']
                }
        return None
    except Exception as e:
        st.warning(f"Could not fetch YouTube video info: {e}")
        return None

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
    """Fetches the transcript for a given YouTube video ID with fallback and retries."""
    max_retries = 2
    retry_delay = 2  # seconds

    try:
        # Try English transcript first
        for attempt in range(max_retries):
            try:
                transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['en'])
                transcript = ' '.join([entry['text'] for entry in transcript_list])
                return transcript
            except Exception as e:
                if attempt < max_retries - 1:
                    st.warning(f"Attempt {attempt + 1} failed to fetch English transcript: {e}. Retrying...")
                    time.sleep(retry_delay)
                else:
                    st.warning(f"English transcript not available: {e}")
                    break

        # Fallback to other transcripts
        try:
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            available_transcripts = list(transcript_list)

            for transcript in available_transcripts:
                for attempt in range(max_retries):
                    try:
                        if transcript.is_translatable:
                            # Try translating to English
                            english_transcript = transcript.translate('en').fetch()
                            transcript_text = ' '.join([entry['text'] for entry in english_transcript])
                            st.info(f"📝 Transcript translated from {transcript.language} to English")
                            return transcript_text
                        elif transcript.language_code in ['en', 'hi']:
                            # Use directly if in supported language
                            transcript_data = transcript.fetch()
                            transcript_text = ' '.join([entry['text'] for entry in transcript_data])
                            if transcript.language_code != 'en':
                                st.info(f"📝 Using transcript in {transcript.language}")
                            return transcript_text
                    except Exception as e:
                        if attempt < max_retries - 1:
                            st.warning(f"Attempt {attempt + 1} failed to process {transcript.language} transcript: {e}. Retrying...")
                            time.sleep(retry_delay)
                        else:
                            st.warning(f"Failed to process transcript in {transcript.language}: {e}")
                            break

            # Final fallback: Use first available transcript
            transcript_dict = transcript_list._manually_created_transcripts or transcript_list._generated_transcripts
            if transcript_dict:
                first_transcript = list(transcript_dict.values())[0]
                for attempt in range(max_retries):
                    try:
                        transcript_data = first_transcript.fetch()
                        transcript_text = ' '.join([entry['text'] for entry in transcript_data])
                        st.info(f"📝 Using transcript in {first_transcript.language}")
                        return transcript_text
                    except Exception as e:
                        if attempt < max_retries - 1:
                            st.warning(f"Attempt {attempt + 1} failed to fetch {first_transcript.language} transcript: {e}. Retrying...")
                            time.sleep(retry_delay)
                        else:
                            st.warning(f"Failed to fetch transcript in {first_transcript.language}: {e}")
                            break

        except Exception as e:
            st.warning(f"Could not fetch any transcript: {e}")
            return None

    except Exception as e:
        st.warning(f"Unexpected error fetching transcript: {e}")
        return None

def get_grok_insights(transcript, video_info=None):
    """Sends the transcript to the Grok API for insights with optional video context."""
    if not transcript:
        return None
    try:
        api_key = get_grok_api_key()
        if not api_key:
            return "Grok API key not found in secrets"
        
        system_prompt = """
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
        
        user_content = f"Give me the summary of this transcript: {transcript}"
        
        if video_info:
            context = f"""
            Video Context:
            - Title: {video_info.get('title', 'N/A')}
            - Channel: {video_info.get('channel_title', 'N/A')}
            - Views: {video_info.get('view_count', 'N/A')}
            - Duration: {video_info.get('duration', 'N/A')}
            
            """
            user_content = context + user_content
            
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": GROK_MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": user_content
                }
            ],
            "temperature": 0.1,
            "max_tokens": 2000
        }
        
        response = requests.post(
            f"{GROK_BASE_URL}/chat/completions",
            headers=headers,
            json=payload,
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            return result['choices'][0]['message']['content']
        else:
            st.error(f"Grok API error: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        st.error(f"Error calling Grok API: {e}")
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
            safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
            return f"{folder}/{safe_title}.mp4", safe_title
    except Exception as e:
        st.error(f"Error downloading video: {e}")
        return None, None

@st.cache_data(ttl=3600)
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
    """Uploads a video to Azure Video Indexer with a name within 80 characters."""
    access_token = get_account_access_token()
    if not access_token:
        return None
        
    # Truncate base video name to 50 characters to leave room for unique ID
    base_name = video_name[:50]
    # Append a short unique identifier
    unique_id = uuid.uuid4().hex[:8]
    safe_video_name = f"{base_name}_{unique_id}"[:80]  # Ensure total length <= 80
    
    upload_url = (
        f"https://api.videoindexer.ai/{LOCATION}/Accounts/{ACCOUNT_ID}/Videos"
        f"?accessToken={access_token}&name={urllib.parse.quote(safe_video_name)}&privacy=Private&language=English"
    )
    try:
        with open(file_path, 'rb') as f:
            files = {'file': (os.path.basename(file_path), f)}
            response = requests.post(upload_url, files=files, timeout=300)
            response.raise_for_status()
            return response.json()["id"]
    except requests.exceptions.HTTPError as e:
        st.error(f"Error uploading video: {e.response.status_code} - {e.response.text}")
        return None
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
    
    max_attempts = 60
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
    
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📝 Keywords", "🏷️ Topics", "🔖 Labels", "🎬 Scenes", "📊 Stats"])
    
    with tab1:
        st.subheader("Keywords")
        keywords = insights_data.get("keywords", [])
        if keywords:
            keyword_data = []
            for k in keywords[:20]:
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
            for l in labels[:15]:
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
            for i, scene in enumerate(scenes[:10]):
                with st.expander(f"Scene {i+1}: {scene.get('start', '0:00')} - {scene.get('end', '0:00')}"):
                    st.write(scene.get("description", "No description available."))
                    
                    if "keyFrames" in scene:
                        st.write("**Key Moments:**")
                        for kf in scene["keyFrames"][:3]:
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

    with st.sidebar:
        st.header("🔧 API Status")
        
        grok_status, grok_message = check_grok_api()
        youtube_status, youtube_message = check_youtube_api()
        azure_status, azure_message = check_azure_api()
        
        if grok_status:
            st.success("✅ Grok API Connected")
        else:
            st.error("❌ Grok API Error")
            st.error(grok_message)
            
        if youtube_status:
            st.success("✅ YouTube API Connected")
        else:
            st.error("❌ YouTube API Error")
            st.error(youtube_message)
        
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

    youtube_url = st.text_input(
        "YouTube Video URL", 
        placeholder="https://www.youtube.com/watch?v=...",
        help="Paste any YouTube video URL here"
    )

    if st.button("🚀 Analyze Video", type="primary", use_container_width=True):
        if not youtube_url:
            st.error("Please enter a valid YouTube URL.")
            return
            
        if not (grok_status and youtube_status and azure_status):
            st.error("Cannot proceed - API connections failed. Please check your credentials.")
            return

        video_id = extract_video_id(youtube_url)
        if not video_id:
            st.error("Invalid YouTube URL. Please check the URL and try again.")
            return

        st.info("📹 Fetching video information...")
        video_info = get_youtube_video_info(video_id)
        if video_info:
            st.success(f"📹 Video: {video_info['title']} by {video_info['channel_title']}")
        else:
            st.warning("Could not fetch video information from YouTube API")

        progress_container = st.container()
        
        with progress_container:
            st.info("🔄 Starting analysis...")
            progress_bar = st.progress(0)
            status_text = st.empty()

        analysis_success = True

        try:
            # Step 1: Get transcript and Grok summary
            status_text.text("📝 Fetching transcript...")
            progress_bar.progress(0.1)
            
            transcript = get_youtube_transcript(video_id)
            if transcript:
                status_text.text("🤖 Generating AI summary...")
                progress_bar.progress(0.2)
                
                grok_summary = get_grok_insights(transcript, video_info)
                if not grok_summary:
                    analysis_success = False
                    st.warning("Failed to generate Grok summary.")
            else:
                grok_summary = None
                analysis_success = False
                st.warning("No transcript available for this video. Ensure captions are enabled.")

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
                            if not azure_insights:
                                analysis_success = False
                                st.warning("Failed to fetch Azure insights.")
                        else:
                            azure_insights = None
                            analysis_success = False
                            st.warning("Azure video indexing failed.")
                    else:
                        azure_insights = None
                        analysis_success = False
                        st.warning("Failed to upload video to Azure.")
                else:
                    azure_insights = None
                    analysis_success = False
                    st.warning("Failed to download video.")

            # Clear progress indicators
            progress_container.empty()

            # Display results
            if analysis_success:
                st.success("✅ Analysis complete!")
            else:
                st.warning("⚠️ Analysis completed with errors. Some results may be missing.")
            
            col1, col2 = st.columns([1, 1])
            
            if video_info:
                st.header("📹 Video Information")
                info_col1, info_col2, info_col3 = st.columns(3)
                
                with info_col1:
                    st.metric("👀 Views", f"{int(video_info['view_count']):,}" if video_info['view_count'].isdigit() else video_info['view_count'])
                    st.metric("👍 Likes", f"{int(video_info['like_count']):,}" if video_info['like_count'].isdigit() else video_info['like_count'])
                
                with info_col2:
                    st.metric("💬 Comments", f"{int(video_info['comment_count']):,}" if video_info['comment_count'].isdigit() else video_info['comment_count'])
                    st.metric("⏱️ Duration", video_info['duration'])
                    
                with info_col3:
                    st.metric("📺 Channel", video_info['channel_title'])
                    st.metric("📅 Published", video_info['published_at'][:10])
                
                if video_info.get('tags'):
                    st.subheader("🏷️ Video Tags")
                    tags_text = ", ".join(video_info['tags'][:10])
                    st.write(tags_text)
                
                st.markdown("---")
            
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
            st.error(f"An unexpected error occurred during analysis: {str(e)}")
            analysis_success = False

if __name__ == "__main__":
    main()
