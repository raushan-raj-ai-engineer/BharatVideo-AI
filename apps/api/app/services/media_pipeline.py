from __future__ import annotations

import math
import re
import subprocess
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw, ImageFont

from app.core.config import get_settings
from app.services.engine_bridge import EngineBridgeClient
from app.services.storage import LocalStorage


def _safe_text(value: str) -> str:
    value = re.sub(r"\s+", " ", value or "").strip()
    return value[:1200]


def _font(size: int):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for item in candidates:
        if Path(item).is_file():
            return ImageFont.truetype(item, size=size)
    return ImageFont.load_default()


def _wrap(draw: ImageDraw.ImageDraw, text: str, font, max_width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        box = draw.textbbox((0, 0), candidate, font=font)
        if current and box[2] - box[0] > max_width:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines[:8]


def generate_mock_image(*, project_id: str, scene_id: str, order_index: int, prompt: str, aspect_ratio: str) -> tuple[str, dict]:
    storage = LocalStorage()
    if aspect_ratio == "16:9":
        width, height = 1280, 720
    else:
        width, height = 720, 1280
    image = Image.new("RGB", (width, height), (24, 27, 36))
    draw = ImageDraw.Draw(image)
    title_font = _font(max(30, width // 18))
    body_font = _font(max(22, width // 28))
    small_font = _font(max(16, width // 42))
    margin = int(width * 0.08)
    draw.rounded_rectangle((margin, margin, width-margin, height-margin), radius=28, fill=(244, 244, 239), outline=(210, 210, 205), width=3)
    draw.text((margin*1.35, margin*1.35), f"BHARATVIDEO AI  •  SCENE {order_index + 1}", font=small_font, fill=(60,60,65))
    y = margin*2.25
    lines = _wrap(draw, _safe_text(prompt), body_font, width - int(margin*2.8))
    for line in lines:
        draw.text((margin*1.35, y), line, font=body_font, fill=(20,20,24))
        y += body_font.size * 1.45
    draw.text((margin*1.35, height-margin*1.8), "Local mock visual • replace with Veo/Runway later", font=small_font, fill=(95,95,100))
    temp = Path(storage.absolute_path(f"projects/{project_id}/media/{scene_id}/visual.png"))
    temp.parent.mkdir(parents=True, exist_ok=True)
    image.save(temp, format="PNG")
    return storage.public_url_for(temp), {"width": width, "height": height, "provider": "mock"}


def generate_image(*, project_id: str, scene_id: str, order_index: int, prompt: str, aspect_ratio: str) -> tuple[str, dict]:
    settings = get_settings()
    provider = settings.image_provider.lower()
    if provider == "mock":
        return generate_mock_image(
            project_id=project_id, scene_id=scene_id, order_index=order_index,
            prompt=prompt, aspect_ratio=aspect_ratio,
        )
    raise RuntimeError(f"IMAGE_PROVIDER={provider!r} is not enabled in v0.3. Use mock until an external provider is configured.")


def generate_voice(*, project_id: str, scene_id: str, text: str, voice: str, rate: int) -> tuple[str, dict]:
    settings = get_settings()
    storage = LocalStorage()
    target_rel = f"projects/{project_id}/media/{scene_id}/voice.wav"
    if settings.tts_provider == "mock":
        out = Path(storage.absolute_path(target_rel))
        out.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run([
            settings.ffmpeg_binary, "-y", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
            "-t", "1.0", str(out),
        ], check=True, capture_output=True)
        return storage.public_url_for(out), {"provider": "mock", "voice": "silence"}

    bridge = EngineBridgeClient()
    result = bridge.tts(text=_safe_text(text), voice=voice, rate=rate)
    asset_id = str(result["asset_id"])
    data = bridge.download_asset(asset_id)
    url = storage.write_bytes_asset(target_rel, data)
    return url, {"provider": result.get("backend", "host_tts"), "voice": voice, "rate": rate, "bridge_asset_id": asset_id}


def _srt_ts(seconds: float) -> str:
    ms = max(0, int(round(seconds * 1000)))
    h, rem = divmod(ms, 3600000)
    m, rem = divmod(rem, 60000)
    s, ms = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def generate_scene_srt(*, project_id: str, scene_id: str, dialogue: str, duration_seconds: float) -> tuple[str, dict]:
    storage = LocalStorage()
    text = _safe_text(dialogue) or " "
    parts = [x.strip() for x in re.split(r"(?<=[.!?।])\s+|\n+", text) if x.strip()]
    if not parts:
        parts = [text]
    step = max(0.8, duration_seconds / len(parts))
    rows = []
    for idx, part in enumerate(parts, start=1):
        start = min(duration_seconds, (idx - 1) * step)
        end = min(duration_seconds, idx * step)
        rows += [str(idx), f"{_srt_ts(start)} --> {_srt_ts(max(start+0.5,end))}", part, ""]
    url = storage.write_text_asset(f"projects/{project_id}/media/{scene_id}/captions.srt", "\n".join(rows))
    return url, {"segments": len(parts)}


def _path_from_public(url: str) -> Path:
    storage = LocalStorage()
    return storage.path_from_public_url(url).resolve()


def compose_scene_video(*, project_id: str, scene_id: str, image_url: str, voice_url: str, duration_seconds: float, resolution: str) -> tuple[str, dict]:
    settings = get_settings()
    storage = LocalStorage()
    image_path = _path_from_public(image_url)
    voice_path = _path_from_public(voice_url)
    width, height = [int(x) for x in resolution.split("x", 1)]
    out = Path(storage.absolute_path(f"projects/{project_id}/media/{scene_id}/scene.mp4"))
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        settings.ffmpeg_binary, "-y", "-loop", "1", "-i", str(image_path), "-i", str(voice_path),
        "-vf", f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2",
        "-t", f"{max(1.0,duration_seconds):.3f}", "-r", "24", "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-af", "apad", "-c:a", "aac", "-ar", "48000", "-movflags", "+faststart", str(out),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg scene compose failed: {proc.stderr[-2000:]}")
    return storage.public_url_for(out), {"resolution": resolution, "duration_seconds": duration_seconds, "provider": "ffmpeg"}


def compose_project_video(*, project_id: str, scene_video_urls: Iterable[str], subtitle_url: str | None = None, burn_subtitles: bool = True) -> tuple[str, dict]:
    settings = get_settings()
    storage = LocalStorage()
    paths = [_path_from_public(x) for x in scene_video_urls]
    if not paths:
        raise RuntimeError("No scene videos are ready")
    work = Path(storage.absolute_path(f"projects/{project_id}/exports"))
    work.mkdir(parents=True, exist_ok=True)
    concat = work / "concat.txt"
    concat.write_text("\n".join([f"file '{p.as_posix()}'" for p in paths]), encoding="utf-8")
    base = work / "final_local_base.mp4"
    cmd = [settings.ffmpeg_binary, "-y", "-f", "concat", "-safe", "0", "-i", str(concat), "-c", "copy", "-movflags", "+faststart", str(base)]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        cmd = [settings.ffmpeg_binary, "-y", "-f", "concat", "-safe", "0", "-i", str(concat), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-ar", "48000", "-movflags", "+faststart", str(base)]
        proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg final compose failed: {proc.stderr[-2500:]}")

    out = work / "final_local_preview.mp4"
    captions_burned = False
    subtitle_error = None
    if burn_subtitles and subtitle_url:
        subtitle_path = _path_from_public(subtitle_url)
        filter_arg = f"subtitles={subtitle_path.as_posix()}:force_style='FontName=Noto Sans Devanagari,FontSize=18,Outline=2,Shadow=1,MarginV=45'"
        burn_cmd = [settings.ffmpeg_binary, "-y", "-i", str(base), "-vf", filter_arg, "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-c:a", "copy", "-movflags", "+faststart", str(out)]
        burn = subprocess.run(burn_cmd, capture_output=True, text=True)
        if burn.returncode == 0:
            captions_burned = True
        else:
            subtitle_error = burn.stderr[-1500:]
    if not captions_burned:
        import shutil
        shutil.copy2(base, out)
    return storage.public_url_for(out), {
        "scene_count": len(paths),
        "provider": "ffmpeg",
        "captions_burned": captions_burned,
        "subtitle_warning": subtitle_error,
    }


def generate_project_srt(*, project_id: str, scenes: Iterable[tuple[str, float]]) -> tuple[str, dict]:
    storage = LocalStorage()
    rows: list[str] = []
    cursor = 0.0
    index = 1
    for dialogue, duration in scenes:
        text = _safe_text(dialogue)
        if not text:
            cursor += duration
            continue
        parts = [x.strip() for x in re.split(r"(?<=[.!?।])\s+|\n+", text) if x.strip()] or [text]
        step = max(0.6, duration / len(parts))
        for local_idx, part in enumerate(parts):
            start = cursor + local_idx * step
            end = min(cursor + duration, start + step)
            rows += [str(index), f"{_srt_ts(start)} --> {_srt_ts(max(start + 0.45, end))}", part, ""]
            index += 1
        cursor += duration
    url = storage.write_text_asset(f"projects/{project_id}/exports/captions.srt", "\n".join(rows))
    return url, {"segments": index - 1, "duration_seconds": cursor}
