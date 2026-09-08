# BharatVideo AI — Fresher End-to-End Guide

This document explains BharatVideo AI from zero for a fresher, junior developer, tester, or contributor.

You do **not** need to understand React, FastAPI, Docker, Redis, Celery, Blender, FFmpeg, AI, and payments on day one.

The correct approach is to understand the product one layer at a time.

---

# 1. First understand the product

BharatVideo AI is an AI-assisted video creation platform.

A simple user journey is:

```text
User registers
      ↓
Creates a project
      ↓
Gives a topic/story idea
      ↓
AI creates structured scenes
      ↓
User edits scenes
      ↓
System generates voice
      ↓
System renders characters
      ↓
System composes final video
      ↓
User previews/downloads video
```

If the user needs more credits:

```text
Pricing
  ↓
Razorpay Checkout
  ↓
Payment
  ↓
Webhook
  ↓
Credits Added
```

Everything in the project exists to support one of these steps.

---

# 2. Why are there so many technologies?

Different components solve different problems.

| Technology | Why it exists |
|---|---|
| Next.js | Web application framework |
| React | UI components |
| TypeScript | Safer frontend code |
| FastAPI | Backend APIs |
| Python | Backend + AI/media integration |
| PostgreSQL | Permanent data storage |
| Redis | Queue/broker communication |
| Celery | Background processing |
| Docker | Consistent local services |
| Ollama | Local LLM |
| Blender | 3D video rendering |
| FFmpeg | Audio/video composition |
| Razorpay | Payments |
| zrok | Temporary public webhook URL |

Remember this simplified version:

```text
Frontend = what user sees
Backend = business logic
Database = remembers data
Queue = holds long jobs
Worker = executes jobs
Engine = creates media
Payment gateway = collects money
```

---

# 3. Frontend and backend

## Frontend

The frontend normally runs at:

```text
http://localhost:3000
```

It contains pages such as:

- register
- login
- dashboard
- project
- scene editor
- pricing
- account

The frontend should not directly connect to PostgreSQL.

Correct pattern:

```text
Browser
  ↓
FastAPI
  ↓
Database
```

The backend owns validation, security, ownership, credits, billing, and jobs.

---

# 4. What is an API?

Suppose the frontend wants pricing plans.

It calls:

```http
GET /v1/billing/plans
```

The backend returns JSON.

Example:

```json
{
  "billing_mode": "mock",
  "plans": [
    {
      "id": "creator",
      "price_inr": 299
    }
  ]
}
```

An API is simply a contract that allows two software components to communicate.

---

# 5. FastAPI basics

FastAPI is the Python backend framework.

Very simple example:

```python
@app.get("/hello")
def hello():
    return {"message": "Hello"}
```

Calling:

```text
GET /hello
```

returns:

```json
{"message":"Hello"}
```

Real BharatVideo APIs are divided into domains such as:

```text
auth
projects
scenes
media
providers
analytics
billing
```

This is much cleaner than one giant Python file.

---

# 6. Database basics

If a user creates:

```text
Project: AI Bahu Comedy
Language: Hindi
```

we need it to survive server restarts.

So persistent data goes to PostgreSQL.

Typical entities include:

```text
Users
Projects
Scenes
Jobs
Credits
Payments
Subscriptions
```

Conceptually:

```text
User
 ├── Project 1
 │    ├── Scene 1
 │    ├── Scene 2
 │    └── Scene 3
 │
 └── Project 2
      ├── Scene 1
      └── Scene 2
```

---

# 7. Authentication vs authorization

These are different.

**Authentication:** Who are you?

**Authorization:** Are you allowed to access this resource?

Example:

Rohit logs in successfully = authentication.

Rohit tries to open someone else's project and is rejected = authorization.

Simplified token flow:

```text
Email + Password
      ↓
Backend verifies password
      ↓
JWT token
      ↓
Browser sends token on protected requests
      ↓
Backend identifies current user
```

A valid token must still pass project-ownership checks.

---

# 8. Why Redis and Celery?

Rendering can take seconds or minutes.

Bad design:

