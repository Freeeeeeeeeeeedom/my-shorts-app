import io
import os
import subprocess
import tempfile
import zipfile
from pathlib import Path
import streamlit as st

st.set_page_config(page_title="AI Video, Shorts & Song Studio", page_icon="🎬", layout="centered")

# Aliases for safe execution
st_radio = getattr(st, "radio")
st_video = getattr(st, "video")
st_audio = getattr(st, "audio")
st_download = getattr(st, "download_button")
run_cmd = getattr(subprocess, "run")
zip_deflated = getattr(zipfile, "ZIP_DEFLATED")

# Session state so generated clips/songs stay visible across download clicks
if "generated_clips" not in st.session_state:
    st.session_state.generated_clips = []
if "generated_full_video" not in st.session_state:
    st.session_state.generated_full_video = None
if "generated_audio_song" not in st.session_state:
    st.session_state.generated_audio_song = None
if "zip_bytes" not in st.session_state:
    st.session_state.zip_bytes = None

st.title("🎬 AI Video, Shorts & Song Studio")
st.caption("Phone se video ya song upload karke Copyright-Free Shorts, Full Video ya Audio Song (.mp3) banayein.")

# 1. File Upload
uploaded_file = st.file_uploader(
    "📁 Apne phone se Video ya Audio Song select karein:",
    type=["mp4", "mov", "mkv", "mp3", "wav", "m4a"]
)

# 2. Output Mode Selection
st.markdown("### ⚙️ Aapko Kya Banana Hai?")
output_type = st_radio(
    "Option chunein:",
    [
        "🔥 Trending Shorts / Reels (Vertical 9:16 Clips)",
        "🎥 Full Video Copyright-Free (Poori Video)",
        "🎶 Copyright-Free Video Song (.mp4)",
        "🎧 Copyright-Free Audio Song (.mp3)"
    ],
    index=0
)

is_audio_only = output_type == "🎧 Copyright-Free Audio Song (.mp3)"
is_shorts = output_type == "🔥 Trending Shorts / Reels (Vertical 9:16 Clips)"
is_full_or_vsong = output_type in [
    "🎥 Full Video Copyright-Free (Poori Video)",
    "🎶 Copyright-Free Video Song (.mp4)"
]

# Resolution & Quality (shown only for video outputs)
quality_mode = "Fast Turbo (720p)"
preset_speed = "ultrafast"
crf_val = "25"

if not is_audio_only:
    col_q1, col_q2 = st.columns(2)
    with col_q1:
        quality_mode = st.selectbox(
            "Video Resolution & Quality",
            ["High Quality (1080p HD)", "Fast Turbo (720p)"],
            index=0 if is_shorts else 1
        )
    with col_q2:
        preset_speed = "veryfast" if "1080p" in quality_mode else "ultrafast"
        crf_val = "21" if "1080p" in quality_mode else "25"
        st.caption(f"⚡ Render Profile: **{quality_mode}**")

# Clips settings (only for Shorts)
num_clips = 1
clip_duration = 30
clip_timing_mode = "Auto (Poori Video se Alag-Alag Parts)"
custom_start_str = "00:10"

if is_shorts:
    col1, col2 = st.columns(2)
    with col1:
        num_clips = st.slider("Kitni Clips chahiye?", min_value=1, max_value=5, value=3)
    with col2:
        clip_duration = st.slider("Har Clip ki Duration (Seconds)", min_value=15, max_value=60, value=30, step=5)

    clip_timing_mode = st_radio(
        "Clips kahan se cut karein?",
        ["Auto (Poori Video se Alag-Alag Parts)", "Exact Time Selection (MM:SS)"],
        horizontal=True
    )
    if clip_timing_mode == "Exact Time Selection (MM:SS)":
        custom_start_str = st.text_input("Start Time likhein (MM:SS format mein, jaise 01:30):", value="00:15")
        num_clips = 1

# 3. Viral Hook & Watermark (only for video outputs)
custom_hook_text = ""
watermark_text = ""
if not is_audio_only:
    st.markdown("### ✍️ Viral Hook & Branding")
    hook_presets = [
        "None (Koi Text Nahi)",
        "WAIT FOR THE END!",
        "WATCH TILL THE END",
        "99% PEOPLE MISS THIS",
        "UNBELIEVABLE MOMENT",
        "Custom Hook Likhein..."
    ]
    default_hook_idx = 1 if is_shorts else 0
    selected_hook = st.selectbox("Top Viral Hook Text chunein:", hook_presets, index=default_hook_idx)
    if selected_hook == "Custom Hook Likhein...":
        custom_hook_text = st.text_input("Apna Viral Hook likhein:", placeholder="e.g. YE SCENE MISS MAT KARNA!")
    elif selected_hook != "None (Koi Text Nahi)":
        custom_hook_text = selected_hook

    watermark_text = st.text_input("Apna Page / Channel Watermark (Optional):", placeholder="e.g. @RoKoClips")

# 4. Pro Copyright Protection Settings
st.markdown("### 🛡️ Pro Anti-Copyright Shield")
if is_audio_only:
    audio_shield = st.checkbox(
        "🎵 Audio Shield (Pitch +3% & Tempo Modulation)",
        value=True,
        help="Audio fingerprint badalne ke liye pitch aur tempo shift karta hai."
    )
    video_shield = False
    pro_visual = False
