# BharatVideo AI

> AI-powered regional video creation platform for Indian creators, small businesses, and content teams.

BharatVideo AI is a web-first AI video generation platform that combines **story generation, scene planning, regional-language dialogue, TTS, Blender-based 3D rendering, FFmpeg composition, authentication, credits, and Razorpay payments** in one application.

The current project is optimized for **local development and Test Mode** first, with a path to public SaaS deployment later.

---

## 1. What BharatVideo AI does

A user can:

1. Register and log in.
2. Create a video project.
3. Enter a topic, prompt, or story idea.
4. Generate structured scenes using an LLM.
5. Edit or regenerate individual scenes.
6. Generate dialogue and voice.
7. Queue a render job.
8. Render 3D character scenes using Blender.
9. Compose media using FFmpeg.
10. Preview the final video.
11. Purchase credits/plans using Razorpay.

Typical flow:

```text
User
 ↓
Create Project
 ↓
Generate Story
 ↓
Scenes
 ↓
Voice + Actions + Camera Plan
 ↓
Render Queue
 ↓
Blender / TTS / FFmpeg
 ↓
Final Video
```

---

## 2. Current release

Current development release: **v0.8**

Major capabilities:

- Next.js + React + TypeScript frontend
- FastAPI backend
- PostgreSQL
- Redis + Celery background jobs
- Docker Compose local environment
- Ollama-first local LLM flow
- project and scene management
- scene-level regeneration
- login/register with JWT authentication
- password hashing
- project ownership checks
- credit ledger
- pricing plans
- Razorpay Test Mode integration
- UPI/Card/Netbanking support when enabled in Razorpay
- webhook signature verification
- idempotent payment fulfilment
- Blender-based 3D video rendering
- Babuji / Guddu / Bittu character workflow
- Hindi/Hinglish/Kanpuriya content support
- neural TTS path with fallback
- adaptive scene timing
- reduced unwanted silence
- FFmpeg composition and silence QA
- host render-engine bridge

---

## 3. Architecture

```text
                           User
                            │
                            ▼
                 ┌────────────────────┐
                 │ Next.js Web App    │
                 │ localhost:3000     │
                 └─────────┬──────────┘
                           │ HTTP/JSON
                           ▼
                 ┌────────────────────┐
                 │ FastAPI Backend    │
                 │ localhost:8000     │
                 └──────┬─────┬───────┘
                        │     │
                 ┌──────┘     └──────────────┐
                 ▼                           ▼
        ┌─────────────────┐          ┌─────────────────┐
        │ PostgreSQL      │          │ Redis           │
        │ persistent data │          │ queue / broker  │
        └─────────────────┘          └────────┬────────┘
                                             │
                                             ▼
                                    ┌─────────────────┐
                                    │ Celery Worker   │
                                    └────────┬────────┘
                                             │
                                             ▼
                                 ┌──────────────────────┐
                                 │ Host Engine Bridge   │
                                 │ localhost:8090       │
                                 └──────────┬───────────┘
                                            │
                                            ▼
                            ┌────────────────────────────┐
                            │ Blender / TTS / FFmpeg     │
                            │ agentic-content-factory    │
                            └────────────────────────────┘
```

Billing flow:

```text
User
 ↓
Pricing Page
 ↓
Razorpay Checkout
 ↓
UPI / Card / Netbanking
 ↓
Payment Captured
 ↓
Webhook
 ↓
FastAPI
 ↓
Credit Ledger / Subscription
```

---

## 4. Technology stack

### Frontend

- Next.js
- React
- TypeScript
- Tailwind CSS

### Backend

- Python
- FastAPI
- SQLAlchemy
- PostgreSQL

### Background processing

- Redis
- Celery

### AI / Media

- Ollama
- local LLM such as `llama3.2`
- Blender
- FFmpeg
- neural TTS integration
- macOS speech fallback

### Payments

- Razorpay
- Test Mode for local development
- signature verification
- webhook validation
- idempotent credit fulfilment

### Infrastructure

- Docker
- Docker Compose
- zrok for temporary public webhook testing

---

## 5. Repository structure

Core folders used by the current release:

