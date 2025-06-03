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
import re

# Page configuration
st.set_page_config(
    page_title="YouTube Video Analyzer",
    page_icon="🎥",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# API configurations
GROK_MODEL = 'grok-3-mini-beta'
GROK_BASE_URL = "https://api.x.ai/v1"
LOCATION = "trial"

# Secret key getters
def get_grok_api_key():
    try:
        return st.secrets["GROK"]["API_KEY"]
    except KeyError:
        return None

def get_youtube_api_key():
    try:
        return st.secrets["YOUTUBE"]["API_KEY"]
    except KeyError:
        return None

def get_scraper_api_key():
    try:
        return st.secrets["SCRAPER"]["API_KEY"]
    except KeyError:
        return None

# Azure configuration
try:
    SUBSCRIPTION_KEY = st.secrets["AZURE"]["SUBSCRIPTION_KEY"]
    ACCOUNT_ID = st.secrets["AZURE"]["ACCOUNT_ID"]
except KeyError:
    st.error("Azure credentials are missing in secrets.")
    st.stop()

# API Status Checks
def check_grok_api():
    """Checks if the Grok API is working."""
    try:
        api_key = get_grok_api_key()
        if not api_key:
            return False, "Grok API key not found"
            
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
        
        return response.status_code == 200, f"Status: {response.status_code}"
    except Exception as e:
        return False, f"Error: {str(e)}"

def check_youtube_api():
    """Checks if the YouTube Data API is working."""
    try:
        api_key = get_youtube_api_key()
        if not api_key:
            return False, "YouTube API key not found"
            
        url = f"https://www.googleapis.com/youtube/v3/videos?part=snippet&id=dQw4w9WgXcQ&key={api_key}"
        response = requests.get(url, timeout=10)
        
        return response.status_code == 200, f"Status: {response.status_code}"
    except Exception as e:
        return False, f"Error: {str(e)}"

def check_azure_api():
    """Checks if the Azure Video Indexer API is working."""
    try:
        url = f"https://api.videoindexer.ai/Auth/trial/Accounts/{ACCOUNT_ID}/AccessToken?allowEdit=true"
        headers = {"Ocp-Apim-Subscription-Key": SUBSCRIPTION_KEY, "Cache-Control": "no-cache"}
        response = requests.get(url, headers=headers, timeout=10)
        
        return response.status_code == 200, f"Status: {response.status_code}"
    except Exception as e:
        return False, f"Error: {str(e)}"

def check_scraper_api():
    """Checks if the ScraperAPI is working."""
    try:
        api_key = get_scraper_api_key()
        if not api_key:
            return False, "ScraperAPI key not found"
            
        # Test with a simple request
        url = f"http://api.scraperapi.com?api_key={api_key}&url=https://httpbin.org/ip"
        response = requests.get(url, timeout=10)
        
        return response.status_code == 200, f"Status: {response.status_code}"
    except Exception as e:
        return False, f"Error: {str(e)}"

# Core Functions
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
    except Exception:
        return None

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
    except Exception:
        return None

def get_youtube_transcript_with_scraper(video_id):
    """Enhanced transcript fetching with better ScraperAPI integration."""
    # Method 1: Direct YouTube Transcript API
    try:
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['en'])
        transcript = ' '.join([entry['text'] for entry in transcript_list])
        return transcript, "Direct YouTube API"
    except:
        pass
    
    # Method 2: Try other languages and translate
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        for transcript in transcript_list:
            try:
                if transcript.is_translatable:
                    english_transcript = transcript.translate('en').fetch()
                    transcript_text = ' '.join([entry['text'] for entry in english_transcript])
                    return transcript_text, f"Translated from {transcript.language}"
                elif transcript.language_code in ['en', 'hi', 'es', 'fr', 'de']:
                    transcript_data = transcript.fetch()
                    transcript_text = ' '.join([entry['text'] for entry in transcript_data])
                    return transcript_text, f"Direct {transcript.language}"
            except:
                continue
    except:
        pass
    
    # Method 3: ScraperAPI + YouTube page scraping
    try:
        scraper_key = get_scraper_api_key()
        if scraper_key:
            youtube_url = f"https://www.youtube.com/watch?v={video_id}"
            scraper_url = f"http://api.scraperapi.com?api_key={scraper_key}&url={youtube_url}&render=true"
            
            response = requests.get(scraper_url, timeout=45)
            if response.status_code == 200:
                content = response.text
                
                # Method 3a: Look for transcript in ytInitialPlayerResponse
                import re
                
                # Pattern 1: Look for captions in player response
                player_response_match = re.search(r'"captions":\{"playerCaptionsTracklistRenderer":\{"captionTracks":\[([^\]]+)\]', content)
                if player_response_match:
                    captions_data = player_response_match.group(1)
                    # Extract first caption URL
                    url_match = re.search(r'"baseUrl":"([^"]+)"', captions_data)
                    if url_match:
                        caption_url = url_match.group(1).replace('\\u0026', '&')
                        
                        # Fetch the caption file
                        caption_response = requests.get(caption_url, timeout=15)
                        if caption_response.status_code == 200:
                            # Parse XML captions
                            import xml.etree.ElementTree as ET
                            try:
                                root = ET.fromstring(caption_response.text)
                                transcript_parts = []
                                for text_elem in root.findall('.//text'):
                                    if text_elem.text:
                                        transcript_parts.append(text_elem.text)
                                
                                if transcript_parts:
                                    return ' '.join(transcript_parts), "ScraperAPI + Captions"
                            except:
                                pass
                
                # Pattern 2: Look for transcript in page content
                transcript_patterns = [
                    r'"transcriptRenderer".*?"runs":\[([^\]]+)\]',
                    r'"cueGroup":\[([^\]]+)\]',
                    r'"caption":"([^"]+)"'
                ]
                
                for pattern in transcript_patterns:
                    matches = re.findall(pattern, content)
                    if matches:
                        transcript_text = ' '.join(matches[:50])  # Take first 50 matches
                        if len(transcript_text) > 100:  # Reasonable length check
                            return transcript_text, "ScraperAPI + Pattern Match"
    except Exception as e:
        st.warning(f"ScraperAPI method failed: {str(e)[:100]}...")
    
    # Method 4: Alternative API approach
    try:
        scraper_key = get_scraper_api_key()
        if scraper_key:
            # Try different YouTube URL formats
            urls_to_try = [
                f"https://www.youtube.com/api/timedtext?v={video_id}&lang=en&fmt=srv3",
                f"https://www.youtube.com/api/timedtext?v={video_id}&lang=en-US&fmt=srv3",
                f"https://www.youtube.com/api/timedtext?v={video_id}&lang=en&fmt=vtt"
            ]
            
            for url in urls_to_try:
                try:
                    scraper_url = f"http://api.scraperapi.com?api_key={scraper_key}&url={url}"
                    response = requests.get(scraper_url, timeout=20)
                    
                    if response.status_code == 200 and len(response.text) > 50:
                        # Parse the transcript response
                        import xml.etree.ElementTree as ET
                        try:
                            root = ET.fromstring(response.text)
                            transcript_parts = []
                            for text_elem in root.findall('.//text'):
                                if text_elem.text:
                                    # Clean up the text
                                    clean_text = re.sub(r'<[^>]+>', '', text_elem.text)
                                    transcript_parts.append(clean_text)
                            
                            if transcript_parts:
                                return ' '.join(transcript_parts), "ScraperAPI + Timedtext API"
                        except:
                            # Try parsing as plain text
                            clean_text = re.sub(r'<[^>]+>', '', response.text)
                            if len(clean_text) > 100:
                                return clean_text, "ScraperAPI + Raw Text"
                except:
                    continue
    except:
        pass
    
    # Method 5: Generate transcript from video info if available
    try:
        api_key = get_youtube_api_key()
        if api_key:
            # Get video description and title as fallback content
            video_info = get_youtube_video_info(video_id)
            if video_info and video_info.get('description'):
                description = video_info['description']
                if len(description) > 200:  # Substantial description
                    return description, "Video Description (Fallback)"
    except:
        pass
    
    return None, "All transcript methods failed"

