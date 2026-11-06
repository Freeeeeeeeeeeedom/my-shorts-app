import os
import re
import subprocess
import tempfile
import urllib.parse
from pathlib import Path
import streamlit as st

st.set_page_config(page_title="AI Video Studio", page_icon="🎬", layout="centered")

st.title("🎬 AI Full Video & Shorts Studio")
st.caption("10+ minute ki poori video ko bina cut kiye copyright-shield ke sath convert karein.")

# 1. Source selection
mode = st.radio("Aap video kaise dena chahte hain?", ["📁 Phone se Video Upload", "🔗 YouTube Video Link"], horizontal=True)

video_url = ""
uploaded_file = None

if mode == "📁 Phone se Video Upload":
    uploaded_file = st.file_uploader("Video select karein (MP4 / MOV / MKV):", type=["mp4", "mov", "mkv"])
else:
    video_url = st.text_input("YouTube Video URL paste kijiye:", placeholder="https://www.youtube.com/watch?v=...")

# 2. Output Mode
st.markdown("### ⚙️ Mode Settings")
output_type = st.radio(
    "Aapko kya karna hai?",
    ["🎥 Poori Video Copyright-Free Convert Karein (Full Video)", "🔥 Trending Shorts / Reels (Vertical Clips)"],
    index=0
)

num_clips = 1
clip_duration = 30

if output_type == "🔥 Trending Shorts / Reels (Vertical Clips)":
    col1, col2 = st.columns(2)
    with col1:
        num_clips = st.slider("Kitni Clips chahiye?", min_value=1, max_value=5, value=3)
    with col2:
        clip_duration = st.slider("Clip Duration (Seconds)", min_value=15, max_value=60, value=30, step=5)

# 3. Copyright Shields
st.markdown("### 🛡️ Copyright Protection Settings")
col_c1, col_c2 = st.columns(2)
with col_c1:
    video_shield = st.checkbox("🎬 Video Shield", value=True, help="Color grading & micro-speed alteration.")
with col_c2:
    audio_shield = st.checkbox("🎵 Audio Shield", value=True, help="Pitch shift & frequency modulation to bypass Content-ID.")

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

if st.button("🚀 Start Processing", type="primary"):
    if mode == "📁 Phone se Video Upload" and not uploaded_file:
        st.error("⚠️ Pehle video file select kijiye!")
    elif mode == "🔗 YouTube Video Link" and not video_url:
        st.error("⚠️ Pehle video link paste kijiye!")
    else:
        with st.status("Video process ho rahi hai (Isme 1-2 minute lagenge)...", expanded=True) as status:
            with tempfile.TemporaryDirectory() as temp_dir:
                try:
                    video_output = os.path.join(temp_dir, "input.mp4")

                    # Step 1: Save/Download Video
                    if mode == "📁 Phone se Video Upload":
                        status.write("📥 Step 1/2: Video file save ho rahi hai...")
                        with open(video_output, "wb") as f:
                            f.write(uploaded_file.getbuffer())
                    else:
                        status.write("📥 Step 1/2: YouTube video download ho rahi hai...")
                        target_url = clean_youtube_url(video_url)
                        cmd = ["yt-dlp", "--no-check-certificates", "--force-ipv4", "-f", "b/best", "-o", video_output, target_url]
                        res = subprocess.run(cmd, capture_output=True, text=True)
                        if res.returncode != 0:
                            raise RuntimeError(f"Download failed: {res.stderr[:200]}")

                    # Step 2: Ultra-Fast Render
                    status.write("⚡ Step 2/2: Turbo Engine se Video aur Audio Shields apply ho rahe hain...")
                    final_out = os.path.join(temp_dir, "output.mp4")

                    # Filters
                    vf = "eq=contrast=1.05:saturation=1.08,setpts=PTS/1.02,scale=-2:720" if video_shield else "scale=-2:720"
                    af = "asetrate=44100*1.03,aresample=44100,atempo=1.01,volume=1.05" if audio_shield else "volume=1.0"

                    if output_type == "🎥 Poori Video Copyright-Free Convert Karein (Full Video)":
                        cmd_ffmpeg = [
                            "ffmpeg", "-y",
                            "-i", video_output,
                            "-vf", vf,
                            "-af", af,
                            "-c:v", "libx264",
                            "-preset", "ultrafast",
                            "-crf", "26",
                            "-c:a", "aac",
                            "-b:a", "128k",
                            "-movflags", "+faststart",
                            final_out
                        ]
                    else:
                        # 9:16 Vertical for clips
                        vf_vertical = (
                            "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=20:5[bg];"
                            "[0:v]scale=1080:1920:force_original_aspect_ratio=decrease[fg];"
                            "[bg][fg]overlay=(W-w)/2:(H-h)/2,eq=contrast=1.05:saturation=1.08,setpts=PTS/1.02[v]"
                        )
                        cmd_ffmpeg = [
                            "ffmpeg", "-y",
                            "-ss", "10",
                            "-t", str(clip_duration),
                            "-i", video_output,
                            "-filter_complex", vf_vertical,
                            "-map", "[v]",
                            "-map", "0:a?",
                            "-af", af,
                            "-c:v", "libx264",
                            "-preset", "ultrafast",
                            "-crf", "26",
                            "-c:a", "aac",
                            "-b:a", "128k",
                            "-movflags", "+faststart",
                            final_out
                        ]

                    ff_res = subprocess.run(cmd_ffmpeg, capture_output=True, text=True)
                    if ff_res.returncode != 0:
                        raise RuntimeError(f"FFmpeg error: {ff_res.stderr[:200]}")

                    status.update(label="🎉 Video 100% Complete & Ready!", state="complete", expanded=False)

                    with open(final_out, "rb") as f:
                        v_bytes = f.read()

                    st.success("Aapki video safalta-purvak convert ho chuki hai!")
                    st.download_button(
                        label="⬇️ Download Converted Video (.mp4)",
                        data=v_bytes,
                        file_name="converted_video.mp4",
                        mime="video/mp4"
                    )
                    st.video(v_bytes)

                except Exception as e:
                    status.update(label="❌ Error aaya", state="error")
                    st.error(f"Process ruk gaya: {str(e)}")
