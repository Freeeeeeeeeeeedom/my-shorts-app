
import os
import re
import subprocess
import tempfile
import urllib.parse
from pathlib import Path
import streamlit as st

st.set_page_config(page_title="AI Shorts Clipper", page_icon="🎬", layout="centered")

st.title("🎬 AI Shorts & Reels Clipper")
st.caption("Long video se automatically trending vertical 9:16 clips banayein.")

# Tab for URL or Direct Phone Upload
tab1, tab2 = st.tabs(["🔗 YouTube / Video Link", "📁 Phone se Video Upload"])

video_url = ""
uploaded_file = None

with tab1:
    video_url = st.text_input("YouTube Video URL paste kijiye:", placeholder="https://www.youtube.com/watch?v=...")

with tab2:
    uploaded_file = st.file_uploader("Apne phone se video select karein (MP4 / MOV):", type=["mp4", "mov", "mkv"])

col1, col2 = st.columns(2)
with col1:
    clip_duration = st.slider("Clip Duration (Seconds)", min_value=15, max_value=60, value=30, step=5)
with col2:
    start_point = st.selectbox("Kaunsa part chahiye?", ["Shuruat ka Hook (First 30s)", "Middle High Energy", "Climax / End Part", "Custom Seconds"])

custom_start = 0
if start_point == "Custom Seconds":
    custom_start = st.number_input("Video ke kis second se shuru karein?", min_value=0, value=30)

fair_use = st.checkbox("🛡️ Fair Use / Anti-Copyright Filters", value=True, help="1.02x subtle speed & color vibrance adjustments.")

def clean_youtube_url(url: str) -> str:
    url = url.strip()
    if "youtu.be/" in url:
        video_id = url.split("youtu.be/")[1].split("?")[0]
        return f"https://www.youtube.com/watch?v={video_id}"
    elif "youtube.com/watch" in url:
        parsed = urllib.parse.urlparse(url)
        queries = urllib.parse.parse_qs(parsed.query)
        if "v" in queries:
            return f"https://www.youtube.com/watch?v={queries['v'][0]}"
    return url

if st.button("🚀 Generate Short Clip", type="primary"):
    if not video_url and not uploaded_file:
        st.warning("Pehle video ka link daaliye ya file upload kijiye!")
    else:
        with st.status("Video process ho rahi hai...", expanded=True) as status:
            with tempfile.TemporaryDirectory() as temp_dir:
                try:
                    video_output = os.path.join(temp_dir, "input.mp4")

                    # 1. Obtain Video
                    if uploaded_file:
                        status.write("📥 Step 1/3: Uploaded video save ho rahi hai...")
                        with open(video_output, "wb") as f:
                            f.write(uploaded_file.getbuffer())
                    else:
                        status.write("📥 Step 1/3: YouTube video download ho rahi hai...")
                        target_url = clean_youtube_url(video_url)
                        
                        cmd_down = [
                            "yt-dlp",
                            "--no-check-certificates",
                            "--extractor-args", "youtube:player_client=android,web",
                            "-f", "best[height<=720]/bestvideo[height<=720]+bestaudio/best",
                            "-o", video_output,
                            target_url
                        ]
                        res = subprocess.run(cmd_down, capture_output=True, text=True)
                        if res.returncode != 0:
                            cmd_fallback = [
                                "yt-dlp",
                                "--no-check-certificates",
                                "-f", "b/best",
                                "-o", video_output,
                                target_url
                            ]
                            res2 = subprocess.run(cmd_fallback, capture_output=True, text=True)
                            if res2.returncode != 0:
                                error_msg = res.stderr or res2.stderr or "Unknown download error"
                                raise RuntimeError(f"YouTube Download Error: {error_msg}")

                    # Determine Start Time
                    if start_point == "Shuruat ka Hook (First 30s)":
                        ss = 5
                    elif start_point == "Middle High Energy":
                        ss = 45
                    elif start_point == "Climax / End Part":
                        ss = 90
                    else:
                        ss = custom_start

                    # 2. Render 9:16 Vertical Short
                    status.write("🎞️ Step 2/3: 9:16 Vertical format aur Fair-Use filters lag rahe hain...")
                    short_output = os.path.join(temp_dir, "short.mp4")

                    vf = (
                        "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=20:5[bg];"
                        "[0:v]scale=1080:1920:force_original_aspect_ratio=decrease[fg];"
                        "[bg][fg]overlay=(W-w)/2:(H-h)/2,"
                        "eq=contrast=1.05:saturation=1.08,setpts=PTS/1.02[v]"
                    )
                    af = "atempo=1.02" if fair_use else "volume=1.0"

                    cmd_ffmpeg = [
                        "ffmpeg", "-y",
                        "-ss", str(ss),
                        "-t", str(clip_duration),
                        "-i", video_output,
                        "-filter_complex", vf,
                        "-map", "[v]",
                        "-map", "0:a?",
                        "-af", af,
                        "-c:v", "libx264",
                        "-preset", "veryfast",
                        "-crf", "24",
                        "-c:a", "aac",
                        "-movflags", "+faststart",
                        short_output
                    ]
                    ff_res = subprocess.run(cmd_ffmpeg, capture_output=True, text=True)
                    if ff_res.returncode != 0:
                        raise RuntimeError(f"FFmpeg error: {ff_res.stderr}")

                    # 3. Read and Show
                    status.write("✅ Step 3/3: Short ready hai!")
                    status.update(label="🎉 Short Clip Taiyar!", state="complete", expanded=False)

                    with open(short_output, "rb") as f:
                        video_bytes = f.read()

                    st.video(video_bytes)
                    st.download_button(
                        label="⬇️ Download Short Video (.mp4)",
                        data=video_bytes,
                        file_name="trending_short.mp4",
                        mime="video/mp4"
                    )

                except Exception as e:
                    status.update(label="❌ Error aaya", state="error")
                    st.error(f"Process complete nahi ho paya: {str(e)}")