```text
bharatvideo_ai_mvp_v0_1/
│
├── apps/
│   ├── api/                 # FastAPI backend
│   └── web/                 # Next.js frontend
│
├── engine_bridge/           # Bridge to host rendering engine
├── engine_adapters/         # Adapter layer for rendering/media providers
├── engine_patch/            # BharatVideo timing/render improvements
├── packages/                # Shared/supporting packages
├── scripts/                 # Install/verify/helper scripts
│
├── docker-compose.yml
├── .env.example
├── .gitignore
├── VERSION
└── README.md
```

The existing Blender/media engine currently lives outside this repository:

```text
/Users/maa/agentic-content-factory
```

This separation is intentional.

BharatVideo owns:

- UI
- users
- projects
- scenes
- billing
- credits
- queues
- orchestration

The host engine owns:

- Blender scene generation
- animation
- TTS/media integration
- FFmpeg composition

---

## 6. Prerequisites

Recommended local setup:

- macOS
- Docker Desktop
- Git
- Python 3
- Blender
- FFmpeg
- Ollama
- zrok only for local webhook testing

Check tools:

```bash
git --version
docker --version
docker compose version
python3 --version
ffmpeg -version
blender --version
ollama --version
```

---

## 7. Clone

```bash
git clone https://github.com/raushan-raj-ai-engineer/BharatVideo-AI.git
cd BharatVideo-AI
```

Current local development folder may still be:

```bash
cd ~/Downloads/bharatvideo_ai_mvp_v0_1
```

The folder name is historical; check `VERSION` for the actual installed release.

---

## 8. Environment setup

Create local environment file:

```bash
cp .env.example .env
```

Never commit `.env`.

Example development configuration:

```env
BILLING_MODE=mock

RAZORPAY_KEY_ID=
RAZORPAY_KEY_SECRET=
RAZORPAY_WEBHOOK_SECRET=
RAZORPAY_EXPECTED_ACCOUNT_ID=

OLLAMA_MODEL=llama3.2
```

For Razorpay **Test Mode**:

```env
BILLING_MODE=razorpay
RAZORPAY_KEY_ID=rzp_test_xxxxxxxxx
RAZORPAY_KEY_SECRET=your_test_secret
RAZORPAY_WEBHOOK_SECRET=your_webhook_secret
```

Never place real credentials in source code, Git commits, screenshots, or documentation.

---

## 9. Start the application

Make sure Docker Desktop is running.

```bash
docker compose up -d
```

Check services:

```bash
docker compose ps
```

Main local endpoints:

| Service | Address |
|---|---|
| Web | `http://localhost:3000` |
| API | `http://localhost:8000` |
| API Docs | `http://localhost:8000/docs` |
| PostgreSQL | `localhost:5432` |
| Redis | `localhost:6379` |
| Host render bridge | `http://localhost:8090` |

Logs:

```bash
docker compose logs -f api
```

```bash
docker compose logs -f worker
```

```bash
docker compose logs -f web
```

Avoid this unless you intentionally want to delete persistent volumes:

```bash
docker compose down -v
```

---

## 10. Basic checks

Billing plans:

```bash
curl http://localhost:8000/v1/billing/plans
```

Frontend:

```text
http://localhost:3000
```

FastAPI Swagger:

```text
http://localhost:8000/docs
```

---

## 11. End-to-end video flow

```text
Register/Login
    ↓
Create Project
    ↓
Enter Topic/Story
    ↓
Generate Scenes
    ↓
Review/Edit Scene
    ↓
Regenerate if needed
    ↓
Generate Voice/Media
    ↓
Queue Render
    ↓
Redis
    ↓
Celery Worker
    ↓
Host Engine Bridge
    ↓
Blender + TTS + FFmpeg
    ↓
Final Preview
```

Long-running rendering is intentionally asynchronous. The HTTP API should create a job and let a worker process it instead of blocking the browser request.

---

## 12. Real video mode

The intended output is a real character-based video, not just static cards.

The current real-render path can use:

- Blender 3D characters
- multiple camera cuts
- character actions
- facial/mouth states
- story-specific props
- neural speech
- adaptive scene timing
- FFmpeg final composition

Recurring characters currently include:

