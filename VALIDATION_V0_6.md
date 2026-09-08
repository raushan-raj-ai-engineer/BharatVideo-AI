# V0.6 validation

- BharatVideo API/service regression: 17/17 PASS.
- Python compile: bridge, neural TTS helper, and patched audio engine PASS.
- Shell syntax: installer/start/bridge scripts PASS.
- Existing V6.6 timing fix retained; neural TTS is an additive hook before macOS `say` fallback.
- Full frontend TypeScript build was not executed in the artifact container because React/Next dependencies are not installed there. Docker build installs those dependencies on the target system.
- Full Blender graphical render cannot be executed in this artifact environment; the user's Mac Blender installation is the runtime target.
