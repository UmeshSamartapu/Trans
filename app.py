import streamlit as st
from dotenv import load_dotenv
import os
import google.generativeai as genai
from youtube_transcript_api import YouTubeTranscriptApi
from urllib.parse import urlparse, parse_qs

load_dotenv()

# Configure Google Gemini API
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

def extract_video_id(url):
    """Extract video ID from various YouTube URL formats"""
    parsed = urlparse(url)
    if parsed.hostname == 'youtu.be':
        return parsed.path[1:]
    if parsed.hostname in ('www.youtube.com', 'youtube.com'):
        if parsed.path == '/watch':
            return parse_qs(parsed.query)['v'][0]
        if parsed.path.startswith('/embed/'):
            return parsed.path.split('/')[2]
        if parsed.path.startswith('/v/'):
            return parsed.path.split('/')[2]
    return None

def get_transcript_text(youtube_url, language='en'):
    """Fetch and concatenate YouTube transcript"""
    try:
        video_id = extract_video_id(youtube_url)
        if not video_id:
            st.error("Invalid YouTube URL")
            return None
            
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        try:
            transcript = transcript_list.find_transcript([language])
        except Exception as e:
            try:
                transcript = transcript_list.find_transcript(['en'])
                st.warning(f"Transcript not available in selected language. Using English instead.")
            except Exception as e:
                st.error(f"Could not find transcript: {str(e)}")
                return None
        
        try:
            transcript_data = transcript.fetch()
        except Exception as e:
            st.error(f"Failed to fetch transcript data: {str(e)}")
            return None
            
        if not transcript_data:
            st.error("No transcript data received")
            return None
            
        if not isinstance(transcript_data, list):
            st.error("Received invalid transcript data format")
            return None
            
        transcript_text = []
        for entry in transcript_data:
            try:
                if isinstance(entry, dict) and 'text' in entry and entry['text']:
                    transcript_text.append(entry['text'].strip())
            except Exception as e:
                continue
        
        if not transcript_text:
            st.error("No valid transcript text found in the video")
            return None
            
        return " ".join(transcript_text)
        
    except Exception as e:
        st.error(f"Error fetching transcript: {str(e)}")
        return None

def generate_summary(transcript, prompt):
    """Generate summary using Gemini"""
    try:
        model = genai.GenerativeModel('gemini-pro')
        
        response = model.generate_content(prompt + transcript)
        return response.text
    except Exception as e:
        st.error(f"AI Generation Error: {str(e)}")
        return None

# Streamlit UI
st.title("YouTube Video Summarizer")
st.markdown("Enter a YouTube URL to get AI-generated summary")

youtube_url = st.text_input("YouTube URL:")
language = st.selectbox("Select transcript language", ['en', 'es', 'fr', 'de', 'it', 'pt'])
summary_length = st.select_slider("Summary Length", options=['Short', 'Medium', 'Long'], value='Medium')

length_prompts = {
    'Short': 'Generate a brief summary (max 100 words)',
    'Medium': 'Generate a comprehensive summary (max 250 words)',
    'Long': 'Generate a detailed summary (max 500 words)'
}

DEFAULT_PROMPT = f"""You are a professional YouTube content analyzer. 
Generate a {summary_length.lower()} summary of this video transcript with these elements:
1. Key topics covered
2. Main points discussed
3. Important conclusions
4. Overall significance

{length_prompts[summary_length]}. Present in clear, concise bullet points:\n"""

if youtube_url:
    try:
        video_id = extract_video_id(youtube_url)
        if video_id:
            st.image(f"https://img.youtube.com/vi/{video_id}/0.jpg", 
                    caption="Video Thumbnail", use_column_width=True)
    except:
        pass

if st.button("Generate Summary"):
    if youtube_url:
        with st.spinner("Analyzing video..."):
            transcript = get_transcript_text(youtube_url)
            if transcript:
                summary = generate_summary(transcript, DEFAULT_PROMPT)
                if summary:
                    st.subheader("Video Summary")
                    st.markdown(summary)
                else:
                    st.error("Failed to generate summary")
            else:
                st.error("Could not retrieve transcript")
    else:
        st.warning("Please enter a YouTube URL first")