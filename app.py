import os
import re
import subprocess
import tempfile
import urllib.parse
from pathlib import Path
import streamlit as st

st.set_page_config(page_title="AI Video & Shorts Studio Pro", page_icon="🎬", layout="centered")

st.title("🎬 AI Video & Shorts Studio Pro")
st.caption("High-Resolution Shorts, Viral Hooks, Watermark aur Pro Anti-Copyright Shield.")

# 1. Source selection
mode = st.radio(
    "Aap video kaise dena chahte hain?",
    ["📁 Phone se Video Upload", "🔗 YouTube Video Link"],
    horizontal=True
)

video_url = ""
uploaded_file = None

if mode == "📁 Phone se Video Upload":
    uploaded_file = st.file_uploader("Video select karein (MP4 / MOV / MKV):", type=["mp4", "mov", "mkv"])
else:
    video_url = st.text_input("YouTube Video URL paste kijiye:", placeholder="https://www.youtube.com/watch?v=...")

# 2. Output Mode & Resolution
st.markdown("### ⚙️ Mode & Quality Settings")
output_type = st.radio(
    "Aapko kya karna hai?",
    [
        "🔥 Trending Shorts / Reels (Vertical 9:16 Clips)",
        "🎥 Poori Video Copyright-Free Convert Karein (Full Video)"
    ],
    index=0
)

col_q1, col_q2 = st.columns(2)
with col_q1:
    quality_mode = st.selectbox(
        "Video Resolution & Quality",
        ["High Quality (1080p HD)", "Fast Turbo (720p)"],
        index=0
    )
with col_q2:
    preset_speed = "veryfast" if "1080p" in quality_mode else "ultrafast"
    crf_val = "21" if "1080p" in quality_mode else "25"
    st.caption(f"⚡ Render Profile: **{quality_mode}**")

num_clips = 1
clip_duration = 30
clip_timing_mode = "Auto (Poori Video se Alag-Alag Parts)"
custom_start_str = "00:10"

if output_type == "🔥 Trending Shorts / Reels (Vertical 9:16 Clips)":
    col1, col2 = st.columns(2)
    with col1:
        num_clips = st.slider("Kitni Clips chahiye?", min_value=1, max_value=5, value=3)
    with col2:
        clip_duration = st.slider("Har Clip ki Duration (Seconds)", min_value=15, max_value=60, value=30, step=5)

    clip_timing_mode = st.radio(
        "Clips kahan se cut karein?",
        ["Auto (Poori Video se Alag-Alag Parts)", "Exact Time Selection (MM:SS)"],
        horizontal=True
    )
    if clip_timing_mode == "Exact Time Selection (MM:SS)":
        custom_start_str = st.text_input("Start Time likhein (MM:SS format mein, jaise 01:30):", value="00:15")
        num_clips = 1

# 3. Viral Hook & Watermark Settings
st.markdown("### ✍️ Viral Hook & Branding")
hook_presets = [
    "None (Koi Text Nahi)",
    "WAIT FOR THE END!",
    "WATCH TILL THE END",
    "99% PEOPLE MISS THIS",
    "UNBELIEVABLE MOMENT",
    "Custom Hook Likhein..."
]
selected_hook = st.selectbox("Top Viral Hook Text chunein:", hook_presets, index=1)
custom_hook_text = ""
if selected_hook == "Custom Hook Likhein...":
    custom_hook_text = st.text_input("Apna Viral Hook likhein:", placeholder="e.g. YE SCENE MISS MAT KARNA!")
elif selected_hook != "None (Koi Text Nahi)":
    custom_hook_text = selected_hook

watermark_text = st.text_input("Apna Page / Channel Watermark (Optional):", placeholder="e.g. @YourPageName")

# 4. Pro Copyright Protection Settings
st.markdown("### 🛡️ Pro Anti-Copyright Shield")
col_c1, col_c2, col_c3 = st.columns(3)
with col_c1:
    video_shield = st.checkbox("🎬 Color & Speed", value=True, help="Vibrance boost + 1.02x micro-speed.")
with col_c2:
    pro_visual = st.checkbox("🪞 Mirror & Zoom", value=True, help="Horizontal flip + 6% smart zoom-in.")
with col_c3:
    audio_shield = st.checkbox("🎵 Audio Shield", value=True, help="+3% Pitch shift & tempo alteration.")


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


