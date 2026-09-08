# BharatVideo AI MVP V0.8 — Quality + Payments Consolidated Release

V0.8 is a one-shot upgrade over V0.7. It preserves login, protected projects, pricing and credits, while fixing the biggest pacing issues seen in the real rendered preview and completing the Razorpay payment path for India.

## 1. Video quality / natural pacing

- Removes the old fixed 6.5-second dialogue safety floor that caused long empty scene tails.
- Renderer V6.8 measures real generated speech and can **grow or shrink** scene duration.
- Leading/trailing TTS silence is trimmed before scene timing is finalized.
- Fixed silence between every scene is replaced by adaptive transition timing.
- Ordinary conversation gets near-zero/short transitions; reactions and punchlines keep intentional holds.
- Low-level room tone avoids digital-silence holes.
- Small J-cut style audio overlap is available for continuous dialogue.
- Final FFmpeg continuity QA detects unexplained near-silence and can fail the export instead of silently shipping dead air.
- Babuji/Guddu/Bittu cast lock remains enabled for comedy projects.
- Unsupported LLM actions are normalized to renderer-supported physical actions.
- Stronger prop interaction / movement for phone snatch, phone pass, whisper, AI interview, recoil/backpedal and reaction beats.
- Lightweight text-driven mouth visemes improve the old binary puppet-mouth look.

See `QUALITY_V0_8.md`.

## 2. Login / account / pricing

Preserved and regression-tested:

- Register + login.
- Account-scoped/private projects.
- Existing legacy project claim for the first account.
- Signup credits and credit ledger.
- Free / Creator / Pro / Business pricing.
- Account page with credit and payment history.

## 3. Razorpay: UPI + cards + net banking

V0.8 completes the payment path rather than only showing pricing cards.

- Server-side Razorpay Order creation.
- Razorpay Standard Checkout in the web app.
- UPI Intent/QR, cards and net banking when enabled on the merchant Razorpay account.
- Checkout signature verification on the server.
- Server fetches the Razorpay payment and requires `captured` status, exact order, amount and INR currency before entitlement.
- Raw-body webhook HMAC verification with a **separate webhook secret**.
- `X-Razorpay-Event-Id` webhook dedupe.
- Exactly-once `PaymentFulfillment` guard prevents double credits from callback + repeated webhook events.
- `payment.authorized` does not grant credits.
- `payment.captured` / `order.paid` can fulfill the order.
- Failed/authorised/captured attempts appear in payment history.
- Mock/Test billing remains the safe default; no real money is charged until you explicitly configure Razorpay.

See `PAYMENTS_V0_8.md`.

## One-shot upgrade

```bash
cd ~/Downloads
unzip -o bharatvideo_ai_mvp_v0_8.zip
cd bharatvideo_ai_mvp_v0_8

./install_and_start_v0_8.sh \
  ~/Downloads/bharatvideo_ai_mvp_v0_1 \
  /Users/maa/agentic-content-factory
```

Open:

```text
http://localhost:3000
```

The installer preserves `.env`, PostgreSQL/Docker volumes, storage and existing projects. New payment audit/idempotency tables are additive.

## Enable Razorpay Test mode after install

Keep the app in mock mode until your Test keys are ready. Then edit:

```text
~/Downloads/bharatvideo_ai_mvp_v0_1/.env
```

Set:

```env
BILLING_MODE=razorpay
RAZORPAY_KEY_ID=rzp_test_...
RAZORPAY_KEY_SECRET=...
RAZORPAY_WEBHOOK_SECRET=...
```

Restart API + web (or rerun the start script). Configure the Test-mode Razorpay webhook to:

```text
https://YOUR-PUBLIC-API/v1/billing/webhooks/razorpay
```

Use a separate webhook secret. Do not commit any real/test secrets to Git.

## Validation performed in the packaging environment

- BharatVideo API/auth/billing/continuity: **28/28 PASS**.
- Full Agentic Content Factory renderer regression with V6.8 overlay: **92/92 PASS**.
- Exact earlier 3.59s-in-3.00s timing regression: PASS.
- Adaptive pause / oversized-slot shrink / silence trim / continuity tests: PASS.
- Razorpay webhook bad-signature, captured, duplicate-event and exactly-once fulfillment tests: PASS.
- Python compile: PASS.
- Shell syntax: PASS.
- TS/TSX source parse: PASS (10 files).
- V0.7 → V0.8 installer simulation: PASS.
- Rollback simulation: PASS.

### Validation limitation

The packaging environment cannot run the target Mac's Blender 5.2 graphical render. It also could not complete a full `next build` because dependency download timed out; the TS/TSX source was syntax-parsed successfully and the target Docker build installs the pinned Next/React packages.

## Do not apply older patches afterwards

V0.8 supersedes the earlier V0.3.x–V0.7 patch chain.