else:
    col_c1, col_c2, col_c3 = st.columns(3)
    with col_c1:
        video_shield = st.checkbox("🎬 Color & Speed", value=True, help="Vibrance boost + 1.02x micro-speed.")
    with col_c2:
        pro_visual = st.checkbox("🪞 Mirror & Zoom", value=True, help="Horizontal flip + 6% smart zoom-in.")
    with col_c3:
        audio_shield = st.checkbox("🎵 Audio Shield", value=True, help="+3% Pitch shift & tempo alteration.")


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


def get_media_duration(media_path: str) -> float:
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        media_path
    ]
    res = run_cmd(cmd, capture_output=True, text=True)
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
    if not uploaded_file:
        st.error("⚠️ Pehle upar se koi Video ya Audio file select kijiye!")
    else:
        st.session_state.generated_clips = []
        st.session_state.generated_full_video = None
        st.session_state.generated_audio_song = None
        st.session_state.zip_bytes = None

        with st.status("Process shuru ho rahi hai...", expanded=True) as status:
            with tempfile.TemporaryDirectory() as temp_dir:
                try:
                    ext = Path(uploaded_file.name).suffix or ".mp4"
                    input_path = os.path.join(temp_dir, f"input{ext}")

                    status.write("📥 Step 1/2: File load ho rahi hai...")
                    Path(input_path).write_bytes(uploaded_file.getbuffer())

                    af = "asetrate=44100*1.03,aresample=44100,atempo=1.01,volume=1.05" if audio_shield else "volume=1.0"

                    # CASE 1: Copyright-Free Audio Song (.mp3)
                    if is_audio_only:
                        status.write("🎧 Step 2/2: Audio Song (.mp3) copyright-shield ke sath ban raha hai...")
                        audio_out = os.path.join(temp_dir, "copyright_free_song.mp3")
                        cmd_ffmpeg = [
                            "ffmpeg", "-y",
                            "-i", input_path,
                            "-vn",
                            "-af", af,
                            "-c:a", "libmp3lame",
                            "-b:a", "192k",
                            audio_out
                        ]
                        ff_res = run_cmd(cmd_ffmpeg, capture_output=True, text=True)
                        if ff_res.returncode != 0:
                            raise RuntimeError(f"Audio error: {ff_res.stderr[-300:]}")

                        st.session_state.generated_audio_song = Path(audio_out).read_bytes()
                        status.update(label="🎉 Audio Song Taiyar!", state="complete", expanded=False)

                    # CASE 2: Full Video or Video Song (.mp4)
                    elif is_full_or_vsong:
                        status.write(f"🎞️ Step 2/2: Video ({quality_mode}) render ho rahi hai...")
                        final_out = os.path.join(temp_dir, "copyright_free_video.mp4")

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
                            "-i", input_path,
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
                        ff_res = run_cmd(cmd_ffmpeg, capture_output=True, text=True)
                        if ff_res.returncode != 0:
                            raise RuntimeError(f"FFmpeg error: {ff_res.stderr[-300:]}")

                        st.session_state.generated_full_video = Path(final_out).read_bytes()
                        status.update(label="🎉 Video Taiyar!", state="complete", expanded=False)

                    # CASE 3: Trending Shorts / Reels (Vertical 9:16 Clips)
                    else:
                        total_dur = get_media_duration(input_path)
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
                                "-i", input_path,
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
                            ff_res = run_cmd(cmd_ffmpeg, capture_output=True, text=True)
                            if ff_res.returncode != 0:
                                raise RuntimeError(f"FFmpeg error on Clip #{idx+1}: {ff_res.stderr[-300:]}")
                            rendered_clips.append((idx + 1, int(ss), Path(clip_out).read_bytes()))

                        st.session_state.generated_clips = rendered_clips

                        if len(rendered_clips) > 1:
                            zip_buffer = io.BytesIO()
                            with zipfile.ZipFile(zip_buffer, "w", zip_deflated) as zf:
                                for c_idx, _, c_bytes in rendered_clips:
                                    zf.writestr(f"viral_short_{c_idx}.mp4", c_bytes)
                            st.session_state.zip_bytes = zip_buffer.getvalue()

                        status.update(label=f"🎉 {len(rendered_clips)} Shorts Taiyar!", state="complete", expanded=False)

                except Exception as e:
                    status.update(label="❌ Error aaya", state="error")
                    st.error(f"Process ruk gaya: {str(e)}")

# =====================================================================
# Persistent Output Display (Stays visible across Download button clicks!)
# =====================================================================
if st.session_state.generated_audio_song:
    st.success("Aapka Copyright-Free Audio Song (.mp3) taiyar hai!")
    st_audio(st.session_state.generated_audio_song, format="audio/mp3")
    st_download(
        label="⬇️ Download Audio Song (.mp3)",
        data=st.session_state.generated_audio_song,
        file_name="copyright_free_song.mp3",
        mime="audio/mpeg",
        key="dl_audio_persistent"
    )

if st.session_state.generated_full_video:
    st.success("Aapki Copyright-Protected Video taiyar hai!")
    st_download(
        label="⬇️ Download Video (.mp4)",
        data=st.session_state.generated_full_video,
        file_name="copyright_free_video.mp4",
        mime="video/mp4",
        key="dl_full_
