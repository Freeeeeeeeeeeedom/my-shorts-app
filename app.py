import io
import os
import subprocess
import tempfile
import zipfile
from pathlib import Path
import streamlit as st

st.set_page_config(
    page_title="AI Video, Shorts & Song Studio",
    page_icon="🎬",
    layout="centered",
)

st_radio = getattr(st, "radio")
st_video = getattr(st, "video")
st_audio = getattr(st, "audio")
st_download = getattr(st, "download_button")
run_cmd = getattr(subprocess, "run")
zip_deflated = getattr(zipfile, "ZIP_DEFLATED")

defaults = [
    ("clips", []),
    ("full_vid", None),
    ("audio_mp3", None),
    ("zip_data", None),
]
for k, v in defaults:
    if k not in st.session_state:
        st.session_state[k] = v

st.title("🎬 AI Video, Shorts & Song Studio")
st.caption(
    "Phone se video ya song upload karke Copyright-Free "
    "Shorts, Full Video ya Audio Song (.mp3) banayein."
)

uploaded_file = st.file_uploader(
    "📁 Video ya Audio Song select karein:",
    type=["mp4", "mov", "mkv", "mp3", "wav", "m4a"],
)

output_type = st_radio(
    "⚙️ Aapko Kya Banana Hai?",
    [
        "🔥 Trending Shorts / Reels (Vertical 9:16 Clips)",
        "🎥 Full Video Copyright-Free (Poori Video)",
        "🎶 Copyright-Free Video Song (.mp4)",
        "🎧 Copyright-Free Audio Song (.mp3)",
    ],
    index=0,
)

is_audio = output_type == "🎧 Copyright-Free Audio Song (.mp3)"
is_shorts = "Trending Shorts" in output_type
is_full = (
    "Full Video" in output_type
    or "Video Song" in output_type
)

quality = "Fast Turbo (720p)"
if not is_audio:
    quality = st.selectbox(
        "Video Quality",
        ["High Quality (1080p HD)", "Fast Turbo (720p)"],
        index=0 if is_shorts else 1,
    )
preset = "veryfast" if "1080p" in quality else "ultrafast"
crf = "21" if "1080p" in quality else "25"

num_clips, clip_dur, timing_mode, start_str = 1, 30, "Auto", "00:15"
if is_shorts:
    c1, c2 = st.columns(2)
    num_clips = c1.slider("Kitni Clips chahiye?", 1, 5, 3)
    clip_dur = c2.slider("Clip Duration (Sec)", 15, 60, 30, 5)
    timing_mode = st_radio(
        "Clips kahan se cut karein?",
        ["Auto", "Exact Time (MM:SS)"],
        horizontal=True,
    )
    if timing_mode == "Exact Time (MM:SS)":
        start_str = st.text_input("Start Time (MM:SS):", value="00:15")
        num_clips = 1

hook_txt, wm_txt = "", ""
if not is_audio:
    st.markdown("### ✍️ Viral Hook & Watermark")
    hooks = [
        "None",
        "WAIT FOR THE END!",
        "WATCH TILL THE END",
        "99% PEOPLE MISS THIS",
        "Custom...",
    ]
    sel_hook = st.selectbox(
        "Viral Hook:", hooks, index=1 if is_shorts else 0
    )
    if sel_hook == "Custom...":
        hook_txt = st.text_input("Custom Hook likhein:")
    elif sel_hook != "None":
        hook_txt = sel_hook
    wm_txt = st.text_input(
        "Channel Watermark (Optional):", placeholder="e.g. @RoKoClips"
    )

st.markdown("### 🛡️ Anti-Copyright Shield")
if is_audio:
    audio_shield = st.checkbox(
        "🎵 Audio Shield (Pitch +3% & Tempo)", value=True
    )
    video_shield = False
    pro_visual = False
else:
    s1, s2, s3 = st.columns(3)
    video_shield = s1.checkbox("🎬 Color & Speed", value=True)
    pro_visual = s2.checkbox("🪞 Mirror & Zoom", value=True)
    audio_shield = s3.checkbox("🎵 Audio Shield", value=True)