- Babuji
- Guddu
- Bittu

Examples of normalized action concepts:

```text
mock_shock
snatch_phone
whisper
phone_pass
ai_interview
backpedal
```

---

## 13. Scene timing and silence handling

Earlier versions could create excessive gaps because dialogue scenes used conservative minimum durations.

The current approach prefers:

- actual speech duration
- adaptive scene duration
- short conversational transitions
- larger pauses only for reactions/punchlines
- room-tone continuity
- final silence detection

A technically successful render can still be a bad video. Video quality must consider motion, pacing, speech, camera variety, props, and continuity.

---

## 14. Authentication and authorization

The current application supports:

- registration
- login
- password hashing
- JWT authentication
- protected routes
- project ownership
- account credits

Remember:

- **Authentication** = who are you?
- **Authorization** = are you allowed to access this project/resource?

A valid login must not allow one user to access another user's private project.

---

## 15. Pricing and credits

Current development plans:

| Plan | Price | Credits |
|---|---:|---:|
| Free | ₹0 | 30 |
| Creator | ₹299 | 250 |
| Pro | ₹799 | 800 |
| Business | ₹1,499 | 1,800 |

These values are product configuration and may evolve.

The credit ledger should be the source of truth for credit additions/deductions.

---

## 16. Razorpay Test Mode

Always validate Test Mode before Live Mode.

```text
BharatVideo
    ↓
Create Razorpay Test Order
    ↓
Checkout
    ↓
Test Payment
    ↓
Callback Verification
    ↓
Webhook
    ↓
Confirm Captured State
    ↓
Credits Added Exactly Once
```

Important rules:

- use `rzp_test_...` keys locally
- Test Mode does not charge real money
- browser callback is not enough by itself
- verify payment signatures
- verify webhook signatures
- only fulfil captured/paid payments
- callback and webhook must not add credits twice

---

## 17. Local webhook testing with zrok

Razorpay cannot directly call `localhost`.

Install:

```bash
brew install zrok
```

Enable:

```bash
zrok enable YOUR_ACCOUNT_TOKEN
```

Do not share the token.

Share the API:

```bash
zrok share public http://localhost:8000
```

Example public URL:

```text
https://example.share.zrok.io
```

Razorpay Test webhook URL:

```text
https://example.share.zrok.io/v1/billing/webhooks/razorpay
```

Typical events used by the app:

```text
payment.authorized
payment.captured
payment.failed
order.paid
```

Keep zrok running while testing.

---

## 18. Testing

### API tests inside Docker

The running API image may not include pytest by default. For temporary local testing:

```bash
docker compose exec api sh -lc \
'pip install -q pytest && python -m pytest -q'
```

For isolated test configuration:

```bash
docker compose exec \
  -e BILLING_MODE=mock \
  -e RAZORPAY_EXPECTED_ACCOUNT_ID= \
  -e REDIS_URL=redis://redis:6379/15 \
  -e CELERY_BROKER_URL=redis://redis:6379/15 \
  -e CELERY_RESULT_BACKEND=redis://redis:6379/15 \
  api sh -lc \
  'python -m pytest -q --ignore=tests/test_bridge_duration_autofit.py'
```

### Host bridge test

This test depends on the host repository layout:

```bash
/Users/maa/agentic-content-factory/.venv/bin/python \
-m pytest apps/api/tests/test_bridge_duration_autofit.py -q
```

The important rule is:

> Keep test configuration separate from real local Razorpay configuration.

---

## 19. Common troubleshooting

### `python: command not found`

Use:

```bash
python3 --version
```

or activate a virtual environment.

### `ModuleNotFoundError: fastapi`

You are using a Python environment without project dependencies. Use the Docker API environment or install dependencies in a venv.

### `No module named pytest`

Install pytest in the test environment.

### Redis connection refused inside Docker

Wrong:

```text
redis://localhost:6379
```

Correct Compose-style hostname:

```text
redis://redis:6379
```

Inside a container, `localhost` refers to that same container.

### Billing test expects mock but receives razorpay

Your real local `.env` may use:

```env
BILLING_MODE=razorpay
```

while an automated test expects mock billing. Override the variable only for the test process.

### `Webhook account mismatch`

