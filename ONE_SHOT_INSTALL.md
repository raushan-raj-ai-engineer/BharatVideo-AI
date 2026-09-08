# BharatVideo AI V0.8 one-shot upgrade

V0.8 contains the adaptive video-continuity/performance changes plus the completed Razorpay payment path.

```bash
cd ~/Downloads
unzip -o bharatvideo_ai_mvp_v0_8.zip
cd bharatvideo_ai_mvp_v0_8

./install_and_start_v0_8.sh \
  ~/Downloads/bharatvideo_ai_mvp_v0_1 \
  /Users/maa/agentic-content-factory
```

The installer:

- backs up release-controlled app code and active Blender engine files;
- preserves `.env`, storage and Docker/PostgreSQL volumes;
- installs renderer V6.8 + bridge 0.8.0;
- verifies the active imported engine path;
- runs duration/continuity engine regression tests;
- installs the improved app UI/API;
- adds missing Razorpay webhook env placeholders without overwriting existing values;
- rebuilds/recreates Docker services without `-v`;
- restarts the authenticated engine bridge.

After successful startup, open `http://localhost:3000`.

## Razorpay remains opt-in

The safe default is `BILLING_MODE=mock`. To accept payments, configure Test mode first using `PAYMENTS_V0_8.md`. Do not put live secrets in Git.

Do not apply V0.3.x/V0.4/V0.5/V0.6/V0.7 patches after V0.8.
