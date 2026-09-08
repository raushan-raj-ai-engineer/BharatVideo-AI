# Agentic Content Factory adapter — v0.2

The existing `/Users/maa/agentic-content-factory` repository stays independent.

v0.2 uses a small guarded **host bridge** instead of importing or modifying the existing engine:

1. BharatVideo worker creates an explicit episode-plan JSON.
2. Docker calls `host.docker.internal:8090` with a shared local-dev token.
3. `engine_bridge/bridge_server.py` runs on macOS, where Blender/Homebrew are available.
4. The bridge invokes `content_factory.cartoon.blender_full.cli --render-plan ...`.
5. The resulting MP4 is copied back into BharatVideo local storage.

The bridge does **not** accept arbitrary shell commands. It exposes only health, preflight and validated render operations.
