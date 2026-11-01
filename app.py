import os
import re
import subprocess
import tempfile
import urllib.parse
from pathlib import Path
import streamlit as st

st.set_page_config(page_title="AI Video & Shorts Clipper", page_icon="🎬", layout="centered")

st.title("🎬 AI Video & Shorts Studio")
st.caption("Long video se viral clips banayein ya poori video ko copyright-free convert karein.")

# 1. Source selection
mode = st.radio("Aap video kaise dena chahte hain?", ["📁 Phone se Video Upload (Recommended)", "🔗 YouTube Video Link"], horizontal=True)

video_url = ""
uploaded_file = None

if mode == "📁 Phone se Video Upload (Recommended)":
    uploaded_file = st.file_uploader("Apne phone ki gallery se video select karein (MP4 / MOV / MKV):", type=["mp4", "mov", "mkv"])
else:
    video_url = st.text_input("YouTube Video URL paste kijiye:", placeholder="https://www.youtube.com/watch?v=...")

# 2. Output Type: Clips vs Full Video
st.markdown("### ⚙️ Output Settings")
output_type = st.radio(
    "Aapko kya chahiye?",
    ["🔥 Trending Shorts / Reels (Vertical 9:16 Clips)", "🎥 Poori Video Copyright-Free Convert Karein (Full Video)"],
    help="Clips se chhote-chhote shorts banenge. Full Video se poori lambi video bina cut kiye copyright-shield ke sath ready hogi."
)

num_clips = 1
clip_duration = 30

if output_type == "🔥 Trending Shorts / Reels (Vertical 9:16 Clips)":
    col1, col2 = st.columns(2)
    with col1:
        num_clips = st.slider("Kitni Clips chahiye?", min_value=1, max_value=5, value=3)
    with col2:
        clip_duration = st.slider("Har Clip ki Duration (Seconds)", min_value=15, max_value=60, value=30, step=5)
else:
    st.info("ℹ️ Poori video bina cut kiye transform hogi taaki YouTube, Facebook aur Instagram par Copyright na aaye.")

# 3. Copyright Shields
st.markdown("### 🛡️ Copyright Protection Settings")
col_c1, col_c2 = st.columns(2)
with col_c1:
    video_shield = st.checkbox("🎬 Video Shield (Color & Vibrance Modulation)", value=True, help="Color grading & subtle speed adjustment taaki video Content-ID bot match na ho.")
with col_c2:
    audio_shield = st.checkbox("🎵 Audio Shield (Anti-Content ID)", value=True, help="Pitch shift (+3%) & frequency modulation jisse YouTube/FB ka audio fingerprint bypass ho.")

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

def get_video_duration(video_path: str) -> float:
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        video_path
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    try:
        return float(res.stdout.strip())
    except Exception:
        return 180.0