def to_sec(t: str) -> float:
    try:
        p = [float(x) for x in t.strip().split(":")]
        if len(p) == 2:
            return p[0] * 60 + p[1]
        if len(p) == 3:
            return p[0] * 3600 + p[1] * 60 + p[2]
        return max(0.0, p[0])
    except Exception:
        return 0.0


def get_dur(path: str) -> float:
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        path,
    ]
    res = run_cmd(cmd, capture_output=True, text=True)
    try:
        return float(res.stdout.strip())
    except Exception:
        return 120.0


def text_filters(hook: str, wm: str, vert: bool) -> str:
    font = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    fopt = f"fontfile={font}:" if os.path.exists(font) else ""
    out = []
    items = [
        (hook, "54" if vert else "38", "180" if vert else "40", "red@0.85"),
        (wm, "36" if vert else "28", "h-180" if vert else "h-60", "black@0.55"),
    ]
    for txt, fs, yp, bg in items:
        if txt.strip():
            clean = (
                txt.strip()
                .replace("\\", "\\\\")
                .replace(":", "\\:")
                .replace("'", "")
                .replace('"', "")
                .replace("%", "\\%")
            )
            out.append(
                f"drawtext={fopt}text='{clean}':fontcolor=white:"
                f"fontsize={fs}:box=1:boxcolor={bg}:"
                f"boxborderw=14:x=(w-text_w)/2:y={yp}"
            )
    return ",".join(out)
if st.button("🚀 Start Processing", type="primary"):
    if not uploaded_file:
        st.error("⚠️ Pehle koi Video ya Audio file select kijiye!")
    else:
        st.session_state.clips = []
        st.session_state.full_vid = None
        st.session_state.audio_mp3 = None
        st.session_state.zip_data = None

        with st.status("Process ho raha hai...", expanded=True) as status:
            with tempfile.TemporaryDirectory() as tmp:
                try:
                    ext = Path(uploaded_file.name).suffix or ".mp4"
                    in_path = os.path.join(tmp, f"in{ext}")
                    Path(in_path).write_bytes(uploaded_file.getbuffer())

                    af = (
                        "asetrate=44100*1.03,aresample=44100,"
                        "atempo=1.01,volume=1.05"
                        if audio_shield
                        else "volume=1.0"
                    )

                    if is_audio:
                        out_mp3 = os.path.join(tmp, "song.mp3")
                        cmd = [
                            "ffmpeg", "-y", "-i", in_path, "-vn",
                            "-af", af, "-c:a", "libmp3lame",
                            "-b:a", "192k", out_mp3,
                        ]
                        r = run_cmd(cmd, capture_output=True, text=True)
                        if r.returncode != 0:
                            raise RuntimeError(r.stderr[-250:])
                        st.session_state.audio_mp3 = Path(out_mp3).read_bytes()

                    elif is_full:
                        out_mp4 = os.path.join(tmp, "full.mp4")
                        h_res = "1080" if "1080p" in quality else "720"
                        vf = []
                        if pro_visual:
                            vf.append("hflip,crop=iw*0.94:ih*0.94")
                        vf.append(f"scale=-2:{h_res}")
                        if video_shield:
                            vf.append(
                                "eq=contrast=1.05:saturation=1.08,"
                                "setpts=PTS/1.02"
                            )
                        tf = text_filters(hook_txt, wm_txt, False)
                        if tf:
                            vf.append(tf)
                        cmd = [
                            "ffmpeg", "-y", "-i", in_path,
                            "-vf", ",".join(vf), "-af", af,
                            "-c:v", "libx264", "-preset", preset,
                            "-crf", crf, "-c:a", "aac", "-b:a", "192k",
                            "-movflags", "+faststart", out_mp4,
                        ]
                        r = run_cmd(cmd, capture_output=True, text=True)
                        if r.returncode != 0:
                            raise RuntimeError(r.stderr[-250:])
                        st.session_state.full_vid = Path(out_mp4).read_bytes()

                    else:
                        dur = get_dur(in_path)
                        w, h = (
                            (1080, 1920)
                            if "1080p" in quality
                            else (720, 1280)
                        )
                        fg = (
                            ("hflip,crop=iw*0.94:ih*0.94," if pro_visual else "")
                            + f"scale={w}:{h}:force_original_aspect_ratio=decrease"
                        )
                        post = []
                        if video_shield:
                            post.append(
                                "eq=contrast=1.05:saturation=1.08,"
                                "setpts=PTS/1.02"
                            )
                        tf = text_filters(hook_txt, wm_txt, True)
                        if tf:
                            post.append(tf)
                        p_str = ("," + ",".join(post)) if post else ""
                        vf_c = (
                            f"[0:v]scale={w}:{h}:"
                            f"force_original_aspect_ratio=increase,"
                            f"crop={w}:{h},boxblur=20:5[bg];"
                            f"[0:v]{fg}[fg];"
                            f"[bg][fg]overlay=(W-w)/2:(H-h)/2{p_str}[v]"
                        )

                        if timing_mode != "Auto":
                            times = [min(to_sec(start_str), max(0.0, dur - 5))]
                        else:
                            step = max(5.0, (dur - clip_dur) / max(1, num_clips))
                            times = [
                                min(i * step, max(0.0, dur - clip_dur))
                                for i in range(num_clips)
                            ]

                        res_clips = []
                        for i, ss in enumerate(times):
                            c_out = os.path.join(tmp, f"s_{i+1}.mp4")
                            cmd = [
                                "ffmpeg", "-y", "-ss", str(ss),
                                "-t", str(clip_dur), "-i", in_path,
                                "-filter_complex", vf_c,
                                "-map", "[v]", "-map", "0:a?", "-af", af,
                                "-c:v", "libx264", "-preset", preset,
                                "-crf", crf, "-c:a", "aac", "-b:a", "192k",
                                "-movflags", "+faststart", c_out,
                            ]
                            r = run_cmd(cmd, capture_output=True, text=True)
                            if r.returncode != 0:
                                raise RuntimeError(r.stderr[-250:])
                            res_clips.append(
                                (i + 1, int(ss), Path(c_out).read_bytes())
                            )

                        st.session_state.clips = res_clips
                        if len(res_clips) > 1:
                            zb = io.BytesIO()
                            with zipfile.ZipFile(zb, "w", zip_deflated) as zf:
                                for idx, _, b in res_clips:
                                    zf.writestr(f"viral_short_{idx}.mp4", b)
                            st.session_state.zip_data = zb.getvalue()

                    status.update(
                        label="🎉 Taiyar Hai!", state="complete", expanded=False
                    )
                except Exception as e:
                    status.update(label="❌ Error aaya", state="error")
                    st.error(f"Error: {e}")

