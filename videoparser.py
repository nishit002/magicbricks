import streamlit as st
try:
    import yt_dlp
except ImportError:
    st.error("The 'yt_dlp' module is missing. Please ensure 'yt-dlp' is installed via 'pip install yt-dlp' or check your requirements.txt.")
    st.stop()
import requests
import urllib.parse
import time
try:
    from youtube_transcript_api import YouTubeTranscriptApi
except ImportError:
    st.error("The 'youtube_transcript_api' module is missing. Please ensure 'youtube-transcript-api' is installed.")
    st.stop()
try:
    from openai import OpenAI
except ImportError:
    st.error("The 'openai' module is missing. Please ensure 'openai' is installed.")
    st.stop()
from urllib.parse import urlparse, parse_qs
import json
import os
import tempfile

# Initialize OpenAI client with secrets
try:
    client = OpenAI(api_key=st.secrets["OPENAI"]["API_KEY"], base_url="https://api.x.ai/v1")
except KeyError:
    st.error("OpenAI API key is missing in secrets. Please configure it in .streamlit/secrets.toml.")
    st.stop()
GROQ_MODEL = 'grok-3-mini-beta'
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
            temperature=0.1
        )
        return True, "OpenAI (Grok) API is working."
    except Exception as e:
        return False, f"OpenAI (Grok) API error: {e}"

def check_azure_api():
    """Checks if the Azure Video Indexer API is working."""
    try:
        url = f"https://api.videoindexer.ai/Auth/trial/Accounts/{ACCOUNT_ID}/AccessToken?allowEdit=true"
        headers = {"Ocp-Apim-Subscription-Key": SUBSCRIPTION_KEY, "Cache-Control": "no-cache"}
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return True, "Azure Video Indexer API is working."
    except Exception as e:
        return False, f"Azure Video Indexer API error: {e}"

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
            temperature=0.1
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        st.error(f"Error calling Groq API: {e}")
        return None

