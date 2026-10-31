import os
import subprocess
import tempfile
from pathlib import Path
import streamlit as st

st.set_page_config(page_title="AI Shorts Clipper", page_icon="🎬", layout="centered")

st.title("🎬 AI Shorts & Reels Clipper")
st.caption("Long video se automatically trending vertical 9:16 clips banayein.")

# Input
video_url = st.text_input("YouTube Video URL paste kijiye:", placeholder="https://www.youtube.com/watch?v=...")

col1, col2 = st.columns(2)
with col1:
    clip_duration = st.slider("Clip Duration (Seconds)", min_value=15, max_value=60, value=30, step=5)
with col2:
    start_point = st.selectbox("Kaunsa part chahiye?", ["Shuruat ka Hook (First 30s)", "Middle High Energy", "Climax / End Part", "Custom Seconds"])

custom_start = 0
if start_point == "Custom Seconds":
    custom_start = st.number_input("Video ke kis second se shuru karein?", min_value=0, value=30)

fair_use = st.checkbox("🛡️ Fair Use / Anti-Copyright Filters", value=True, help="1.02x subtle speed & color vibrance adjustments.")

if st.button("🚀 Generate Short Clip", type="primary"):
    if not video_url:
        st.warning("Pehle video ka link daaliye!")
    else:
        with st.status("Video process ho rahi hai...", expanded=True) as status:
            with tempfile.TemporaryDirectory() as temp_dir:
                try:
                    # 1. Download Video
                    status.write("📥 Step 1/3: Video download ho rahi hai...")
                    video_output = os.path.join(temp_dir, "input.mp4")
                    cmd_down = [
                        "yt-dlp",
                        "-f", "best[ext=mp4][height<=720]/best[height<=720]/best",
                        "-o", video_output,
                        video_url
                    ]
                    subprocess.run(cmd_down, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)

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

                    # 9:16 Blurred Background Filtergraph
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
                    subprocess.run(cmd_ffmpeg, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)

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
                  