A real expected Razorpay account ID can conflict with fake test fixture data. Clear it only in isolated tests, not in your real configuration.

### API works but Blender render fails

Docker health does not prove the host rendering engine is running.

Trace:

```text
API → Worker → Host Bridge :8090 → agentic-content-factory → Blender
```

---

## 20. Git safety

Never commit:

```text
.env
API secrets
Razorpay secrets
webhook secrets
zrok tokens
large generated videos
audio artifacts
database dumps
node_modules
.next
```

Recommended `.gitignore` entries:

```gitignore
.env
.env.local
.env.production

node_modules/
.next/

__pycache__/
*.pyc
.pytest_cache/

logs/
storage/
artifacts/

*.mp4
*.wav
*.mp3
*.aiff

.DS_Store
```

Before commit:

```bash
git status
git diff
```

Check accidentally tracked `.env`:

```bash
git ls-files | grep -E '(^|/)\.env$'
```

Credential check:

```bash
git grep -n "rzp_test_"
git grep -n "rzp_live_"
```

No real credentials should appear.

---

## 21. Recommended Git workflow

```bash
git switch -c feature/my-feature
```

Make change, run tests, then:

```bash
git diff
git status
git add .
git commit -m "feat: describe the feature"
git push -u origin feature/my-feature
```

Useful prefixes:

```text
feat:
fix:
test:
docs:
refactor:
```

---

## 22. Engineering principles

### Scene-first generation

```text
Project
  └── Scenes
        ├── Dialogue
        ├── Voice
        ├── Visual Plan
        ├── Action
        └── Rendered Media
```

This makes scene-level editing and regeneration possible.

### Provider abstraction

Do not hard-code the entire application to one provider.

The architecture should be able to support providers such as:

```text
Ollama
Blender
Veo
Runway
other TTS/video providers
```

behind clear adapters.

### Background jobs

```text
API → Queue → Worker
```

Long media work should not block HTTP requests.

### Idempotent billing

One payment must produce one fulfilment, even if callback/webhook events repeat.

### Local-first, cloud-ready

Keep development inexpensive locally while maintaining boundaries that allow storage, render workers, DB, and providers to move to cloud infrastructure later.

---

## 23. Production roadmap

Before public paid launch, complete at least:

- permanent domain
- HTTPS
- production deployment
- database backup strategy
- object storage
- monitoring/logging
- rate limiting
- production secrets management
- production TTS provider/licensing
- Razorpay Live KYC/activation
- live webhook
- refund/cancellation logic
- render-failure credit compensation
- Terms of Service
- Privacy Policy
- support/contact process
- load/performance testing
- security review

---

## 24. Contribution ideas

Beginner-friendly:

- improve error messages
- loading states
- empty states
- input validation
- API tests
- payment regression tests
- documentation
- accessible labels
- one extra language option

Intermediate:

- dedicated `.env.test`
- dev dependency file including pytest
- CI pipeline
- database migrations
- render cancellation
- job retries
- cloud storage abstraction
- email verification
- forgot password
- rate limiting
- structured logging

Advanced:

- cloud render workers
- GPU-aware queueing
- Veo/Runway adapters
- better lip sync/visemes
- reusable animation library
- scene continuity scoring
- autoscaling
- CDN
- observability/tracing
- subscription renewal flows

---

## 25. New developer learning order

Do not try to understand everything at once.

```text
Day 1  Run the app
Day 2  Understand Web → API
Day 3  Understand database models
Day 4  Understand authentication
Day 5  Understand projects/scenes
Day 6  Understand Redis + Celery
Day 7  Understand host bridge
Day 8  Understand Blender/TTS/FFmpeg
Day 9  Understand billing/credits
Day 10 Run tests and make one small improvement
```

For a full beginner explanation, read:

**`FRESHER_END_TO_END_GUIDE.md`**

---

## 26. Disclaimer

BharatVideo AI is currently a development-stage project. Local tunnels, Test Mode credentials, local storage, and development settings are not production security controls.

Complete a proper production, legal, security, and operational review before accepting real customers.

---

## License

Add the final project license before public/open-source distribution. If the repository remains private/commercial, document internal usage rights separately.