```text
Browser request
      ↓
FastAPI starts Blender
      ↓
Browser waits until render completes
```

Better design:

```text
Browser
   ↓
FastAPI creates Job
   ↓
Task placed in queue
   ↓
API responds quickly
   ↓
Worker gets task
   ↓
Render happens separately
```

Remember:

```text
Redis = broker/queue communication
Celery = task execution framework
```

---

# 9. Docker networking — very important

Each Compose service runs in a separate container.

Example:

```text
api container
redis container
postgres container
worker container
web container
```

Inside the API container:

```text
localhost
```

means the API container itself.

So this may fail:

```text
redis://localhost:6379
```

while this works:

```text
redis://redis:6379
```

because `redis` is the Compose service hostname.

This single concept explains many Docker bugs.

---

# 10. Docker Compose

Start services:

```bash
docker compose up -d
```

Check:

```bash
docker compose ps
```

API logs:

```bash
docker compose logs -f api
```

Worker logs:

```bash
docker compose logs -f worker
```

Stop without deleting volumes:

```bash
docker compose down
```

Be careful with:

```bash
docker compose down -v
```

because `-v` can delete persistent database volumes.

---

# 11. AI story generation

Example input:

```text
Babuji thinks AI is Guddu's foreign wife.
```

The LLM may create:

```text
Scene 1: Babuji sees AI on the phone
Scene 2: Babuji starts questioning it
Scene 3: Guddu tries to explain
Scene 4: Bittu increases confusion
Scene 5: Punchline/twist
```

Important design lesson:

> Do not let free-form AI text directly control the whole product.

Convert AI output into structured scene data.

Example:

```json
{
  "scene_number": 1,
  "speaker": "Babuji",
  "dialogue": "...",
  "action": "mock_shock"
}
```

Structured data can be validated, stored, edited, regenerated, and tested.

---

# 12. Why scene-based architecture matters

Suppose a video has 12 scenes and only Scene 8 is bad.

Without scene separation you may regenerate the entire video.

With scene architecture:

```text
Project
  ├── Scene 1
  ├── Scene 2
  ├── ...
  └── Scene 12
```

you can regenerate only Scene 8.

Benefits:

- faster iteration
- lower compute cost
- easier debugging
- better user control
- better testing

---

# 13. Provider abstraction

Today the project may use:

```text
Ollama
Blender
```

Tomorrow it may use:

```text
Veo
Runway
another TTS provider
another LLM
```

Do not call one provider directly from every file.

Better mental model:

```text
VideoProvider
   ├── BlenderProvider
   ├── VeoProvider
   └── RunwayProvider
```

The rest of the application depends on a contract instead of one implementation.

This is an important OOP/design principle.

---

# 14. Host engine bridge

The web application runs mainly in Docker, while the existing rendering engine can run on macOS.

Flow:

```text
Docker Worker
    ↓
Host Engine Bridge
    ↓
agentic-content-factory
    ↓
Blender
```

Current host engine location:

```text
/Users/maa/agentic-content-factory
```

Bridge port:

```text
8090
```

This is a useful integration pattern: instead of rewriting a working engine, wrap it behind an adapter/bridge.

---

# 15. Blender's job

Blender handles visual generation such as:

- characters
- position
- movement
- camera
- lighting
- props
- facial states
- mouth shapes
- environment

Current recurring characters include:

```text
Babuji
Guddu
Bittu
```

A scene plan may say:

```text
Speaker: Babuji
Action: mock_shock
Prop: phone
Camera: medium close-up
```

The renderer converts that structured plan into animation.

---

# 16. TTS

TTS means **Text To Speech**.

Input:

```text
Arre Guddu, ee phone mein kaun bahuriya baithi hai?
```

Output:

```text
audio
```

Generated audio has a real duration.

If audio is 4.8 seconds but the visual scene is forced to 3 seconds, quality problems appear:

- cut speech
- unnatural speed
- timing mismatch

So real speech duration should influence scene duration.

---

# 17. Why unwanted silence happened

Imagine:

```text
Actual speech = 3.5 seconds
Forced scene = 6.5 seconds
```

That can create about 3 seconds of dead-air.

