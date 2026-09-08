# V0.8 Architecture Delta

The V0.7 web/API/auth/billing architecture is preserved.

New render path:

`scene metadata → transition planner → bridge adaptive timing → neural TTS → edge trim → actual-waveform timing → V6.8 character performance → scene mux → hard visual concat + optional audio J-cut → loudness mastering → continuity QA`

Timing has three authorities:
- API: early UX estimate; can grow or shrink old slots.
- Bridge: transient plan repair; no fixed minimum 6.5s floor.
- Renderer V6.8: actual WAV duration is final source of truth.

The final output is rejected when adaptive continuity detects an unexplained near-silence interval above the release threshold.