if st.button("🚀 Process Video", type="primary"):
    if mode == "📁 Phone se Video Upload (Recommended)" and not uploaded_file:
        st.error("⚠️ Pehle 'Upload' button par tap karke apne phone se koi video select kijiye!")
    elif mode == "🔗 YouTube Video Link" and not video_url:
        st.error("⚠️ Pehle YouTube video ka link box mein paste kijiye!")
    else:
        with st.status("Video process ho rahi hai...", expanded=True) as status:
            with tempfile.TemporaryDirectory() as temp_dir:
                try:
                    video_output = os.path.join(temp_dir, "input.mp4")

                    # Step 1: Obtain Video
                    if mode == "📁 Phone se Video Upload (Recommended)":
                        status.write("📥 Step 1: Phone se video load ho rahi hai...")
                        with open(video_output, "wb") as f:
                            f.write(uploaded_file.getbuffer())
                    else:
                        status.write("📥 Step 1: YouTube video download ho rahi hai...")
                        target_url = clean_youtube_url(video_url)
                        cmd = [
                            "yt-dlp",
                            "--no-check-certificates",
                            "--force-ipv4",
                            "-f", "b/best",
                            "-o", video_output,
                            target_url
                        ]
                        res = subprocess.run(cmd, capture_output=True, text=True)
                        if res.returncode != 0:
                            raise RuntimeError(f"Download blocked by YouTube: {res.stderr[:200]}")

                    total_dur = get_video_duration(video_output)
                    status.write(f"⏱️ Video length: {int(total_dur)} seconds")

                    # Audio Filter string
                    af = "asetrate=44100*1.03,aresample=44100,atempo=1.01,volume=1.05" if audio_shield else "volume=1.0"

                    # CASE A: Full Video Mode (bina cut kiye)
                    if output_type == "🎥 Poori Video Copyright-Free Convert Karein (Full Video)":
                        status.write("🎞️ Step 2: Poori video par Anti-Copyright filters lagaye ja rahe hain...")
                        full_out = os.path.join(temp_dir, "full_copyright_free.mp4")

                        vf = "eq=contrast=1.06:saturation=1.1,setpts=PTS/1.02" if video_shield else "null"

                        cmd_ffmpeg = [
                            "ffmpeg", "-y",
                            "-i", video_output,
                            "-vf", vf,
                            "-af", af,
                            "-c:v", "libx264",
                            "-preset", "veryfast",
                            "-crf", "24",
                            "-c:a", "aac",
                            "-b:a", "192k",
                            "-movflags", "+faststart",
                            full_out
                        ]
                        ff_res = subprocess.run(cmd_ffmpeg, capture_output=True, text=True)
                        if ff_res.returncode != 0:
                            raise RuntimeError(f"FFmpeg error: {ff_res.stderr[:300]}")

                        status.update(label="🎉 Poori Video Taiyar!", state="complete", expanded=False)

                        with open(full_out, "rb") as f:
                            full_bytes = f.read()

                        st.subheader("🎥 Aapki Full Copyright-Free Video")
                        st.video(full_bytes)
                        st.download_button(
                            label="⬇️ Download Full Video (.mp4)",
                            data=full_bytes,
                            file_name="full_copyright_free_video.mp4",
                            mime="video/mp4"
                        )

                    # CASE B: Multiple Shorts / Clips Mode
                    else:
                        status.write(f"🎞️ Step 2: {num_clips} Vertical (9:16) Shorts render ho rahe hain...")
                        
                        vf = (
                            "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=20:5[bg];"
                            "[0:v]scale=1080:1920:force_original_aspect_ratio=decrease[fg];"
                            "[bg][fg]overlay=(W-w)/2:(H-h)/2,"
                            "eq=contrast=1.06:saturation=1.1,setpts=PTS/1.02[v]"
                        ) if video_shield else (
                            "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=20:5[bg];"
                            "[0:v]scale=1080:1920:force_original_aspect_ratio=decrease[fg];"
                            "[bg][fg]overlay=(W-w)/2:(H-h)/2[v]"
                        )

                        # Calculate timestamps for multiple clips evenly
                        step = max(10.0, (total_dur - clip_duration) / max(1, num_clips))
                        rendered_clips = []

                        for i in range(num_clips):
                            ss = min(i * step, max(0.0, total_dur - clip_duration))
                            clip_out = os.path.join(temp_dir, f"clip_{i+1}.mp4")

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
                                "-b:a", "192k",
                                "-movflags", "+faststart",
                                clip_out
                            ]
                            ff_res = subprocess.run(cmd_ffmpeg, capture_output=True, text=True)
                            if ff_res.returncode == 0 and os.path.exists(clip_out):
                                with open(clip_out, "rb") as f:
                                    rendered_clips.append((i + 1, int(ss), f.read()))

                        status.update(label=f"🎉 {len(rendered_clips)} Clips Taiyar!", state="complete", expanded=False)

                        st.subheader(f"🔥 Aapke {len(rendered_clips)} Trending Shorts")
                        for idx, start_sec, c_bytes in rendered_clips:
                            st.markdown(f"#### 🎬 Clip #{idx} (From {start_sec}s - {start_sec + clip_duration}s)")
                            st.video(c_bytes)
                            st.download_button(
                                label=f"⬇️ Download Clip #{idx} (.mp4)",
                                data=c_bytes,
                                file_name=f"short_clip_{idx}.mp4",
                                mime="video/mp4",
                                key=f"dl_clip_{idx}"
                            )
                            st.markdown("---")

                except Exception as e:
                    status.update(label="❌ Error aaya", state="error")
                    st.error(f"Process complete nahi ho paya: {str(e)}")