Repeated across scenes, the video feels disconnected.

The improved approach uses:

- actual voice length
- small conversational gaps
- reaction pauses only when needed
- ambient continuity
- silence detection

Engineering lesson:

> A temporary safety workaround can later become a product-quality bug.

---

# 18. FFmpeg

FFmpeg is used for media operations such as:

- combining audio/video
- trimming
- encoding
- mixing tracks
- silence analysis
- producing final MP4

Conceptual flow:

```text
Blender video
      +
TTS audio
      +
Captions
      +
Ambient audio
      ↓
FFmpeg
      ↓
final.mp4
```

---

# 19. Billing modes

## Mock mode

```env
BILLING_MODE=mock
```

Useful for:

- automated tests
- frontend development
- credit-flow testing

## Razorpay mode

```env
BILLING_MODE=razorpay
```

Useful for:

- Razorpay Test Mode
- later Razorpay Live Mode

Do not make all automated tests depend on an external payment gateway.

---

# 20. Razorpay flow

Example: user buys Pro.

```text
User selects Pro
      ↓
Frontend requests checkout
      ↓
Backend creates Razorpay order
      ↓
Razorpay Checkout opens
      ↓
User pays
      ↓
Callback returns payment data
      ↓
Backend verifies signature
      ↓
Razorpay webhook arrives
      ↓
Backend verifies webhook
      ↓
Payment confirmed captured
      ↓
Credits added
```

---

# 21. Why webhooks matter

The browser is not a reliable payment source of truth.

It can close, lose network, or be manipulated.

A webhook is server-to-server communication:

```text
Razorpay Server
      ↓
Your Backend
```

That gives the backend an independent payment event.

---

# 22. Why webhook signatures matter

Anybody can send an HTTP request to a public URL.

Without verification an attacker could fake:

```json
{"payment":"captured"}
```

Therefore:

```text
Webhook
   ↓
Verify cryptographic signature
   ↓
Trust event only if valid
```

Never award credits from unverified payment JSON.

---

# 23. Idempotency

Suppose both happen:

```text
Checkout callback
Webhook
```

Without protection:

```text
+800 credits from callback
+800 credits from webhook
= 1600 ❌
```

Correct:

```text
First fulfilment = +800
Repeated same payment = +0
```

This is idempotency.

Simple definition:

> Repeating the same operation must not create duplicate business effects.

---

# 24. Why zrok is used locally

Razorpay cannot call:

```text
http://localhost:8000
```

from the public internet.

zrok temporarily provides:

```text
Internet
   ↓
Public HTTPS URL
   ↓
localhost:8000
```

Example:

```text
https://example.share.zrok.io/v1/billing/webhooks/razorpay
```

Production should use a permanent domain/server instead of a development tunnel.

---

# 25. Environment variables and secrets

Bad:

```python
RAZORPAY_SECRET = "actual-secret"
```

Better:

```python
os.getenv("RAZORPAY_KEY_SECRET")
```

Real values stay in `.env`.

`.env.example` contains names/placeholders, not secrets.

Never commit:

```text
API keys
passwords
JWT secrets
webhook secrets
zrok tokens
database credentials
```

---

# 26. Git basics

Initialize:

```bash
git init
git branch -M main
```

Check:

```bash
git status
```

Stage:

```bash
git add .
```

Commit:

```bash
git commit -m "feat: initial BharatVideo AI v0.8 release"
```

Remote:

```bash
git remote add origin https://github.com/raushan-raj-ai-engineer/BharatVideo-AI.git
```

Push:

```bash
git push -u origin main
```

---

# 27. `.gitignore`

Do not track generated or sensitive files.