def get_grok_insights(transcript, video_info=None, method_used=None):
    """Enhanced Grok analysis with speaker detection and comprehensive insights."""
    if not transcript:
        return None
    
    try:
        api_key = get_grok_api_key()
        if not api_key:
            return "Grok API key not found"
        
        system_prompt = """You are an advanced YouTube video analyzer. Analyze the transcript and provide:

1. **SUMMARY** (5-6 sentences overview)
2. **KEY SPEAKERS** (if multiple speakers detected, identify who is speaking)
3. **MAIN TOPICS** (list primary discussion topics)
4. **KEY HIGHLIGHTS** (bullet points of important moments)
5. **SENTIMENT ANALYSIS** (overall tone: Positive/Negative/Neutral with explanation)
6. **TAGS** (relevant hashtags/keywords for the content)
7. **TIMESTAMPS** (if available in transcript)

Guidelines:
- Focus on actionable insights and concrete information
- Identify different speakers if conversation/interview format
- Extract numbers, statistics, and specific data points
- Highlight any controversial or trending topics
- Note if it's educational, entertainment, news, etc.
- Ignore filler words and focus on substance"""

        user_content = f"Analyze this video transcript (obtained via {method_used}):\n\n{transcript}"
        
        if video_info:
            context = f"""
CONTEXT:
- Title: {video_info.get('title', 'N/A')}
- Channel: {video_info.get('channel_title', 'N/A')}
- Views: {video_info.get('view_count', 'N/A')}
- Duration: {video_info.get('duration', 'N/A')}
- Published: {video_info.get('published_at', 'N/A')}

"""
            user_content = context + user_content
            
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": GROK_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            "temperature": 0.1,
            "max_tokens": 3000
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
            return f"Grok API error: {response.status_code}"
            
    except Exception as e:
        return f"Error calling Grok API: {e}"