def parse_time_to_seconds(time_str: str) -> float:
    parts = time_str.strip().split(":")
    try:
        if len(parts) == 2:
            return int(parts[0]) * 60 + float(parts[1])
        elif len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
        return max(0.0, float(time_str))
    except Exception:
        return 0.0


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
        return 120.0


def find_font_path() -> str:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return ""


def escape_drawtext(text: str) -> str:
    return (
        text.replace("\\", "\\\\")
        .replace(":", "\\:")
        .replace("'", "")
        .replace('"', "")
        .replace("%", "\\%")
    )


def build_text_filters(hook: str, watermark: str, is_vertical: bool) -> str:
    font_path = find_font_path()
    font_opt = f"fontfile={font_path}:" if font_path else ""
    filters = []

    if hook.strip():
        safe_hook = escape_drawtext(hook.strip())
        fontsize = "54" if is_vertical else "38"
        y_pos = "180" if is_vertical else "40"
        filters.append(
            f"drawtext={font_opt}text='{safe_hook}':fontcolor=white:fontsize={fontsize}:"
            f"box=1:boxcolor=red@0.85:boxborderw=18:x=(w-text_w)/2:y={y_pos}"
        )

    if watermark.strip():
        safe_wm = escape_drawtext(watermark.strip())
        fontsize = "36" if is_vertical else "28"
        y_pos = "h-180" if is_vertical else "h-60"
        filters.append(
            f"drawtext={font_opt}text='{safe_wm}':fontcolor=white@0.85:fontsize={fontsize}:"
            f"box=1:boxcolor=black@0.55:boxborderw=10:x=(w-text_w)/2:y={y_pos}"
        )

    return ",".join(filters)