Common entries:

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
.DS_Store
```

Before commit:

```bash
git status
git diff
```

Credential check:

```bash
git grep -n "rzp_test_"
git grep -n "rzp_live_"
```

---

# 28. Testing strategy

A mature project uses multiple test levels.

## Unit tests

One small function.

## API tests

Endpoints and validation.

## Integration tests

Multiple services together.

Example:

```text
API → Redis → Worker
```

## Payment tests

Test:

- order creation
- signatures
- webhook validation
- captured status
- idempotency

## Media/render tests

Test:

- duration
- bridge
- action normalization
- audio presence
- silence
- final asset validity

---

# 29. Why tests can fail while app still works

Example:

Real local configuration:

```env
BILLING_MODE=razorpay
```

Old automated test expects:

```env
BILLING_MODE=mock
```

The application may be correct while the test environment is wrong.

Another example:

```text
redis://localhost:6379
```

can be wrong inside a Docker container.

Always ask:

> Is this a code bug, configuration bug, environment bug, or test-data bug?

---

# 30. Useful isolated test command

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

Bridge test:

```bash
/Users/maa/agentic-content-factory/.venv/bin/python \
-m pytest apps/api/tests/test_bridge_duration_autofit.py -q
```

Understand the command:

```text
docker compose exec = run inside container
-e NAME=value       = temporary env override
api                 = target service
python -m pytest    = execute tests
```

---

# 31. Debugging workflow

When something fails:

### Step 1 — Reproduce exactly

Write what you clicked or ran.

### Step 2 — Identify layer

```text
browser
frontend
API
database
Redis
worker
bridge
Blender
payment provider
```

### Step 3 — Check logs

```bash
docker compose logs -f api
```

```bash
docker compose logs -f worker
```

### Step 4 — Test dependency directly

Example:

```bash
curl http://localhost:8000/v1/billing/plans
```

### Step 5 — Fix smallest responsible layer

Avoid changing unrelated modules.

### Step 6 — Add regression test

A bug without a test can return later.

---

# 32. How to read the codebase

Do not read every file alphabetically.

Trace one user action.

Example:

```text
Click Buy Pro
```

Then follow:

```text
Frontend button
 ↓
API request
 ↓
FastAPI route
 ↓
Service/business logic
 ↓
Database/payment call
 ↓
Response
```

This is much easier for a fresher.

---

# 33. 14-day learning plan

## Day 1 — Run the project

Learn Docker services, ports, logs.

Goal: Web and API working.

## Day 2 — Frontend basics

Learn React component, state, props, API calls, TypeScript interfaces.

## Day 3 — FastAPI

Learn GET, POST, request body, response, status code.

## Day 4 — Database

Learn table, primary key, foreign key, SQLAlchemy session/model.

## Day 5 — Authentication

Learn password hashing, JWT, current user, protected route.

## Day 6 — Projects and scenes

Understand scene-based architecture and regeneration.

## Day 7 — Redis + Celery

Trace one background media job.

## Day 8 — Host bridge

Understand Docker-to-macOS render communication.

## Day 9 — Blender + FFmpeg

Trace scene data to final MP4.

## Day 10 — TTS and timing

Understand speech duration, transitions, silence.

## Day 11 — Billing

Understand orders, callbacks, signatures, webhooks.

## Day 12 — Idempotency

Explain why credits are not duplicated.

## Day 13 — Tests

Run API/payment/bridge tests and diagnose one broken environment variable.

## Day 14 — First contribution

Make one small feature/fix/test and commit it on a feature branch.

---

# 34. Good fresher improvements

Start small:

- better error message
- loading state
- empty-state UI
- input validation
- one API test
- one billing regression test
- one accessibility improvement
- one new language option
- documentation
- better logging

Do not start by rewriting the architecture.

---

# 35. Intermediate improvements

After understanding the flow:

- dedicated `.env.test`
- pytest/dev dependency management
- CI/CD
- database migrations
- render job cancellation
- retry policies
- cloud storage abstraction
- email verification
- forgot password
- refresh-token strategy
- rate limiting
- structured analytics
- render-cost tracking
- automatic credit refund on render failure

---

# 36. Advanced improvements

For experienced contributors:

- cloud render workers
- GPU-aware scheduling
- multiple worker queues
- priority jobs
- Veo/Runway adapters
- cost-aware provider routing
- phoneme/viseme lip sync
- reusable animation library
- better character rigs
- scene continuity scoring
- observability and tracing
- autoscaling
- CDN
- subscription renewals
- invoicing/tax integration
- enterprise workspaces

---

# 37. Security checklist

Never commit:

```text
passwords
API keys
webhook secrets
JWT secrets
database passwords
access tokens
```

Validate:

```text
input
ownership
payment signature
webhook signature
file size/type
```

Production should consider:

- HTTPS
- strict CORS
- token expiry
- rate limits
- secret rotation
- backups
- audit logs
- dependency scanning
- secure object-storage URLs

---

# 38. Performance mindset

A normal DB request may take milliseconds.

A Blender render may take seconds/minutes.

So render requests should behave like:

```text
Request job
   ↓
