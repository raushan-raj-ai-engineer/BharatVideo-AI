# BharatVideo AI V0.7 validation

- Existing + new backend tests: **21/21 PASS**.
- Includes registration/login, signup credits, mock plan checkout, project isolation and 3-character/story-prop render-plan tests.
- Python compileall: PASS.
- TS/TSX syntax transpile validation: PASS (10 source files, 0 syntax errors at validation time).
- Full frontend dependency install/typecheck could not be completed in the isolated build environment because package-network access timed out. Docker on the target Mac installs the pinned Next/React/TypeScript dependencies during `docker compose build`.
- V0.7 installer shell syntax: PASS.
- Installer simulation over a V0.6-like app + full V6.4 engine tree: PASS when CI explicitly skips network-only TTS installation; production install checks for already-installed `edge-tts` first and installs it only when missing.
- Active renderer checksum/import-path verification and exact V6.6 3.59s/3.00s timing regression remain preserved.
- Database compatibility: new tables only (`users`, `project_owners`, `credit_ledger`, `subscriptions`, `payment_orders`). Existing project tables are not destructively migrated.