def download_youtube_video(youtube_url, folder):
    """Downloads a YouTube video to a temporary folder."""
    ydl_opts = {
        'format': '18',
        'merge_output_format': 'mp4',
        'outtmpl': f'{folder}/%(title)s.%(ext)s',
        'quiet': True,
        'cookiesfrombrowser': ('chrome', None)
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(youtube_url, download=True)
            return f"{folder}/{info['title']}.mp4"
    except Exception as e:
        st.error(f"Error downloading video: {e}")
        return None

def get_account_access_token():
    """Gets the Azure Video Indexer access token."""
    url = f"https://api.videoindexer.ai/Auth/trial/Accounts/{ACCOUNT_ID}/AccessToken?allowEdit=true"
    headers = {"Ocp-Apim-Subscription-Key": SUBSCRIPTION_KEY, "Cache-Control": "no-cache"}
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error getting access token: {e}")
        return None

def upload_video(file_path, video_name):
    """Uploads a video to Azure Video Indexer."""
    upload_url = (
        f"https://api.videoindexer.ai/{LOCATION}/Accounts/{ACCOUNT_ID}/Videos"
        f"?accessToken={get_account_access_token()}&name={video_name}&privacy=Private&language=English"
    )
    try:
        with open(file_path, 'rb') as f:
            files = {'file': (os.path.basename(file_path), f)}
            response = requests.post(upload_url, files=files)
            response.raise_for_status()
            return response.json()["id"]
    except Exception as e:
        st.error(f"Error uploading video: {e}")
        return None

def wait_for_indexing(video_id):
    """Polls until video indexing is complete."""
    status_url = (
        f"https://api.videoindexer.ai/{LOCATION}/Accounts/{ACCOUNT_ID}/Videos/{video_id}/Index"
        f"?accessToken={get_account_access_token()}"
    )
    with st.spinner("Indexing video... This may take a few minutes."):
        while True:
            try:
                response = requests.get(status_url)
                response.raise_for_status()
                state = response.json().get("state")
                if state == "Processed":
                    return True
                time.sleep(10)
            except Exception as e:
                st.error(f"Error checking indexing status: {e}")
                return False

def get_insights(video_id):
    """Fetches insights from Azure Video Indexer."""
    insights_url = (
        f"https://api.videoindexer.ai/{LOCATION}/Accounts/{ACCOUNT_ID}/Videos/{video_id}/Index"
        f"?accessToken={get_account_access_token()}"
    )
    try:
        response = requests.get(insights_url)
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
    
    st.subheader("Keywords")
    keywords = insights_data.get("keywords", [])
    if keywords:
        st.table([{"Keyword": k["text"]} for k in keywords])
    else:
        st.write("No keywords detected.")

    st.subheader("Topics")
    topics = insights_data.get("topics", [])
    if topics:
        st.table([{"Topic": t["name"]} for t in topics])
    else:
        st.write("No topics detected.")

    st.subheader("Labels")
    labels = insights_data.get("labels", [])
    if labels:
        st.table([{"Label": l["name"]} for l in labels])
    else:
        st.write("No labels detected.")

    st.subheader("Key Moments")
    scenes = insights_data.get("scenes", [])
    if scenes:
        for scene in scenes:
            st.write(f"**Scene at {scene['start']} - {scene['end']}**")
            st.write(scene.get("description", "No description available."))
    else:
        st.write("No key moments detected.")

# Streamlit UI
st.title("YouTube Video Analyzer")
st.markdown("Enter a YouTube URL to get a summary and insights powered by Grok and Azure Video Indexer.")

# API Status Check
st.header("API Status")
openai_status, openai_message = check_openai_api()
azure_status, azure_message = check_azure_api()

col1, col2 = st.columns(2)
with col1:
    st.subheader("Grok API")
    if openai_status:
        st.success(openai_message)
    else:
        st.error(openai_message)
with col2:
    st.subheader("Azure API")
    if azure_status:
        st.success(azure_message)
    else:
        st.error(azure_message)

# Video Analysis Section
youtube_url = st.text_input("YouTube Video URL", placeholder="https://www.youtube.com/watch?v=...")
if st.button("Analyze Video"):
    if not youtube_url:
        st.error("Please enter a valid YouTube URL Cummulative distribution function (CDF) of the video duration in minutes is given by:
    F(t) = 1 - e^(-0.1t), t ≥ 0
Find the probability that the duration of a randomly selected video is between 5 and 10 minutes.

To find the probability that the duration of a randomly selected video is between 5 and 10 minutes using the given cumulative distribution function (CDF), \( F(t) = 1 - e^{-0.1t} \) for \( t \geq 0 \), we proceed as follows:

The CDF \( F(t) \) gives the probability that the video duration \( T \) is less than or equal to \( t \), i.e., \( F(t) = P(T \leq t) \). To find the probability that the duration is between 5 and 10 minutes, \( P(5 < T < 10) \), we use the property of the CDF:

\[
P(a < T < b) = F(b) - F(a)
\]

Here, \( a = 5 \) and \( b = 10 \). So, we need to compute:

\[
P(5 < T < 10) = F(10) - F(5)
\]

### Step 1: Compute \( F(10) \)
Substitute \( t = 10 \) into the CDF:

\[
F(10) = 1 - e^{-0.1 \cdot 10} = 1 - e^{-1}
\]

Using the value of \( e^{-1} \approx 0.367879 \):

\[
F(10) = 1 - 0.367879 = 0.632121
\]

### Step 2: Compute \( F(5) \)
Substitute \( t = 5 \) into the CDF:

\[
F(5) = 1 - e^{-0.1 \cdot 5} = 1 - e^{-0.5}
\]

Using the value of \( e^{-0.5} \approx 0.606531 \):

\[
F(5) = 1 - 0.606531 = 0.393469
\]

### Step 3: Compute the Probability
Now, subtract \( F(5) \) from \( F(10) \):

\[
P(5 < T < 10) = F(10) - F(5) = 0.632121 - 0.393469 = 0.238652
\]

### Final Answer
The probability that the duration of a randomly selected video is between 5 and 10 minutes is approximately:

\[
\boxed{0.239}
\]