Return job ID
   ↓
Process asynchronously
   ↓
Track status
   ↓
Return final asset
```

Do not keep an HTTP request open for the entire render if it can be avoided.

---

# 39. Cost mindset

Local development can be almost free because many components run locally:

```text
Blender
FFmpeg
Ollama
PostgreSQL
Redis
Razorpay Test Mode
```

Production may add cost for:

- servers
- storage
- bandwidth
- commercial TTS
- external AI video APIs
- monitoring
- email
- managed database
- payment processing

Over time track:

```text
job
provider
credits used
estimated cost
actual cost
```

---

# 40. Product-quality mindset

A generated MP4 is not automatically a good video.

Technically:

```text
File exists = PASS
```

But user experience may still fail because:

- characters do not move naturally
- voice sounds robotic
- silence is too long
- props are missing
- camera repeats too much
- mouth timing is wrong

So quality requires both automated checks and human review.

Useful future quality gates:

- silence duration
- audio clipping
- missing character
- missing voice
- unsupported action
- subtitle overflow
- repetitive camera
- low motion
- lip-sync drift

---

# 41. AI testing mindset

Normal deterministic code:

```text
2 + 2 = 4
```

AI output may vary.

Therefore combine:

## Deterministic tests

```text
HTTP status
schema
file exists
duration > 0
signature valid
credits added once
```

## Quality evaluation

```text
story relevance
dialogue naturalness
scene continuity
voice quality
visual consistency
```

## Human evaluation

Creative output still needs human judgement.

---

# 42. Full render request trace

When user clicks Generate Video:

```text
1. React handler runs
2. Frontend calls API
3. FastAPI authenticates user
4. Project ownership is checked
5. Render job is created
6. Job is stored
7. Task is sent to Redis
8. Celery worker receives it
9. Render plan is prepared
10. Host bridge receives request
11. TTS generates voice
12. Timing is calculated
13. Blender renders scene
14. FFmpeg composes media
15. Result is returned/stored
16. Job becomes completed
17. Frontend reads job status
18. User sees final video
```

Debugging question:

> At which numbered step did reality stop matching expectation?

---

# 43. Full payment trace

```text
1. User is logged in
2. User selects plan
3. Backend validates plan
4. Backend creates Razorpay order
5. Checkout opens
6. Test payment completes
7. Callback returns payment data
8. Backend verifies callback signature
9. Razorpay sends webhook
10. Backend verifies webhook signature
11. Captured/paid state is confirmed
12. Backend checks previous fulfilment
13. Credits are added exactly once
14. Payment history is recorded
15. Account page shows new credits
```

Never jump from browser success directly to credit fulfilment without verification.

---

# 44. Documentation rule

When adding a feature, update the relevant documentation.

A good feature document should answer:

1. What is it?
2. Why does it exist?
3. How do I run it?
4. Which environment variables are required?
5. How do I test it?
6. What can fail?
7. Is it local-only or production-ready?

---

# 45. Code review checklist

Before pushing:

```text
[ ] Feature works
[ ] Tests pass
[ ] No secret committed
[ ] No generated media committed
[ ] Error handling exists
[ ] Env variables documented
[ ] Ownership/security preserved
[ ] Billing remains idempotent
[ ] Docs updated when needed
```

Commands:

```bash
git status
git diff
```

---

# 46. Good commit messages

Good:

```text
feat: add render job cancellation
fix: prevent duplicate credit fulfilment
test: cover invalid webhook signature
docs: add Razorpay local setup
refactor: isolate video provider adapter
```

Weak:

```text
changes
update
final
fix stuff
```

---

# 47. Questions every fresher should answer

1. Why does BharatVideo use FastAPI?
2. Why doesn't the frontend access PostgreSQL directly?
3. What does Redis do?
4. What does Celery do?
5. Why is Blender behind a bridge?
6. What is a scene?
7. Why regenerate one scene instead of the whole video?
8. What is TTS?
9. Why does speech duration affect visual timing?
10. What is a webhook?
11. Why verify webhook signatures?
12. What is idempotency?
13. Why must `.env` not be committed?
14. Why is `localhost` different inside Docker?
15. Why should rendering be asynchronous?
16. What is provider abstraction?
17. What is JWT?
18. Authentication vs authorization?
19. Why Test Mode before Razorpay Live?
20. Why is a generated MP4 not enough to claim good video quality?

If you can explain these in your own words, you understand the core system.

---

# 48. Practice tasks

## Task 1 — Version API

Create:

```text
GET /v1/system/version
```

Response:

```json
{"version":"0.8.0"}
```

Learn FastAPI route + test.

## Task 2 — Credits card

Show current credits on frontend.

Learn API call + state + TypeScript type.

## Task 3 — Prevent negative credits

Add a test/business rule.

## Task 4 — New render action

Add one normalized scene action and renderer behavior.

## Task 5 — Job failure UI

Display a friendly failed-job state and retry guidance.

---

# 49. Interview explanation

A concise interview answer:

> BharatVideo AI is a scene-based AI video generation platform. The frontend uses Next.js and TypeScript, while FastAPI provides authentication, project, scene, billing, and job APIs. PostgreSQL stores persistent data and Redis/Celery handles long-running media work asynchronously. The application uses a host bridge to connect with an existing Blender-based rendering engine that generates 3D scenes, TTS audio, and FFmpeg-composed video. The platform also supports credit-based pricing and Razorpay payments with signature validation, webhooks, and idempotent fulfilment. Rendering and AI providers are kept behind adapter boundaries so additional providers can be added later.

---

# 50. Final mental model

Whenever the project feels too large, return to this:

```text
USER
 ↓
