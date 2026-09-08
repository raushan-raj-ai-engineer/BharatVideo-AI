from __future__ import annotations

from pathlib import Path
from typing import Any
import contextlib
import json
import math
import os
import re
import shutil
import shlex
import subprocess
import tempfile
import wave

from .plan_adapter import EpisodeSpec, SceneSpec


class AudioGenerationError(RuntimeError):
    pass


def _run(command: list[str], *, input_text: str | None = None) -> None:
    proc = subprocess.run(
        command,
        input=input_text,
        text=input_text is not None,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if proc.returncode:
        raise AudioGenerationError(
            f"Command failed ({proc.returncode}): {' '.join(command)}\n"
            f"{proc.stderr[-3000:]}"
        )


def _wav_duration(path: Path) -> float:
    with contextlib.closing(wave.open(str(path), "rb")) as wav:
        rate = wav.getframerate()
        return wav.getnframes() / float(rate) if rate else 0.0


def _say_voices() -> list[tuple[str, str]]:
    say = shutil.which("say")
    if not say:
        return []
    proc = subprocess.run(
        [say, "-v", "?"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if proc.returncode:
        return []

    voices: list[tuple[str, str]] = []
    for line in proc.stdout.splitlines():
        match = re.match(r"^\s*(\S(?:.*?\S)?)\s{2,}([a-z]{2}_[A-Z]{2})\s+#", line)
        if match:
            voices.append((match.group(1).strip(), match.group(2).strip()))
    return voices


def _choose_say_voice(locale: str) -> str | None:
    voices = _say_voices()
    for name, voice_locale in voices:
        if voice_locale == locale:
            return name
    language = locale.split("_", 1)[0]
    for name, voice_locale in voices:
        if voice_locale.startswith(language + "_"):
            return name
    return None


def _normalize_wav(source: Path, dest: Path, *, sample_rate: int) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise AudioGenerationError("ffmpeg not found")
    _run([
        ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
        "-i", str(source),
        "-ac", "1", "-ar", str(sample_rate),
        "-c:a", "pcm_s16le",
        str(dest),
    ])


def _atempo_chain(speed: float) -> str:
    """Build legal ffmpeg atempo chain for any positive speed."""
    if speed <= 0:
        raise AudioGenerationError(f"Invalid speed factor: {speed}")
    factors: list[float] = []
    remaining = speed
    while remaining > 2.0:
        factors.append(2.0)
        remaining /= 2.0
    while remaining < 0.5:
        factors.append(0.5)
        remaining /= 0.5
    factors.append(remaining)
    return ",".join(f"atempo={f:.6f}" for f in factors)


def _speed_wav(source: Path, dest: Path, speed: float, sample_rate: int) -> None:
    if abs(speed - 1.0) < 0.005:
        shutil.copy2(source, dest)
        return
    _run([
        shutil.which("ffmpeg") or "ffmpeg",
        "-hide_banner", "-loglevel", "error", "-y",
        "-i", str(source),
        "-filter:a", _atempo_chain(speed),
        "-ac", "1", "-ar", str(sample_rate),
        "-c:a", "pcm_s16le",
        str(dest),
    ])


def _generate_with_say(
    text: str,
    dest: Path,
    *,
    locale: str,
    rate: int,
    sample_rate: int,
) -> str:
    say = shutil.which("say")
    if not say:
        raise AudioGenerationError("macOS 'say' command is not available")

    voice = _choose_say_voice(locale)
    with tempfile.TemporaryDirectory(prefix="acf-blender-say-") as td:
        aiff = Path(td) / "speech.aiff"
        command = [say]
        if voice:
            command += ["-v", voice]
        command += ["-r", str(rate), "-o", str(aiff), text]
        _run(command)
        _normalize_wav(aiff, dest, sample_rate=sample_rate)

    return f"macos_say:{voice or 'default'}"



KANPURI_SPEECH_MARKERS = (
    "अरे", "बे", "काहे", "ई", "ऊ", "देखौ", "हमका", "तुमका", "लागत",
    "का भइया", "भौकाल", "जुगाड़", "गुड्डुआ", "बोलिहौ", "कइसे", "अइसे",
    "हम कह रहे", "सुनौ", "बताय", "कहि रहे", "पहिलेइ", "कहत हैं",
    "होइ गवा", "गाँठ बाँध", "चुप्पे", "लगाइये",
)

_KANPURI_CHARACTER_OPENERS = {
    "babuji": (
        "अरे बे", "हम बताय दे रहे हैं", "देखौ भइया", "सुनौ बे",
        "हम कहि रहे हैं", "ई बात गाँठ बाँध ल्यो",
    ),
    "guddu": (
        "अरे बाबूजी", "देखौ बाबूजी", "का भइया", "सुनौ त",
        "हमका त पहिलेइ पता था", "ई देखौ",
    ),
    "bittu": (
        "अरे भइया", "बाबूजी सुनौ", "का बे", "भइया ई देखौ",
        "हम कहत हैं", "अरे ई त गजब होइ गवा",
    ),
    "default": ("अरे भइया", "देखौ", "का बे", "सुनौ त", "हम बताय दे रहे हैं"),
}

# Full sentence-level Kanpuri speech transformations.  V5.1/V5.2 only
# replaced a handful of words, so Lekha still sounded like textbook Hindi.
# V5.3 intentionally rewrites *grammar and cadence* before TTS.
_KANPURI_SENTENCE_PATTERNS = (
    (r"^\s*तुम\s+चुप\s+रहो[.!?।]*$", "जाइ चुप्पे बैठौ, नाहीं त एक चपत लगाइये देंगे।"),
    (r"^\s*चुप\s+रहो[.!?।]*$", "चुप्पे बैठौ बे, बहुत भौकाल मत काटौ।"),
    (r"^\s*तुम\s+क्या\s+कर\s+रहे\s+हो[?!।]*$", "ई का भौकाल काटत हो बे?"),
    (r"^\s*क्या\s+कर\s+रहे\s+हो[?!।]*$", "ई का करत हो बे?"),
    (r"^\s*तुम\s+कहाँ\s+जा\s+रहे\s+हो[?!।]*$", "कहाँ सरकत हो बे?"),
    (r"^\s*कहाँ\s+जा\s+रहे\s+हो[?!।]*$", "कहाँ चले जात हो बे?"),
    (r"^\s*मुझे\s+नहीं\s+पता[.!।]*$", "हमका का मालूम बे।"),
    (r"^\s*मैंने\s+कहा\s+था[.!।]*$", "हम पहिलेइ बताय दिहे रहे।"),
    (r"^\s*मैं\s+बता\s+रहा\s+हूँ[.!।]*$", "हम बताय दे रहे हैं।"),
    (r"^\s*मैं\s+कह\s+रहा\s+हूँ[.!।]*$", "हम कहि रहे हैं, कान खोल के सुनौ।"),
    (r"^\s*मत\s+करो[.!।]*$", "ई नौटंकी बंद करौ बे।"),
    (r"^\s*रुको[.!।]*$", "अरे ठहरौ त जरा।"),
    (r"^\s*देखो[.!।]*$", "ई देखौ भइया।"),
)

_KANPURI_REWRITES = (
    # Pronouns / question words
    ("क्यों", "काहे"), ("क्या", "का"), ("यहाँ", "हियाँ"),
    ("मुझे", "हमका"), ("हमें", "हमका"), ("तुम्हें", "तुमका"),
    # Cadence / verbs
    ("लगता है", "लागत है"), ("लगता", "लागत"),
    ("देखो", "देखौ"), ("सुनो", "सुनौ"),
    ("कैसे", "कइसे"), ("ऐसे", "अइसे"),
    ("कर रहे हो", "करत हो"), ("कर रहे हैं", "करत हैं"),
    ("जा रहे हो", "जात हो"), ("जा रहा है", "जात है"),
    ("आ रहे हो", "आवत हो"), ("आ रहा है", "आवत है"),
    ("बोलोगे", "बोलिहौ"), ("करोगे", "करिहौ"),
    ("जाओ", "जाइ"), ("बैठो", "बैठौ"), ("रहो", "रहौ"),
    ("बताओ", "बतावौ"), ("समझो", "समझौ"),
    ("बन गया", "बन गवा"), ("हो गया", "होइ गवा"),
    ("हो गई", "होइ गई"), ("मिल गया", "मिल गवा"),
    ("नहीं है", "नइ है"), ("नहीं", "नइ"),
    # Common spoken contractions
    ("मेरे को", "हमका"), ("तुम लोग", "तुम सब"),
)

_KANPURI_STRONG_MARKERS = (
    "चपत लगाइये देंगे", "भौकाल", "बताय दे रहे", "बताय दिहे", "पहिलेइ",
    "चुप्पे", "नौटंकी", "कान खोल", "सरकत", "कहि रहे", "होइ गवा",
    "काहे", "का बे", "सुनौ", "देखौ", "हमका", "करत हो", "जात हो",
    "आवत", "करिहौ", "जाइ", "बैठौ", "नइ",
)

_ROMAN_HINDI_TTS = {
    "business": "बिजनेस", "customer": "कस्टमर", "customers": "कस्टमर",
    "offer": "ऑफर", "reel": "रील", "reels": "रील", "camera": "कैमरा",
    "algorithm": "एल्गोरिदम", "startup": "स्टार्टअप", "online": "ऑनलाइन",
    "course": "कोर्स", "founder": "फाउंडर", "public": "पब्लिक",
    "live": "लाइव", "views": "व्यूज़", "view": "व्यू",
    "screenshot": "स्क्रीनशॉट", "phone": "फोन", "comment": "कमेंट",
    "comments": "कमेंट", "part two": "पार्ट टू", "thumbnail": "थम्बनेल",
    "confidence": "कॉन्फिडेंस", "innovation": "इनोवेशन",
    "marketing": "मार्केटिंग", "profit": "प्रॉफिट", "expert": "एक्सपर्ट",
    "industry": "इंडस्ट्री", "experience": "एक्सपीरियंस",
    "practical": "प्रैक्टिकल", "digital": "डिजिटल", "premium": "प्रीमियम",
    "delivery": "डिलीवरी", "address": "एड्रेस", "cashback": "कैशबैक",
    "challenge": "चैलेंज", "smart": "स्मार्ट", "module": "मॉड्यूल",
    "ai": "ए आई", "qr": "क्यू आर", "upi": "यू पी आई",
}

def _episode_wants_kanpuri_voice(episode: EpisodeSpec, config: dict[str, Any]) -> bool:
    voice_cfg = config.get("kanpuri_voice_v51", {})
    if not bool(voice_cfg.get("enabled", False)):
        return False
    needle = str(voice_cfg.get("apply_when_language_name_contains", "kanpuri")).lower()
    name = str(episode.language_name or "").lower()
    genre = str(episode.genre or "").lower()
    return needle in name or "kanpuri" in genre


def _replace_roman_for_hindi_tts(text: str) -> str:
    out = str(text or "")
    # Longer phrases first so "part two" wins before individual words.
    for raw, spoken in sorted(_ROMAN_HINDI_TTS.items(), key=lambda item: len(item[0]), reverse=True):
        pattern = re.compile(rf"(?i)(?<![A-Za-z]){re.escape(raw)}(?![A-Za-z])")
        out = pattern.sub(spoken, out)
    return out


def _regionalize_kanpuri_text(text: str, *, character_id: str, turn_index: int) -> str:
    """Rewrite neutral Hindi into strong, TTS-friendly Kanpuriya speech.

    This is deliberately more than vocabulary substitution: V5.3 changes
    sentence grammar, command endings, reactions and cadence.  The source plan
    remains unchanged for subtitles/auditing; only the spoken TTS text changes.
    """
    original = _replace_roman_for_hindi_tts(str(text or "").strip())
    out = original

    # 1) Whole-line idioms first. These create genuinely regional sentence form.
    for pattern, replacement in _KANPURI_SENTENCE_PATTERNS:
        if re.match(pattern, out, flags=re.IGNORECASE):
            out = re.sub(pattern, replacement, out, flags=re.IGNORECASE)
            break

    # 2) Phrase/verb morphology conversion for general lines.
    for formal, regional in _KANPURI_REWRITES:
        out = out.replace(formal, regional)
    out = re.sub(r"(?<!\S)यह(?=\s|$)", "ई", out)
    out = re.sub(r"(?<!\S)ये(?=\s|$)", "ई", out)
    out = re.sub(r"(?<!\S)वह(?=\s|$)", "ऊ", out)
    out = re.sub(r"\s+", " ", out).strip()

    # 3) Character cadence.  Neutral-ish lines get a regional framing clause,
    # not merely a token marker. Deterministic selection keeps reruns stable.
    strong = any(marker in out for marker in _KANPURI_STRONG_MARKERS)
    if out and not strong:
        full_pool = _KANPURI_CHARACTER_OPENERS.get(character_id, _KANPURI_CHARACTER_OPENERS["default"])
        # Keep the original three character openers as the stable front-door so
        # older story tests/subtitle expectations remain valid; the *rest* of
        # the sentence is strengthened below.
        pool = full_pool[:3] if len(full_pool) >= 3 else full_pool
        checksum = sum(ord(ch) for ch in out) + int(turn_index or 0) * 17
        opener = pool[checksum % len(pool)]
        out = f"{opener}, {out}"
        if not any(marker in out for marker in ("भौकाल", "बताय", "पहिलेइ", "चुप्पे", "होइ गवा", "करत हो", "जात हो")):
            out = out.rstrip(".!।?") + ", ठीक से सुनौ अउर समझ ल्यो।"

    # 4) Punchier endings for commands/questions that still sound too formal.
    if out:
        if out.endswith("?") and not any(x in out for x in ("बे?", "भइया?", "बाबूजी?")):
            out = out[:-1].rstrip(" ।") + " बे?"
        elif re.search(r"(?:करौ|जाइ|बैठौ|रहौ|बतावौ|समझौ)[.!।]*$", out):
            out = out.rstrip(".!।") + " बे।"

    # 5) Never let a generic Hindi sentence reach TTS in strong mode.
    if out and not any(marker in out for marker in _KANPURI_STRONG_MARKERS):
        out = f"हम बताय दे रहे हैं, {out}"
    return out


def _spoken_dialect_ratio(texts: list[str]) -> float:
    spoken = [str(text).strip() for text in texts if str(text).strip()]
    if not spoken:
        return 1.0
    hit = sum(1 for text in spoken if any(marker in text for marker in _KANPURI_STRONG_MARKERS))
    return hit / len(spoken)


def _spoken_strong_dialect_ratio(texts: list[str]) -> float:
    return _spoken_dialect_ratio(texts)


_KANPURI_COMPACT_REWRITES = (
    ("हम बताय दे रहे हैं, ", "बताय दे रहे हैं, "),
    ("हम कहि रहे हैं, कान खोल के सुनौ, ", "सुनौ, "),
    ("हम कहि रहे हैं, ", "कहि रहे हैं, "),
    ("ई बात गाँठ बाँध ल्यो, ", "गाँठ बाँध ल्यो, "),
    ("हमका त पहिलेइ पता था, ", "पहिलेइ पता था, "),
    ("भइया ई देखौ, ", "ई देखौ, "),
    ("देखौ भइया, ", "देखौ, "),
    ("अरे भइया, ", "भइया, "),
    ("अरे बाबूजी, ", "बाबूजी, "),
    (", ठीक से सुनौ अउर समझ ल्यो", ", समझ ल्यो"),
    (", कान खोल के सुनौ", ", सुनौ"),
    ("बहुत भौकाल मत काटौ", "भौकाल मत काटौ"),
)


def _compact_kanpuri_spoken_text(text: str, level: int = 1) -> str:
    """Shorten an over-dense Kanpuri line without making the voice robotic.

    The compactor removes generated padding first and preserves regional punch
    markers. Higher levels are only used when the same complete dialogue turn
    still cannot fit at the configured natural-speed cap.
    """
    out = re.sub(r"\s+", " ", str(text or "").strip())
    if not out:
        return out

    for raw, compact in _KANPURI_COMPACT_REWRITES:
        out = out.replace(raw, compact)

    if level >= 2:
        level2 = (
            ("हम पहिलेइ बताय दिहे रहे", "पहिलेइ बताय दिहे रहे"),
            ("जाइ चुप्पे बैठौ, नाहीं त एक चपत लगाइये देंगे",
             "चुप्पे बैठौ, नाहीं त चपत लगाइये देंगे"),
            ("ई का भौकाल काटत हो बे", "का भौकाल काटत हो बे"),
            ("अरे ठहरौ त जरा", "ठहरौ जरा"),
            ("ई देखौ भइया", "ई देखौ"),
            ("हमका का मालूम बे", "हमका नइ मालूम बे"),
        )
        for raw, compact in level2:
            out = out.replace(raw, compact)

        # Generated regionalizers sometimes create two framing clauses before
        # the actual joke. Keep at most one lightweight opener.
        out = re.sub(
            r"^(?:अरे बे|सुनौ बे|का बे|भइया|देखौ|बाबूजी)\s*,\s*"
            r"(?:बताय दे रहे हैं|कहि रहे हैं|सुनौ)\s*,\s*",
            lambda m: m.group(0).split(",", 1)[0] + ", ",
            out,
        )

    if level >= 3:
        # Last-resort semantic compaction: discard only known filler clauses,
        # never arbitrary middle words. This keeps setup/payoff intelligible.
        clauses = [c.strip() for c in re.split(r"[,;]+", out) if c.strip()]
        filler = (
            "समझ ल्यो", "ठीक से सुनौ", "कान खोल के सुनौ",
            "हम बताय दे रहे हैं", "हम कहि रहे हैं",
        )
        kept = [c for c in clauses if not any(c == f for f in filler)]
        if kept:
            out = ", ".join(kept)
            if text.rstrip().endswith("?") and not out.endswith("?"):
                out = out.rstrip("।.!?") + "?"
            elif text.rstrip().endswith(("।", ".", "!")) and not out.endswith(("।", ".", "!")):
                out = out.rstrip("।.!?") + "।"

    out = re.sub(r"\s+", " ", out).strip(" ,")
    if out and not any(marker in out for marker in _KANPURI_STRONG_MARKERS):
        out = "सुनौ, " + out
    return out


def _generate_with_custom_kanpuri_tts(
    text: str,
    dest: Path,
    *,
    character_id: str,
    sample_rate: int,
) -> str:
    """Optional hook for a real regional/voice-cloned TTS backend.

    CONTENT_FACTORY_KANPURI_TTS_CMD may contain placeholders:
    {text_file}, {output}, {character}, {reference_wav}.
    The command must create a WAV file at {output}. This lets the project use a
    licensed Kanpuriya regional voice without hard-coding a cloud vendor.
    """
    template = os.getenv("CONTENT_FACTORY_KANPURI_TTS_CMD", "").strip()
    if not template:
        return ""
    reference = os.getenv("CONTENT_FACTORY_KANPURI_REFERENCE_WAV", "").strip()
    with tempfile.TemporaryDirectory(prefix="acf-kanpuri-tts-") as td:
        td_path = Path(td)
        text_file = td_path / "speech.txt"
        raw_out = td_path / "speech.wav"
        text_file.write_text(text, encoding="utf-8")
        command = template.format(
            text_file=str(text_file),
            output=str(raw_out),
            character=character_id,
            reference_wav=reference,
        )
        proc = subprocess.run(
            shlex.split(command),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if proc.returncode or not raw_out.exists():
            raise AudioGenerationError(
                "Kanpuri custom TTS failed: " + (proc.stderr[-2000:] or command)
            )
        _normalize_wav(raw_out, dest, sample_rate=sample_rate)
    return "kanpuri_custom_tts"


def _piper_candidate_model(
    project_root: Path,
    language_code: str,
) -> tuple[Path, Path] | None:
    explicit = os.getenv("CONTENT_FACTORY_BLENDER_PIPER_MODEL", "").strip()
    if explicit:
        model = Path(explicit).expanduser()
        config = Path(str(model) + ".json")
        if model.exists() and config.exists():
            return model, config

    if language_code != "english":
        return None

    model = project_root / "models/piper/en_US-lessac-medium.onnx"
    config = project_root / "models/piper/en_US-lessac-medium.onnx.json"
    if model.exists() and config.exists():
        return model, config
    return None


def _generate_with_piper(
    text: str,
    dest: Path,
    *,
    model: Path,
    config: Path,
    sample_rate: int,
) -> str:
    try:
        from piper import PiperVoice
    except Exception as exc:
        raise AudioGenerationError(f"Piper Python package unavailable: {exc}") from exc

    with tempfile.TemporaryDirectory(prefix="acf-blender-piper-") as td:
        raw = Path(td) / "raw.wav"
        voice = PiperVoice.load(model, config_path=config)
        with wave.open(str(raw), "wb") as wav_file:
            voice.synthesize_wav(text, wav_file)
        _normalize_wav(raw, dest, sample_rate=sample_rate)
    return f"piper:{model.stem}"


def _write_silence(path: Path, seconds: float, sample_rate: int) -> None:
    frames = max(1, int(round(seconds * sample_rate)))
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(b"\x00\x00" * frames)



def _ambient_pattern(sample_rate: int) -> bytes:
    """One second of very low-level deterministic room tone (-~46 dBFS)."""
    frames = max(1, int(sample_rate))
    data = bytearray(frames * 2)
    # Two gentle hum components plus tiny deterministic pseudo-noise.
    state = 0x13579BDF
    import struct
    for i in range(frames):
        state = (1103515245 * state + 12345) & 0x7FFFFFFF
        noise = (((state >> 12) & 0xFF) - 128) * 0.35
        hum = 110.0 * math.sin(2.0 * math.pi * 67.0 * i / sample_rate)
        hum += 55.0 * math.sin(2.0 * math.pi * 113.0 * i / sample_rate)
        sample = int(max(-32768, min(32767, hum + noise)))
        struct.pack_into("<h", data, i * 2, sample)
    return bytes(data)


def _write_ambient_bed(path: Path, seconds: float, sample_rate: int) -> None:
    frames = max(1, int(round(seconds * sample_rate)))
    pattern = _ambient_pattern(sample_rate)
    pattern_frames = max(1, sample_rate)
    whole, remain = divmod(frames, pattern_frames)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        for _ in range(whole):
            wav.writeframes(pattern)
        if remain:
            wav.writeframes(pattern[:remain * 2])


def _turn_priority(item: dict[str, Any], position: int, total: int) -> float:
    """Score a raw dialogue turn for keeping in a duration-constrained scene.

    The render adapter preserves story shape rather than chopping audio:
    - first setup turn
    - final payoff/reaction
    - short concrete middle exchanges
    - emotional/punch turns
    """
    turn = item["turn"]
    text = str(turn.text or "").strip()
    emotion = str(turn.emotion or "").lower()
    pose = str(turn.pose or "").lower()
    duration = max(0.1, float(item["raw_duration"]))

    score = 0.0
    if position == 0:
        score += 100.0
    if position == total - 1:
        score += 95.0

    # Ending-adjacent turn often carries setup for the punch.
    if position == total - 2:
        score += 18.0

    if emotion in {"laughing", "shocked", "angry", "smirk", "proud", "excited"}:
        score += 14.0
    if pose in {"pointing", "shocked", "give", "show", "thinking"}:
        score += 6.0

    # Prefer concise, concrete spoken lines under a fixed time budget.
    score += max(0.0, 18.0 - duration * 2.2)

    # Hindi punctuation / punch markers.
    if any(token in text for token in ("!", "?", "अरे", "लेकिन", "अब ", "तो ")):
        score += 5.0

    return score


def _selected_totals(
    items: list[dict[str, Any]],
    indices: list[int],
    pauses: list[float],
) -> tuple[float, float, float]:
    speech = sum(float(items[i]["raw_duration"]) for i in indices)
    pause = sum(float(pauses[i]) for i in indices)
    return speech, pause, speech + pause


def _playable_seconds_at_cap(
    items: list[dict[str, Any]],
    indices: list[int],
    pauses: list[float],
    *,
    max_speedup: float,
) -> float:
    """Wall-clock seconds required if speech uses the natural speed-up cap.

    Pauses are NOT speed-compressed by ffmpeg atempo. V2.4 incorrectly treated
    speech+pause as if both were compressible, which produced edge failures such
    as required_speedup=1.16x after a selector had accepted the turns for a
    1.15x cap.
    """
    speech, pause, _ = _selected_totals(items, indices, pauses)
    return (speech / max(1.0, max_speedup)) + pause


def _fits_naturally(
    items: list[dict[str, Any]],
    indices: list[int],
    pauses: list[float],
    *,
    budget: float,
    max_speedup: float,
    safety: float,
) -> bool:
    return _playable_seconds_at_cap(
        items,
        indices,
        pauses,
        max_speedup=max_speedup,
    ) <= max(0.5, budget - safety) + 1e-6


def _compact_selected_pauses(
    items: list[dict[str, Any]],
    indices: list[int],
    pauses: list[float],
    *,
    budget: float,
    max_speedup: float,
    safety: float,
    compact_floor: float,
) -> list[float]:
    """Tighten pauses before sacrificing a complete spoken turn.

    Speech remains at or below max_speedup. Only inter-turn pauses are reduced,
    and never below compact_floor.
    """
    selected_pauses = [float(pauses[i]) for i in indices]
    speech = sum(float(items[i]["raw_duration"]) for i in indices)
    allowed_pause = max(0.0, budget - safety - (speech / max(1.0, max_speedup)))
    current_pause = sum(selected_pauses)

    if current_pause <= allowed_pause + 1e-6:
        return selected_pauses

    minimum_total = compact_floor * len(selected_pauses)
    if allowed_pause < minimum_total - 1e-6:
        return selected_pauses

    reducible = sum(max(0.0, p - compact_floor) for p in selected_pauses)
    need_reduce = current_pause - allowed_pause
    if reducible <= 1e-9:
        return selected_pauses

    ratio = min(1.0, need_reduce / reducible)
    compacted = [
        max(compact_floor, p - ((p - compact_floor) * ratio))
        for p in selected_pauses
    ]
    return compacted


def _select_turns_for_budget(
    raw_segments: list[dict[str, Any]],
    pauses: list[float],
    *,
    budget: float,
    max_speedup: float,
    safety: float,
) -> tuple[list[int], dict[str, Any]]:
    """Select complete dialogue turns using correct wall-clock fit math.

    Speech may be compressed only up to max_speedup; pauses stay real-time.
    """
    total = len(raw_segments)
    all_indices = list(range(total))
    speech_all, pause_all, raw_total = _selected_totals(
        raw_segments,
        all_indices,
        pauses,
    )

    if _fits_naturally(
        raw_segments,
        all_indices,
        pauses,
        budget=budget,
        max_speedup=max_speedup,
        safety=safety,
    ):
        return all_indices, {
            "mode": "all_turns",
            "original_turns": total,
            "kept_turns": total,
            "dropped_turns": 0,
            "original_seconds": round(raw_total, 4),
            "original_speech_seconds": round(speech_all, 4),
            "original_pause_seconds": round(pause_all, 4),
        }

    selected: list[int] = []
    for i in (0, total - 1):
        if i not in selected:
            selected.append(i)

    # If setup + payoff cannot fit together, retain payoff and pair it with
    # the shortest viable earlier setup/reaction line.
    if not _fits_naturally(
        raw_segments,
        selected,
        pauses,
        budget=budget,
        max_speedup=max_speedup,
        safety=safety,
    ):
        last = total - 1
        candidates = list(range(0, max(1, total - 1)))
        shortest = min(
            candidates,
            key=lambda i: float(raw_segments[i]["raw_duration"]),
        )
        selected = sorted(set([shortest, last]))

    middle = [i for i in range(1, max(1, total - 1)) if i not in selected]
    middle.sort(
        key=lambda i: _turn_priority(raw_segments[i], i, total),
        reverse=True,
    )

    for i in middle:
        trial = sorted(selected + [i])
        if _fits_naturally(
            raw_segments,
            trial,
            pauses,
            budget=budget,
            max_speedup=max_speedup,
            safety=safety,
        ):
            selected = trial

    if len(selected) < 3 and total >= 3:
        remaining = [i for i in range(total) if i not in selected]
        remaining.sort(key=lambda i: float(raw_segments[i]["raw_duration"]))
        for i in remaining:
            trial = sorted(selected + [i])
            if _fits_naturally(
                raw_segments,
                trial,
                pauses,
                budget=budget,
                max_speedup=max_speedup,
                safety=safety,
            ):
                selected = trial
                break

    selected = sorted(set(selected))
    if not selected:
        selected = [min(
            range(total),
            key=lambda i: float(raw_segments[i]["raw_duration"]),
        )]

    speech_selected, pause_selected, selected_raw = _selected_totals(
        raw_segments,
        selected,
        pauses,
    )
    playable_at_cap = _playable_seconds_at_cap(
        raw_segments,
        selected,
        pauses,
        max_speedup=max_speedup,
    )

    return selected, {
        "mode": "essential_turn_selection",
        "original_turns": total,
        "kept_turns": len(selected),
        "dropped_turns": total - len(selected),
        "original_seconds": round(raw_total, 4),
        "selected_raw_seconds": round(selected_raw, 4),
        "selected_speech_seconds": round(speech_selected, 4),
        "selected_pause_seconds": round(pause_selected, 4),
        "playable_seconds_at_natural_cap": round(playable_at_cap, 4),
        "selected_turn_indices": [raw_segments[i]["turn"].index for i in selected],
        "dropped_turn_indices": [
            raw_segments[i]["turn"].index
            for i in range(total)
            if i not in selected
        ],
    }


def generate_scene_audio(
    episode: EpisodeSpec,
    scene: SceneSpec,
    *,
    project_root: Path,
    scene_output_dir: Path,
    config: dict[str, Any],
) -> dict[str, Any]:
    """Generate one scene audio track that is guaranteed to fit its shot budget.

    If raw dialogue is longer than the scene budget, speech segments are
    deterministically time-compressed with ffmpeg atempo and the animation
    timeline is rebuilt from the reconciled audio durations.
    """
    audio_cfg = config.get("audio", {})
    duration_cfg = config.get("duration", {})
    sample_rate = int(audio_cfg.get("sample_rate", 24000))
    backend = str(audio_cfg.get("backend", "auto")).lower()
    rates = audio_cfg.get("character_rate", {})
    locale = str(
        audio_cfg.get("locale_by_language", {}).get(
            episode.language_code,
            "hi_IN",
        )
    )
    max_speedup = float(duration_cfg.get("max_scene_speedup", 2.75))
    min_pause = float(duration_cfg.get("minimum_pause_seconds", 0.06))
    max_pause = float(duration_cfg.get("maximum_pause_seconds", 0.18))
    safety = float(duration_cfg.get("target_safety_seconds", 0.08))
    ambient_enabled = bool(
        config.get("audio_mastering", {}).get("ambient_bed_in_pauses", True)
    )

    audio_dir = scene_output_dir / "audio"
    raw_dir = audio_dir / "raw"
    final_dir = audio_dir / "segments"
    raw_dir.mkdir(parents=True, exist_ok=True)
    final_dir.mkdir(parents=True, exist_ok=True)

    budget = max(2.0, float(scene.shot_duration_seconds))
    piper_model = _piper_candidate_model(project_root, episode.language_code)

    raw_segments: list[dict[str, Any]] = []
    backends_used: list[str] = []
    spoken_texts: list[str] = []
    kanpuri_voice = _episode_wants_kanpuri_voice(episode, config)
    voice_cfg = config.get("kanpuri_voice_v51", {})

    for turn in scene.dialogue:
        raw_path = raw_dir / f"turn_{turn.index:02d}_{turn.character_id}.wav"
        rate = int(rates.get(turn.character_id, rates.get("default", 175)))
        spoken_text = (
            _regionalize_kanpuri_text(
                turn.text, character_id=turn.character_id, turn_index=turn.index
            )
            if kanpuri_voice and bool(voice_cfg.get("regionalize_before_tts", True))
            else turn.text
        )
        spoken_texts.append(spoken_text)

        used = ""
        if kanpuri_voice:
            used = _generate_with_custom_kanpuri_tts(
                spoken_text, raw_path,
                character_id=turn.character_id, sample_rate=sample_rate,
            )

        if not used and backend in {"auto", "piper"} and piper_model:
            try:
                used = _generate_with_piper(
                    spoken_text,
                    raw_path,
                    model=piper_model[0],
                    config=piper_model[1],
                    sample_rate=sample_rate,
                )
            except Exception:
                if backend == "piper":
                    raise

        if not used:
            used = _generate_with_say(
                spoken_text,
                raw_path,
                locale=locale,
                rate=rate,
                sample_rate=sample_rate,
            )

        if used not in backends_used:
            backends_used.append(used)

        raw_segments.append({
            "turn": turn,
            "spoken_text": spoken_text,
            "raw_path": raw_path,
            "raw_duration": _wav_duration(raw_path),
        })

    if kanpuri_voice and raw_segments:
        ratio = _spoken_dialect_ratio(spoken_texts)
        minimum = float(voice_cfg.get("minimum_spoken_marker_ratio", 0.85))
        if ratio + 1e-9 < minimum:
            raise AudioGenerationError(
                f"[KANPURI VOICE QA] scene={scene.id} spoken_marker_ratio={ratio:.3f} "
                f"< required={minimum:.3f}"
            )
        print(
            f"[KANPURI VOICE V5.3 STRONG] scene={scene.id} "
            f"spoken_marker_ratio={ratio:.2f} backend={backends_used or ['pending']}"
        )

    if not raw_segments:
        master = audio_dir / "scene_audio.wav"
        ambient_enabled = bool(
            config.get("audio_mastering", {}).get("ambient_bed_in_pauses", True)
        )
        if ambient_enabled:
            _write_ambient_bed(master, budget, sample_rate)
        else:
            _write_silence(master, budget, sample_rate)
        payload = {
            "scene_id": scene.id,
            "budget_seconds": budget,
            "raw_duration_seconds": 0.0,
            "duration_seconds": budget,
            "speedup": 1.0,
            "master_audio": str(master),
            "turns": [],
            "backends_used": [],
            "dialogue_budget": {
                "mode": "no_dialogue",
                "original_turns": 0,
                "kept_turns": 0,
                "dropped_turns": 0,
            },
        }
        (audio_dir / "timeline.json").write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return payload

    pauses_all = [
        min(max_pause, max(min_pause, float(x["turn"].pause_after_seconds)))
        for x in raw_segments
    ]

    selected_indices, dialogue_budget = _select_turns_for_budget(
        raw_segments,
        pauses_all,
        budget=budget,
        max_speedup=max_speedup,
        safety=safety,
    )
    selected_segments = [raw_segments[i] for i in selected_indices]

    compact_floor = float(
        duration_cfg.get("compact_pause_floor_seconds", 0.04)
    )
    pauses = _compact_selected_pauses(
        raw_segments,
        selected_indices,
        pauses_all,
        budget=budget,
        max_speedup=max_speedup,
        safety=safety,
        compact_floor=compact_floor,
    )

    speech_total = sum(float(x["raw_duration"]) for x in selected_segments)
    pause_total = sum(pauses)
    raw_total = speech_total + pause_total

    available_speech = max(0.5, budget - pause_total - safety)
    speedup = max(1.0, speech_total / available_speech)

    # Numerical tolerance is intentionally tiny. Never solve density by
    # silently raising the natural voice cap. In strong Kanpuri mode, first
    # shorten generated filler while preserving complete turns + punchlines.
    repair_levels_used: list[int] = []
    if speedup > max_speedup + 0.003 and kanpuri_voice:
        for compact_level in (1, 2, 3):
            changed = False
            for item in selected_segments:
                before = str(item.get("spoken_text", ""))
                compact = _compact_kanpuri_spoken_text(before, compact_level)
                if not compact or compact == before:
                    continue

                turn = item["turn"]
                compact_path = raw_dir / (
                    f"turn_{turn.index:02d}_{turn.character_id}_compact{compact_level}.wav"
                )
                rate = int(rates.get(turn.character_id, rates.get("default", 175)))
                used = ""
                if kanpuri_voice:
                    used = _generate_with_custom_kanpuri_tts(
                        compact, compact_path,
                        character_id=turn.character_id, sample_rate=sample_rate,
                    )
                if not used and backend in {"auto", "piper"} and piper_model:
                    try:
                        used = _generate_with_piper(
                            compact, compact_path,
                            model=piper_model[0], config=piper_model[1],
                            sample_rate=sample_rate,
                        )
                    except Exception:
                        if backend == "piper":
                            raise
                if not used:
                    used = _generate_with_say(
                        compact, compact_path, locale=locale, rate=rate,
                        sample_rate=sample_rate,
                    )
                if used not in backends_used:
                    backends_used.append(used)
                item["spoken_text"] = compact
                item["raw_path"] = compact_path
                item["raw_duration"] = _wav_duration(compact_path)
                changed = True

            if not changed:
                continue
            repair_levels_used.append(compact_level)
            pauses = _compact_selected_pauses(
                raw_segments, selected_indices, pauses_all,
                budget=budget, max_speedup=max_speedup, safety=safety,
                compact_floor=compact_floor,
            )
            speech_total = sum(float(x["raw_duration"]) for x in selected_segments)
            pause_total = sum(pauses)
            raw_total = speech_total + pause_total
            available_speech = max(0.5, budget - pause_total - safety)
            speedup = max(1.0, speech_total / available_speech)
            print(
                f"[KANPURI DURATION REPAIR V5.4] scene={scene.id} "
                f"level={compact_level} raw={raw_total:.2f}s "
                f"required_speedup={speedup:.3f}x cap={max_speedup:.2f}x"
            )
            if speedup <= max_speedup + 0.003:
                dialogue_budget["mode"] = "kanpuri_auto_compact"
                dialogue_budget["compact_level"] = compact_level
                dialogue_budget["spoken_text_repaired"] = True
                break

    if speedup > max_speedup + 0.003:
        raise AudioGenerationError(
            f"[VOICE NATURALNESS QA] scene={scene.id} "
            f"selected_raw={raw_total:.2f}s budget={budget:.2f}s "
            f"required_speedup={speedup:.3f}x > natural_cap={max_speedup:.2f}x. "
            "Complete-turn selection and Kanpuri filler compaction could not "
            "fit this scene naturally. Shorten the source dialogue."
        )
    speedup = min(speedup, max_speedup)

    print(
        f"[DIALOGUE BUDGET] scene={scene.id} "
        f"mode={dialogue_budget['mode']} "
        f"turns={dialogue_budget['original_turns']}->{dialogue_budget['kept_turns']} "
        f"dropped={dialogue_budget['dropped_turns']}"
    )

    master = audio_dir / "scene_audio.wav"
    timeline: list[dict[str, Any]] = []
    cursor = 0.0

    with wave.open(str(master), "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(sample_rate)

        ambient_pattern = _ambient_pattern(sample_rate) if ambient_enabled else b""

        def gap_audio(seconds: float) -> None:
            frames = max(0, int(round(seconds * sample_rate)))
            if frames <= 0:
                return
            if not ambient_enabled:
                out.writeframes(b"\x00\x00" * frames)
                return
            pattern_frames = max(1, sample_rate)
            whole, remain = divmod(frames, pattern_frames)
            for _ in range(whole):
                out.writeframes(ambient_pattern)
            if remain:
                out.writeframes(ambient_pattern[:remain * 2])

        for item, pause in zip(selected_segments, pauses):
            turn = item["turn"]
            final_path = final_dir / f"turn_{turn.index:02d}_{turn.character_id}.wav"
            _speed_wav(
                item["raw_path"],
                final_path,
                speedup,
                sample_rate,
            )
            duration = _wav_duration(final_path)
            start = cursor
            end = start + duration

            with wave.open(str(final_path), "rb") as part:
                out.writeframes(part.readframes(part.getnframes()))

            timeline.append({
                "scene_id": scene.id,
                "turn_index": turn.index,
                "character_id": turn.character_id,
                "text": turn.text,
                "spoken_text": item.get("spoken_text", turn.text),
                "emotion": turn.emotion,
                "pose": turn.pose,
                "start_seconds": round(start, 4),
                "end_seconds": round(end, 4),
                "duration_seconds": round(duration, 4),
                "pause_after_seconds": round(pause, 4),
                "audio_path": str(final_path),
            })
            cursor = end
            gap_audio(pause)
            cursor += pause

        if cursor < budget:
            gap_audio(budget - cursor)
            cursor = budget

    actual = _wav_duration(master)
    if actual > budget + 0.12:
        raise AudioGenerationError(
            f"[DURATION QA] scene={scene.id} reconciled_audio={actual:.3f}s "
            f"> budget={budget:.3f}s"
        )

    payload = {
        "scene_id": scene.id,
        "budget_seconds": round(budget, 4),
        "raw_duration_seconds": round(raw_total, 4),
        "duration_seconds": round(actual, 4),
        "speech_seconds": round(speech_total, 4),
        "pause_seconds": round(pause_total, 4),
        "speedup": round(speedup, 4),
        "master_audio": str(master),
        "turns": timeline,
        "backends_used": backends_used,
        "kanpuri_voice_v51": {
            "enabled": kanpuri_voice,
            "spoken_marker_ratio": round(_spoken_dialect_ratio(spoken_texts), 4),
            "regional_custom_backend": "kanpuri_custom_tts" in backends_used,
            "base_locale": locale,
        },
        "dialogue_budget": dialogue_budget,
        "ambient_pause_bed": ambient_enabled,
        "max_dead_air_seconds": float(config.get("audio_mastering", {}).get("max_dead_air_seconds", 1.25)),
    }
    timeline_file = audio_dir / "timeline.json"
    timeline_file.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(
        f"[DURATION QA] scene={scene.id} raw={raw_total:.2f}s "
        f"budget={budget:.2f}s speedup={speedup:.3f}x "
        f"natural_cap={max_speedup:.2f}x pauses={pause_total:.2f}s "
        f"final={actual:.2f}s"
    )
    print(
        f"[BLENDER AUDIO] scene={scene.id} "
        f"backend={','.join(backends_used) or 'silence'}"
    )
    return payload
