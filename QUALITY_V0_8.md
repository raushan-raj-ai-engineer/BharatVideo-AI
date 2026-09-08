# BharatVideo AI V0.8 — Video Quality Consolidation

V0.8 is the pacing/performance quality pass based on the real V0.6/V0.7 rendered preview.

## Audio continuity
- Removed the old fixed 6.5-second bridge floor that created long empty scene tails.
- Renderer V6.8 measures generated speech and can grow **or shrink** the scene budget.
- Leading/trailing TTS silence is trimmed.
- Ordinary dialogue boundaries use short adaptive transitions instead of identical fixed silence.
- Low-level room tone prevents digital-silence holes.
- Scene stitching supports small J-cut style overlaps where safe.
- Final continuity QA uses FFmpeg `silencedetect`; unexplained long near-silence is a QA failure rather than a successful export.

## Character performance
- Babuji/Guddu/Bittu comedy cast lock retained.
- Free-form LLM actions are normalized to renderer-supported actions.
- Stronger physical actions include `mock_shock`, `snatch_phone`, `whisper`, `phone_pass`, `ai_interview`, `backpedal`, and prop interactions.
- Story-prop inference is strengthened for phone/chai/charpai and related scene context.
- Movement amplitude was increased so camera cuts do not hide static bodies.
- Lightweight text-driven viseme animation replaces a purely binary mouth-open/mouth-close look.

## What V0.8 does not claim
This is still a lightweight procedural Blender character engine, not a Veo/Runway-class diffusion video model. V0.8 improves pacing, acting and continuity; external generative-video providers remain the future premium path for cinematic shots.
