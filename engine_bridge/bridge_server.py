#!/usr/bin/env python3
"""Guarded macOS host bridge for BharatVideo AI.

V0.8 adds adaptive continuity on top of render safety:
1) a conservative transient scene-duration guard before Blender is launched;
2) active-engine patch verification so Diagnostics can prove which renderer code
   is actually being imported from /Users/maa/agentic-content-factory.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import threading
import uuid
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

BRIDGE_VERSION = "0.8.0"
ENGINE_MARKER = "ADAPTIVE AUDIO CONTINUITY V6.8"
PIPELINE_MARKER = "ADAPTIVE SCENE STITCH V6.8"
WORKER_MARKER = "BHARATVIDEO PERFORMANCE V6.8"


class BridgeConfig:
    def __init__(self, repo_root: Path, token: str):
        self.repo_root = repo_root.resolve()
        self.token = token
        self.asset_dir = Path(tempfile.gettempdir()) / "bharatvideo_engine_bridge_assets"
        self.asset_dir.mkdir(parents=True, exist_ok=True)
        self.assets: dict[str, tuple[Path, str]] = {}
        self.lock = threading.Lock()

    def python(self) -> str:
        candidates = [self.repo_root / ".venv/bin/python", self.repo_root / "venv/bin/python"]
        for item in candidates:
            if item.is_file():
                return str(item)
        found = shutil.which("python3")
        if not found:
            raise RuntimeError("No Python interpreter found for Agentic Content Factory")
        return found

    def base_env(self) -> dict[str, str]:
        env = os.environ.copy()
        src = str(self.repo_root / "src")
        env["PYTHONPATH"] = src + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
        return env

    def engine_patch_status(self) -> dict:
        audio = self.repo_root / "src/content_factory/cartoon/blender_full/audio.py"
        pipeline = self.repo_root / "src/content_factory/cartoon/blender_full/pipeline.py"
        worker = self.repo_root / "src/content_factory/cartoon/blender_full/worker_full.py"
        audio_text = audio.read_text(encoding="utf-8") if audio.is_file() else ""
        pipeline_text = pipeline.read_text(encoding="utf-8") if pipeline.is_file() else ""
        worker_text = worker.read_text(encoding="utf-8") if worker.is_file() else ""
        return {
            "active": ENGINE_MARKER in audio_text and PIPELINE_MARKER in pipeline_text and WORKER_MARKER in worker_text,
            "renderer_version": "V6.8" if ENGINE_MARKER in audio_text and WORKER_MARKER in worker_text else "legacy/unknown",
            "audio_marker": ENGINE_MARKER in audio_text,
            "pipeline_marker": PIPELINE_MARKER in pipeline_text,
            "worker_marker": WORKER_MARKER in worker_text,
            "audio_path": str(audio),
            "pipeline_path": str(pipeline),
            "worker_path": str(worker),
            "audio_sha256": hashlib.sha256(audio.read_bytes()).hexdigest() if audio.is_file() else None,
            "pipeline_sha256": hashlib.sha256(pipeline.read_bytes()).hexdigest() if pipeline.is_file() else None,
            "worker_sha256": hashlib.sha256(worker.read_bytes()).hexdigest() if worker.is_file() else None,
            "neural_tts_hook": "CONTENT_FACTORY_TTS_CMD" in audio_text,
            "adaptive_continuity": "ADAPTIVE AUDIO CONTINUITY V6.8" in audio_text,
            "adaptive_jcut": "ADAPTIVE SCENE STITCH V6.8" in pipeline_text,
            "performance_v68": WORKER_MARKER in worker_text,
            "neural_tts_script": str(self.repo_root / "scripts/bharatvideo_neural_tts.py"),
        }


CONFIG: BridgeConfig


def _json(handler: BaseHTTPRequestHandler, status: int, payload: dict):
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _newest_mp4(root: Path) -> Path | None:
    files = [p for p in root.rglob("*.mp4") if p.is_file()]
    return max(files, key=lambda p: p.stat().st_mtime) if files else None


def _estimate_natural_dialogue_seconds(scene: dict) -> float:
    """V0.8 bridge estimate: natural enough to protect TTS, never a fixed 6.5s floor.

    Renderer V6.8 still measures actual WAV duration.  This bridge estimate exists
    to prevent both under-sized authoring slots and the old over-sized fixed-gap slots.
    """
    turns = scene.get("dialogue") or []
    texts = [str(t.get("text") or "").strip() for t in turns if str(t.get("text") or "").strip()]
    if not texts:
        return 2.0
    joined = " ".join(texts)
    words = [w for w in joined.replace("\n", " ").split(" ") if w.strip()]
    visible_chars = sum(1 for ch in joined if not ch.isspace())
    speech = max(len(words) / 1.85, visible_chars / 7.1, 1.35)
    planned_pauses = sum(max(0.02, min(0.75, float(t.get("pause_after_seconds") or 0.07))) for t in turns)
    safety = 0.24
    return round(max(2.0, speech + planned_pauses + safety), 2)


def _autofit_plan_dialogue_budgets(plan: dict) -> list[dict]:
    changes = []
    adaptive_project = bool((plan.get("story_engine") or {}).get("adaptive_scene_timing_v08"))
    for scene in plan.get("scenes") or []:
        old = max(2.0, float(scene.get("shot_duration_seconds") or 2.0))
        natural = _estimate_natural_dialogue_seconds(scene)
        adaptive_scene = adaptive_project or str(scene.get("timing_mode") or "").startswith("adaptive_dialogue")
        # V0.8 can shrink old 6.5s safety slots as well as grow short ones.
        new = round(natural if adaptive_scene else max(old, natural), 2)
        if abs(new - old) > 0.01:
            scene["shot_duration_seconds"] = new
            changes.append({
                "scene_id": scene.get("id"), "from": old, "to": new,
                "direction": "shrink" if new < old else "grow",
                "guard": "adaptive_bridge_v0.8",
            })
    return changes



class Handler(BaseHTTPRequestHandler):
    server_version = f"BharatVideoEngineBridge/{BRIDGE_VERSION}"

    def log_message(self, fmt, *args):
        print(f"[ENGINE BRIDGE] {self.address_string()} - {fmt % args}")

    def authorized(self) -> bool:
        return self.headers.get("X-BharatVideo-Bridge-Token", "") == CONFIG.token

    def read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0") or 0)
        if length <= 0 or length > 2_000_000:
            raise ValueError("Invalid request body size")
        data = json.loads(self.rfile.read(length).decode("utf-8"))
        if not isinstance(data, dict):
            raise ValueError("JSON root must be an object")
        return data

    def do_GET(self):
        if not self.authorized():
            return _json(self, HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})
        path = urlparse(self.path).path
        if path == "/health":
            try:
                return _json(self, HTTPStatus.OK, {
                    "status": "ok",
                    "bridge_version": BRIDGE_VERSION,
                    "repo_root": str(CONFIG.repo_root),
                    "python": CONFIG.python(),
                    "repo_exists": CONFIG.repo_root.is_dir(),
                    "engine_patch": CONFIG.engine_patch_status(),
                })
            except Exception as exc:
                return _json(self, HTTPStatus.SERVICE_UNAVAILABLE, {"status": "error", "error": str(exc)})
        if path.startswith("/assets/"):
            asset_id = path.rsplit("/", 1)[-1]
            with CONFIG.lock:
                asset = CONFIG.assets.get(asset_id)
            if not asset or not asset[0].is_file():
                return _json(self, HTTPStatus.NOT_FOUND, {"error": "asset not found"})
            file_path, content_type = asset
            content = file_path.read_bytes()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(content)))
            self.send_header("X-Content-SHA256", hashlib.sha256(content).hexdigest())
            self.end_headers()
            self.wfile.write(content)
            return
        return _json(self, HTTPStatus.NOT_FOUND, {"error": "not found"})

    def do_POST(self):
        if not self.authorized():
            return _json(self, HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})
        path = urlparse(self.path).path
        try:
            if path == "/preflight":
                patch = CONFIG.engine_patch_status()
                cmd = [CONFIG.python(), "-m", "content_factory.cartoon.blender_full.cli", "--project", str(CONFIG.repo_root), "--check-only"]
                proc = subprocess.run(cmd, cwd=CONFIG.repo_root, env=CONFIG.base_env(), text=True, capture_output=True, timeout=180)
                ok = proc.returncode == 0
                return _json(self, HTTPStatus.OK if ok else HTTPStatus.BAD_GATEWAY, {
                    "status": "ok" if ok else "failed", "returncode": proc.returncode,
                    "engine_patch": patch, "stdout": proc.stdout[-8000:], "stderr": proc.stderr[-8000:],
                })

            if path == "/tts":
                data = self.read_json(); text = str(data.get("text") or "").strip(); voice = str(data.get("voice") or "Lekha").strip(); rate = int(data.get("rate") or 185)
                if not text or len(text) > 4000: raise ValueError("text must be 1..4000 characters")
                if not 100 <= rate <= 260: raise ValueError("rate must be 100..260")
                if not all(ch.isalnum() or ch in " _-" for ch in voice): raise ValueError("invalid voice name")
                ffmpeg = shutil.which("ffmpeg")
                if not ffmpeg: raise RuntimeError("ffmpeg is required for host TTS")
                asset_id = str(uuid.uuid4()); wav = CONFIG.asset_dir / f"{asset_id}.wav"
                neural = CONFIG.repo_root / "scripts/bharatvideo_neural_tts.py"
                backend = "macos_say"
                if neural.is_file():
                    proc = subprocess.run([CONFIG.python(), str(neural), "--text", text, "--output", str(wav), "--character", voice], cwd=CONFIG.repo_root, env=CONFIG.base_env(), text=True, capture_output=True, timeout=240)
                    if proc.returncode == 0 and wav.is_file(): backend = "edge_neural"
                    else: print("[ENGINE BRIDGE V0.8] neural TTS fallback: " + (proc.stderr[-1500:] or proc.stdout[-1500:]))
                if not wav.is_file():
                    say = shutil.which("say")
                    if not say: raise RuntimeError("Neural TTS failed and macOS say fallback is unavailable")
                    aiff = CONFIG.asset_dir / f"{asset_id}.aiff"
                    proc = subprocess.run([say, "-v", voice, "-r", str(rate), "-o", str(aiff), text], text=True, capture_output=True, timeout=180)
                    if proc.returncode != 0: raise RuntimeError(f"say failed: {proc.stderr[-2000:]}")
                    proc = subprocess.run([ffmpeg, "-y", "-i", str(aiff), "-ar", "48000", "-ac", "2", str(wav)], text=True, capture_output=True, timeout=180); aiff.unlink(missing_ok=True)
                    if proc.returncode != 0 or not wav.is_file(): raise RuntimeError(f"ffmpeg TTS conversion failed: {proc.stderr[-2000:]}")
                with CONFIG.lock: CONFIG.assets[asset_id] = (wav, "audio/wav")
                return _json(self, HTTPStatus.OK, {"status": "succeeded", "asset_id": asset_id, "voice": voice, "rate": rate, "backend": backend, "size_bytes": wav.stat().st_size})

            if path == "/render":
                data = self.read_json(); plan = data.get("plan")
                if not isinstance(plan, dict) or not isinstance(plan.get("scenes"), list) or not plan["scenes"]: raise ValueError("plan.scenes must be a non-empty list")
                if len(plan["scenes"]) > 40: raise ValueError("Bridge refuses plans above 40 scenes")
                patch = CONFIG.engine_patch_status()
                duration_changes = _autofit_plan_dialogue_budgets(plan)
                if duration_changes: print(f"[ENGINE BRIDGE V0.8] conservative speech guard: {duration_changes}")
                if not patch["active"]:
                    print("[ENGINE BRIDGE V0.8] WARNING: renderer V6.8 marker not active; conservative bridge timing guard remains enabled")

                quality = str(data.get("quality") or "draft")
                if quality not in {"draft", "standard", "high"}: raise ValueError("invalid quality")
                max_scenes = data.get("max_scenes")
                if max_scenes is not None:
                    max_scenes = int(max_scenes)
                    if not 1 <= max_scenes <= 12: raise ValueError("max_scenes must be 1..12 or null")

                render_id = str(uuid.uuid4()); work_dir = Path(tempfile.gettempdir()) / f"bharatvideo_render_{render_id}"; output_dir = work_dir / "output"; output_dir.mkdir(parents=True, exist_ok=True)
                plan_path = work_dir / "episode_plan.json"; plan_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
                validate_code = "from content_factory.cartoon.blender_full.plan_adapter import load_episode_plan; " + f"p=load_episode_plan({str(plan_path)!r}); " + "print(f'PLAN_OK scenes={len(p.scenes)} characters={p.characters}')"
                validate_proc = subprocess.run([CONFIG.python(), "-c", validate_code], cwd=CONFIG.repo_root, env=CONFIG.base_env(), text=True, capture_output=True, timeout=60)
                if validate_proc.returncode != 0:
                    return _json(self, HTTPStatus.UNPROCESSABLE_ENTITY, {"status":"failed","stage":"plan_validation","returncode":validate_proc.returncode,"stdout":validate_proc.stdout[-8000:],"stderr":validate_proc.stderr[-12000:]})

                cmd = [CONFIG.python(), "-m", "content_factory.cartoon.blender_full.cli", "--project", str(CONFIG.repo_root), "--render-plan", str(plan_path), "--output-dir", str(output_dir), "--quality", quality, "--fresh"]
                if max_scenes is not None: cmd += ["--max-scenes", str(max_scenes)]
                print(f"[ENGINE BRIDGE V0.8] render start id={render_id} quality={quality} max_scenes={max_scenes or 'ALL'} patch_active={patch['active']}")
                proc = subprocess.run(cmd, cwd=CONFIG.repo_root, env=CONFIG.base_env(), text=True, capture_output=True)
                if proc.returncode != 0:
                    if proc.stdout: print("[ENGINE BRIDGE] renderer stdout tail:\n" + proc.stdout[-6000:])
                    if proc.stderr: print("[ENGINE BRIDGE] renderer stderr tail:\n" + proc.stderr[-12000:])
                    return _json(self, HTTPStatus.BAD_GATEWAY, {"status":"failed","stage":"renderer","returncode":proc.returncode,"engine_patch":patch,"duration_autofit":duration_changes,"stdout":proc.stdout[-12000:],"stderr":proc.stderr[-16000:]})
                mp4 = _newest_mp4(output_dir)
                if not mp4: return _json(self, HTTPStatus.BAD_GATEWAY, {"status":"failed","error":"Renderer completed but no MP4 was found","engine_patch":patch,"stdout":proc.stdout[-12000:],"stderr":proc.stderr[-12000:]})
                stable = CONFIG.asset_dir / f"{render_id}.mp4"; shutil.copy2(mp4, stable)
                with CONFIG.lock: CONFIG.assets[render_id] = (stable, "video/mp4")
                return _json(self, HTTPStatus.OK, {"status":"succeeded","bridge_version":BRIDGE_VERSION,"engine_patch":patch,"duration_autofit":duration_changes,"asset_id":render_id,"output_file":str(mp4),"size_bytes":stable.stat().st_size,"stdout_tail":proc.stdout[-4000:]})
        except (ValueError, json.JSONDecodeError) as exc:
            return _json(self, HTTPStatus.BAD_REQUEST, {"error": str(exc)})
        except Exception as exc:
            return _json(self, HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})
        return _json(self, HTTPStatus.NOT_FOUND, {"error": "not found"})


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--repo", default=os.getenv("HOST_AGENTIC_CONTENT_FACTORY_ROOT", "/Users/maa/agentic-content-factory")); parser.add_argument("--token", default=os.getenv("ENGINE_BRIDGE_TOKEN", "change-me-local-dev-token")); parser.add_argument("--host", default="0.0.0.0"); parser.add_argument("--port", type=int, default=8090); args = parser.parse_args()
    global CONFIG; CONFIG = BridgeConfig(Path(args.repo).expanduser(), args.token)
    if not CONFIG.repo_root.is_dir(): raise SystemExit(f"Repo not found: {CONFIG.repo_root}")
    print(f"[ENGINE BRIDGE V0.8] repo={CONFIG.repo_root}"); print(f"[ENGINE BRIDGE V0.8] patch={CONFIG.engine_patch_status()}"); print(f"[ENGINE BRIDGE V0.8] listening=http://{args.host}:{args.port}")
    ThreadingHTTPServer((args.host, args.port), Handler).serve_forever(); return 0

if __name__ == "__main__": raise SystemExit(main())
