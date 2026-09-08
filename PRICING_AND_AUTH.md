# V0.8 Auth, Pricing and Payments

## Plans
- Free — ₹0 / 30 signup credits.
- Creator — ₹299 / 250 credits.
- Pro — ₹799 / 800 credits.
- Business — ₹1,499 / 1,800 credits.

These MVP paid plans are 30-day credit packs; they are not automatic recurring subscriptions yet.

## Authentication
- Email/password registration and login.
- Passwords are PBKDF2-SHA256 salted hashes.
- Project access is account-scoped.
- First registered account can claim legacy projects created before authentication was added.

Before public launch, use HTTPS, replace `AUTH_SECRET`, and consider moving browser sessions from localStorage bearer tokens to secure HttpOnly cookies as an additional production-hardening step.

## Payments
- Mock billing remains default for development.
- Razorpay integration supports server-created orders and Standard Checkout.
- UPI uses Intent/QR rather than a new manual UPI Collect form.
- Cards and netbanking appear according to methods enabled in the Razorpay merchant account.
- Server verifies Checkout signature and provider captured status.
- Webhook signature uses a separate webhook secret and raw request bytes.
- Event-id dedupe + unique fulfillment record prevents duplicate credit grants.

See `PAYMENTS_V0_8.md` for setup.