WEB
 ↓
API
 ├────────────→ DATABASE
 │
 ├────────────→ PAYMENT
 │
 └→ REDIS
      ↓
    WORKER
      ↓
    BRIDGE
      ↓
 AI / TTS / BLENDER / FFMPEG
      ↓
 FINAL VIDEO
```

Understand one arrow at a time.

That is how a fresher can understand and safely improve a large system.

---

# Appendix A — Useful commands

Start:

```bash
docker compose up -d
```

Status:

```bash
docker compose ps
```

API logs:

```bash
docker compose logs -f api
```

Worker logs:

```bash
docker compose logs -f worker
```

Billing plans:

```bash
curl http://localhost:8000/v1/billing/plans
```

API docs:

```text
http://localhost:8000/docs
```

Frontend:

```text
http://localhost:3000
```

Temporary public webhook tunnel:

```bash
zrok share public http://localhost:8000
```

Git:

```bash
git status
git diff
git log --oneline -5
```

---

# Appendix B — Ports

| Port | Service |
|---:|---|
| 3000 | Next.js web |
| 8000 | FastAPI |
| 5432 | PostgreSQL |
| 6379 | Redis |
| 8090 | Host render bridge |

---

# Appendix C — Before public launch

```text
[ ] permanent domain
[ ] HTTPS
[ ] production deployment
[ ] database backups
[ ] object storage
[ ] monitoring
[ ] rate limiting
[ ] production secrets
[ ] production TTS/licensing
[ ] Razorpay Live activation
[ ] live webhook
[ ] refund/cancellation handling
[ ] Terms of Service
[ ] Privacy Policy
[ ] support process
[ ] render-failure compensation
[ ] load testing
[ ] security review
```

---

# Closing note

BharatVideo AI combines web development, distributed systems, AI, video engineering, automation, and billing.

Do not try to learn everything at once.

Learn one responsibility at a time:

```text
one request
one API
one queue
one job
one scene
one payment
one test
```

That is the fastest way to become confident enough to improve the project safely.