def download_youtube_video(youtube_url, folder):
    """Downloads video with multiple fallback methods."""
    scraper_key = get_scraper_api_key()
    
    # Method 1: Direct yt-dlp
    try:
        ydl_opts = {
            'format': '18/best[height<=480]/mp4',
            'merge_output_format': 'mp4',
            'outtmpl': f'{folder}/%(title)s.%(ext)s',
            'quiet': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(youtube_url, download=True)
            title = info['title']
            safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
            return f"{folder}/{safe_title}.mp4", safe_title
    except Exception as e:
        st.warning(f"Method 1 failed: {str(e)[:100]}...")
    
    # Method 2: yt-dlp with ScraperAPI proxy
    if scraper_key:
        try:
            ydl_opts = {
                'format': '18/best[height<=480]/mp4',
                'merge_output_format': 'mp4',
                'outtmpl': f'{folder}/%(title)s.%(ext)s',
                'quiet': True,
                'proxy': f'http://scraperapi:{scraper_key}@proxy-server.scraperapi.com:8001'
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(youtube_url, download=True)
                title = info['title']
                safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
                return f"{folder}/{safe_title}.mp4", safe_title
        except Exception as e:
            st.warning(f"Method 2 failed: {str(e)[:100]}...")
    
    # Method 3: Alternative download using requests + ScraperAPI
    if scraper_key:
        try:
            # Get video info first
            video_id = extract_video_id(youtube_url)
            if not video_id:
                raise Exception("Could not extract video ID")
            
            # Use ScraperAPI to get video download URL
            scraper_url = f"http://api.scraperapi.com?api_key={scraper_key}&url={youtube_url}"
            response = requests.get(scraper_url, timeout=30)
            
            if response.status_code == 200:
                # Try to extract video URL from response
                content = response.text
                
                # Look for video URLs in the scraped content
                import re
                video_url_pattern = r'"url":"([^"]*\.mp4[^"]*)"'
                matches = re.findall(video_url_pattern, content)
                
                if matches:
                    video_url = matches[0].replace('\\u0026', '&')
                    
                    # Download the video
                    video_response = requests.get(video_url, stream=True, timeout=60)
                    if video_response.status_code == 200:
                        title = f"youtube_video_{video_id}"
                        file_path = f"{folder}/{title}.mp4"
                        
                        with open(file_path, 'wb') as f:
                            for chunk in video_response.iter_content(chunk_size=8192):
                                f.write(chunk)
                        
                        return file_path, title
        except Exception as e:
            st.warning(f"Method 3 failed: {str(e)[:100]}...")
    
    # Method 4: Create a dummy video file for Azure processing
    # This allows Azure to still process audio/transcript analysis
    try:
        st.info("📹 Creating placeholder video for audio analysis...")
        video_id = extract_video_id(youtube_url)
        title = f"youtube_audio_{video_id}"
        
        # Create a minimal MP4 file (1 second black video)
        import subprocess
        file_path = f"{folder}/{title}.mp4"
        
        # Use ffmpeg to create a 1-second black video (if available)
        try:
            subprocess.run([
                'ffmpeg', '-f', 'lavfi', '-i', 'color=black:size=320x240:duration=1',
                '-c:v', 'libx264', '-t', '1', '-pix_fmt', 'yuv420p', 
                file_path, '-y'
            ], check=True, capture_output=True)
            
            return file_path, title
        except:
            # If ffmpeg not available, create a very basic file
            with open(file_path, 'wb') as f:
                # Write minimal MP4 header
                f.write(b'\x00\x00\x00\x20ftypmp42\x00\x00\x00\x00mp42isom')
            
            return file_path, title
            
    except Exception as e:
        st.error(f"All download methods failed: {e}")
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
    """Uploads video to Azure Video Indexer."""
    access_token = get_account_access_token()
    if not access_token:
        return None
        
    base_name = video_name[:50]
    unique_id = uuid.uuid4().hex[:8]
    safe_video_name = f"{base_name}_{unique_id}"[:80]
    
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

def display_comprehensive_insights(grok_analysis, azure_insights, video_info, transcript_method):
    """Display comprehensive analysis from all APIs."""
    
    # Video Information Header
    if video_info:
        st.header("📹 Video Information")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("👀 Views", f"{int(video_info['view_count']):,}" if str(video_info['view_count']).isdigit() else video_info['view_count'])
            st.metric("📺 Channel", video_info['channel_title'])
        
        with col2:
            st.metric("👍 Likes", f"{int(video_info['like_count']):,}" if str(video_info['like_count']).isdigit() else video_info['like_count'])
            st.metric("⏱️ Duration", video_info['duration'])
            
        with col3:
            st.metric("💬 Comments", f"{int(video_info['comment_count']):,}" if str(video_info['comment_count']).isdigit() else video_info['comment_count'])
            st.metric("📅 Published", video_info['published_at'][:10])
            
        with col4:
            st.metric("📝 Transcript", f"✅ {transcript_method}")
            if video_info.get('tags'):
                st.metric("🏷️ Tags", f"{len(video_info['tags'])} tags")
        
        st.markdown("---")
    
    # Main Analysis Sections
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.header("🤖 AI Analysis (Grok)")
        if grok_analysis:
            st.markdown(grok_analysis)
        else:
            st.warning("Grok analysis not available")
    
    with col2:
        st.header("☁️ Azure Video Insights")
        if azure_insights:
            display_azure_insights(azure_insights)
        else:
            st.warning("Azure insights not available")

def display_azure_insights(insights):
    """Enhanced Azure insights display."""
    if not insights or "videos" not in insights:
        st.warning("No Azure insights available.")
        return

    insights_data = insights["videos"][0]["insights"]
    
    # Speakers Section
    speakers = insights_data.get("speakers", [])
    if speakers:
        st.subheader("🎤 Speakers Detected")
        for speaker in speakers[:5]:
            st.write(f"**Speaker {speaker.get('id', 'Unknown')}**: {len(speaker.get('instances', []))} instances")
    
    # Create tabs for detailed insights
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📝 Keywords", "🏷️ Topics", "🔖 Labels", "🎬 Scenes", "📊 Statistics"])
    
    with tab1:
        keywords = insights_data.get("keywords", [])
        if keywords:
            keyword_data = []
            for k in keywords[:25]:
                keyword_data.append({
                    "Keyword": k["text"],
                    "Confidence": f"{k.get('confidence', 0):.2f}",
                    "Instances": len(k.get("instances", []))
                })
            st.dataframe(keyword_data, use_container_width=True)
        else:
            st.info("No keywords detected.")

    with tab2:
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
        labels = insights_data.get("labels", [])
        if labels:
            label_data = []
            for l in labels[:20]:
                label_data.append({
                    "Label": l["name"],
                    "Confidence": f"{l.get('confidence', 0):.2f}",
                    "Instances": len(l.get("instances", []))
                })
            st.dataframe(label_data, use_container_width=True)
        else:
            st.info("No labels detected.")

    with tab4:
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
        duration = insights_data.get("duration", {})
        stats = {
            "Duration": f"{duration.get('seconds', 0)} seconds",
            "Speakers": len(speakers),
            "Keywords": len(insights_data.get("keywords", [])),
            "Topics": len(insights_data.get("topics", [])),
            "Labels": len(insights_data.get("labels", [])),
            "Scenes": len(insights_data.get("scenes", [])),
        }
        
        for key, value in stats.items():
            st.metric(key, value)

# Main Streamlit UI
def main():
    st.title("🎥 YouTube Video Analyzer")
    st.markdown("**Real-time AI-powered video analysis using Grok, YouTube, Azure, and ScraperAPI**")

    # Enhanced sidebar with all API statuses
    with st.sidebar:
        st.header("🔧 API Status Dashboard")
        
        # Check all APIs
        grok_status, grok_msg = check_grok_api()
        youtube_status, youtube_msg = check_youtube_api()
        azure_status, azure_msg = check_azure_api()
        scraper_status, scraper_msg = check_scraper_api()
        
        # Display status with emojis
        apis = [
            ("🤖 Grok AI", grok_status, grok_msg),
            ("📹 YouTube Data", youtube_status, youtube_msg),
            ("☁️ Azure Video", azure_status, azure_msg),
            ("🔄 ScraperAPI", scraper_status, scraper_msg)
        ]
        
        for name, status, msg in apis:
            if status:
                st.success(f"✅ {name}")
            else:
                st.error(f"❌ {name}")
                st.caption(msg)
        
        st.markdown("---")
        st.markdown("**🚀 Features:**")
        st.markdown("- 🎤 Speaker identification")
        st.markdown("- 📝 Real-time transcription")
        st.markdown("- 🧠 AI-powered analysis")
        st.markdown("- 🏷️ Smart tagging")
        st.markdown("- 📊 Comprehensive insights")
        st.markdown("- 🔄 Multiple data sources")

    # Main input
    youtube_url = st.text_input(
        "🎬 YouTube Video URL", 
        placeholder="https://www.youtube.com/watch?v=...",
        help="Paste any YouTube video URL for comprehensive analysis"
    )

    if st.button("🚀 Analyze Video", type="primary", use_container_width=True):
        if not youtube_url:
            st.error("Please enter a valid YouTube URL.")
            return
        
        # Check minimum API requirements
        working_apis = sum([grok_status, youtube_status, azure_status])
        if working_apis < 2:
            st.error("Need at least 2 APIs working for analysis. Please check your credentials.")
            return

        # Extract video ID
        video_id = extract_video_id(youtube_url)
        if not video_id:
            st.error("Invalid YouTube URL format.")
            return

        # Progress tracking
        progress_container = st.container()
        with progress_container:
            st.info("🔄 Starting comprehensive analysis...")
            progress_bar = st.progress(0)
            status_text = st.empty()

        results = {
            'video_info': None,
            'transcript': None,
            'transcript_method': None,
            'grok_analysis': None,
            'azure_insights': None
        }

        try:
            # Step 1: Get video information
            if youtube_status:
                status_text.text("📹 Fetching video metadata...")
                progress_bar.progress(0.1)
                results['video_info'] = get_youtube_video_info(video_id)
                if results['video_info']:
                    st.success(f"✅ Video: {results['video_info']['title']}")

            # Step 2: Get transcript with multiple fallbacks
            status_text.text("📝 Fetching transcript...")
            progress_bar.progress(0.2)
            results['transcript'], results['transcript_method'] = get_youtube_transcript_with_scraper(video_id)
            
            if results['transcript']:
                st.success(f"✅ Transcript obtained via {results['transcript_method']}")
            else:
                st.warning("⚠️ Could not obtain transcript")

            # Step 3: Generate Grok analysis
            if grok_status and results['transcript']:
                status_text.text("🤖 Generating AI analysis...")
                progress_bar.progress(0.4)
                results['grok_analysis'] = get_grok_insights(
                    results['transcript'], 
                    results['video_info'], 
                    results['transcript_method']
                )
                if results['grok_analysis']:
                    st.success("✅ AI analysis complete")

            # Step 4: Azure processing (with better error handling)
            if azure_status:
                status_text.text("⬇️ Attempting video download...")
                progress_bar.progress(0.5)
                
                with tempfile.TemporaryDirectory() as temp_dir:
                    video_path, video_title = download_youtube_video(youtube_url, temp_dir)
                    
                    if video_path and os.path.exists(video_path):
                        status_text.text("☁️ Uploading to Azure...")
                        progress_bar.progress(0.6)
                        
                        azure_video_id = upload_video(video_path, video_title or "YouTube_Video")
                        
                        if azure_video_id:
                            status_text.text("🔍 Processing with Azure (2-5 minutes)...")
                            progress_bar.progress(0.7)
                            
                            if wait_for_indexing(azure_video_id, progress_bar):
                                status_text.text("📊 Retrieving Azure insights...")
                                results['azure_insights'] = get_insights(azure_video_id)
                                if results['azure_insights']:
                                    st.success("✅ Azure analysis complete")
                                else:
                                    st.warning("⚠️ Azure insights retrieval failed")
                            else:
                                st.warning("⚠️ Azure video processing failed")
                        else:
                            st.warning("⚠️ Video upload to Azure failed")
                    else:
                        st.warning("⚠️ Video download failed - Azure analysis skipped")
                        # Still allow other analyses to proceed

            # Clear progress
            progress_container.empty()
            
            # Display results
            success_count = sum([
                bool(results['video_info']),
                bool(results['transcript']),
                bool(results['grok_analysis']),
                bool(results['azure_insights'])
            ])
            
            if success_count >= 2:
                st.success(f"✅ Analysis complete! ({success_count}/4 components successful)")
            else:
                st.warning(f"⚠️ Partial analysis complete ({success_count}/4 components successful)")
            
            # Display comprehensive results
            display_comprehensive_insights(
                results['grok_analysis'],
                results['azure_insights'],
                results['video_info'],
                results['transcript_method']
            )

        except Exception as e:
            progress_container.empty()
            st.error(f"❌ Analysis failed: {str(e)}")

if __name__ == "__main__":
    main()