if st.button("🚀 Start Processing", type="primary"):
    if mode == "📁 Phone se Video Upload" and not uploaded_file:
        st.error("⚠️ Pehle video file select kijiye!")
    elif mode == "🔗 YouTube Video Link" and not video_url:
        st.error("⚠️ Pehle video link paste kijiye!")
    else:
        with st.status("Video process ho rahi hai...", expanded=True) as status:
            with tempfile.TemporaryDirectory() as temp_dir:
                try:
                    video_output = os.path.join(temp_dir, "input.mp4")

                    # Step 1: Save/Download Video
                    if mode == "📁 Phone se Video Upload":
                        status.write("📥 Step 1/2: Video file load ho rahi hai...")
                        with open(video_output, "wb") as f:
                            f.write(uploaded_file.getbuffer())
                    else:
                        status.write("📥 Step 1/2: YouTube video download ho rahi hai...")
                        target_url = clean_youtube_url(video_url)
                        cmd = [
                            "yt-dlp", "--no-check-certificates", "--force-ipv4",
                            "-f", "b/best", "-o", video_output, target_url
                        ]
                        res = subprocess.run(cmd, capture_output=True, text=True)
                        if res.returncode != 0:
                            raise RuntimeError(f"Download failed: {res.stderr[:200]}")

                    total_dur = get_video_duration(video_output)
                    status.write(f"⏱️ Video length: {int(total_dur)} seconds")

                    af = "asetrate=44100*1.03,aresample=44100,atempo=1.01,volume=1.05" if audio_shield else "volume=1.0"

                    # CASE A: Full Video Mode
                    if output_type == "🎥 Poori Video Copyright-Free Convert Karein (Full Video)":
                        status.write(f"🎞️ Step 2/2: Poori video ({quality_mode}) render ho rahi hai...")
                        final_out = os.path.join(temp_dir, "full_pro_video.mp4")

                        vf_parts = []
                        if pro_visual:
                            vf_parts.append("hflip,crop=iw*0.94:ih*0.94")
                        if "1080p" in quality_mode:
                            vf_parts.append("scale=-2:1080")
                        else:
                            vf_parts.append("scale=-2:720")
                        if video_shield:
                            vf_parts.append("eq=contrast=1.05:saturation=1.08,setpts=PTS/1.02")

                        txt_filter = build_text_filters(custom_hook_text, watermark_text, is_vertical=False)
                        if txt_filter:
                            vf_parts.append(txt_filter)

                        vf_str = ",".join(vf_parts)

                        cmd_ffmpeg = [
                            "ffmpeg", "-y",
                            "-i", video_output,
                            "-vf", vf_str,
                            "-af", af,
                            "-c:v", "libx264",
                            "-preset", preset_speed,
                            "-crf", crf_val,
                            "-c:a", "aac",
                            "-b:a", "192k",
                            "-movflags", "+faststart",
                            final_out
                        ]
                        ff_res = subprocess.run(cmd_ffmpeg, capture_output=True, text=True)
                        if ff_res.returncode != 0:
                            raise RuntimeError(f"FFmpeg error: {ff_res.stderr[-300:]}")

                        status.update(label="🎉 Full Video Taiyar!", state="complete", expanded=False)

                        with open(final_out, "rb") as f:
                            v_bytes = f.read()

                        st.success("Aapki Full HD Copyright-Protected Video taiyar hai!")
                        st.download_button(
                            label="⬇️ Download Full Video (.mp4)",
                            data=v_bytes,
                            file_name="pro_copyright_free_video.mp4",
                            mime="video/mp4"
                        )
                        st.video(v_bytes)

                    # CASE B: Vertical 9:16 Shorts / Clips Mode
                    else:
                        out_w, out_h = (1080, 1920) if "1080p" in quality_mode else (720, 1280)
                        status.write(f"🎞️ Step 2/2: {num_clips} Shorts ({out_w}x{out_h}) render ho rahe hain...")

                        fg_transforms = []
                        if pro_visual:
                            fg_transforms.append("hflip,crop=iw*0.94:ih*0.94")
                        fg_transforms.append(f"scale={out_w}:{out_h}:force_original_aspect_ratio=decrease")
                        fg_chain = ",".join(fg_transforms)

                        post_transforms = []
                        if video_shield:
                            post_transforms.append("eq=contrast=1.05:saturation=1.08,setpts=PTS/1.02")
                        txt_filter = build_text_filters(custom_hook_text, watermark_text, is_vertical=True)
                        if txt_filter:
                            post_transforms.append(txt_filter)

                        post_chain = ("," + ",".join(post_transforms)) if post_transforms else ""

                        vf_complex = (
                            f"[0:v]scale={out_w}:{out_h}:force_original_aspect_ratio=increase,crop={out_w}:{out_h},boxblur=20:5[bg];"
                            f"[0:v]{fg_chain}[fg];"
                            f"[bg][fg]overlay=(W-w)/2:(H-h)/2{post_chain}[v]"
                        )

                        if clip_timing_mode == "Exact Time Selection (MM:SS)":
                            timestamps = [min(parse_time_to_seconds(custom_start_str), max(0.0, total_dur - 5))]
                        else:
                            step = max(5.0, (total_dur - clip_duration) / max(1, num_clips))
                            timestamps = [
                                min(i * step, max(0.0, total_dur - clip_duration))
                                for i in range(num_clips)
                            ]

                        rendered_clips = []
                        for idx, ss in enumerate(timestamps):
                            clip_out = os.path.join(temp_dir, f"short_{idx+1}.mp4")
                            cmd_ffmpeg = [
                                "ffmpeg", "-y",
                                "-ss", str(ss),
                                "-t", str(clip_duration),
                                "-i", video_output,
                                "-filter_complex", vf_complex,
                                "-map", "[v]",
                                "-map", "0:a?",
                                "-af", af,
                                "-c:v", "libx264",
                                "-preset", preset_speed,
                                "-crf", crf_val,
                                "-c:a", "aac",
                                "-b:a", "192k",
                                "-movflags", "+faststart",
                                clip_out
                            ]
                            ff_res = subprocess.run(cmd_ffmpeg, capture_output=True, text=True)
                            if ff_res.returncode != 0:
                                raise RuntimeError(f"FFmpeg error on Clip #{idx+1}: {ff_res.stderr[-300:]}")
                            with open(clip_out, "rb") as f:
                                rendered_clips.append((idx + 1, int(ss), f.read()))

                        status.update(label=f"🎉 {len(rendered_clips)} Shorts Taiyar!", state="complete", expanded=False)

                        st.subheader(f"🔥 Aapke {len(rendered_clips)} Viral Shorts")
                        for c_idx, start_s, c_bytes in rendered_clips:
                            st.markdown(f"#### 🎬 Clip #{c_idx} (Start: {start_s}s)")
                            st.video(c_bytes)
                            st.download_button(
                                label=f"⬇️ Download Clip #{c_idx} (.mp4)",
                                data=c_bytes,
                                file_name=f"viral_short_{c_idx}.mp4",
                                mime="video/mp4",
                                key=f"dl_{c_idx}"
                            )
                            st.markdown("---")

                except Exception as e:
                    status.update(label="❌ Error aaya", state="error")
                    st.error(f"Process ruk gaya: {str(e)}")
