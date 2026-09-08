# BharatVideo AI V0.8 — Razorpay Payments

V0.8 supports the application payment path for **UPI Intent/QR, cards, and net banking** through Razorpay Standard Checkout. The exact methods shown to a customer depend on what is enabled on the merchant's Razorpay account.

## Safety model

1. BharatVideo creates a Razorpay Order on the API server. The Razorpay key secret never goes to the browser.
2. The browser opens Razorpay Standard Checkout.
3. The Checkout callback is verified using `razorpay_order_id`, `razorpay_payment_id`, and `razorpay_signature` on the BharatVideo API.
4. After signature verification, BharatVideo fetches the payment from Razorpay and requires `status=captured`, matching order id, INR currency, and exact amount before granting plan credits.
5. Razorpay webhooks are verified over the **raw request body** using `RAZORPAY_WEBHOOK_SECRET` and `X-Razorpay-Signature`.
6. `X-Razorpay-Event-Id` is persisted for webhook deduplication.
7. `PaymentFulfillment.payment_order_id` is unique, so a browser callback plus repeated webhooks cannot grant the same plan credits twice.
8. `payment.authorized` is recorded but does not grant credits. `payment.captured` or `order.paid` can fulfill the order.
9. `payment.failed` is retained in payment history.

## UPI note (2026)

Do not build a new manual VPA/UPI-ID Collect form. Razorpay's current documentation states that UPI Collect is deprecated effective 28 February 2026 for general new integrations. Use Razorpay Checkout's **UPI Intent or UPI QR** path.

## Configure Test mode first

In `.env`:

```env
BILLING_MODE=razorpay
RAZORPAY_KEY_ID=rzp_test_xxxxxxxxx
RAZORPAY_KEY_SECRET=xxxxxxxxx
RAZORPAY_WEBHOOK_SECRET=choose-a-separate-random-webhook-secret
# Optional extra guard:
RAZORPAY_EXPECTED_ACCOUNT_ID=
```

Restart API + web after changing `.env`.

In Razorpay Dashboard Test mode, create a webhook pointing to:

```text
https://YOUR-PUBLIC-API/v1/billing/webhooks/razorpay
```

Subscribe at minimum to:

- `payment.authorized`
- `payment.captured`
- `payment.failed`
- `order.paid`

Use the same webhook secret in the Dashboard and `RAZORPAY_WEBHOOK_SECRET`.

For local development, Razorpay cannot call `localhost`; expose only the API webhook endpoint through an appropriate staging/public tunnel or deploy a staging API.

## Live-mode checklist

- Complete Razorpay account/KYC/activation requirements.
- Replace test keys with live keys.
- Create a Live-mode webhook and use a separate Live webhook secret.
- Confirm automatic/manual capture configuration and only fulfill captured payments.
- Keep `AUTH_SECRET`, `RAZORPAY_KEY_SECRET`, and `RAZORPAY_WEBHOOK_SECRET` out of Git.
- Run a small real payment and refund/reconciliation test before public launch.

Official references:
- https://razorpay.com/docs/payments/payment-gateway/web-integration/standard/integration-steps/
- https://razorpay.com/docs/webhooks/validate-test/
- https://razorpay.com/docs/webhooks/orders/
- https://razorpay.com/docs/payments/payment-methods/upi/