if st.session_state.audio_mp3:
    st.success("Audio Song (.mp3) taiyar hai!")
    st_audio(st.session_state.audio_mp3, format="audio/mp3")
    st_download(
        "⬇️ Download Audio (.mp3)",
        st.session_state.audio_mp3,
        "copyright_free_song.mp3",
        "audio/mpeg",
        key="dl_mp3",
    )

if st.session_state.full_vid:
    st.success("Video (.mp4) taiyar hai!")
    st_download(
        "⬇️ Download Video (.mp4)",
        st.session_state.full_vid,
        "copyright_free_video.mp4",
        "video/mp4",
        key="dl_full",
    )
    st_video(st.session_state.full_vid)

if st.session_state.clips:
    clips_list = st.session_state.clips
    st.subheader(f"🔥 Aapke {len(clips_list)} Viral Shorts")
    if st.session_state.zip_data:
        zip_label = f"📦 Download All {len(clips_list)} Clips (.zip)"
        st_download(
            zip_label,
            st.session_state.zip_data,
            "all_shorts.zip",
            "application/zip",
            type="primary",
            key="dl_zip",
        )
    for idx, ss, b in clips_list:
        st.markdown(f"#### 🎬 Clip #{idx} ({ss}s)")
        st_video(b)
        st_download(
            f"⬇️ Download Clip #{idx} (.mp4)",
            b,
            f"short_{idx}.mp4",
            "video/mp4",
            key=f"dl_{idx}",
        )

with st.expander("🎼 Free Copyright-Free Songs Websites"):
    st.markdown(
        "- **Pixabay Music**: pixabay.com/music\n"
        "- **NCS**: ncs.io\n"
        "- **YouTube Audio Library**: YouTube Studio"
    )
