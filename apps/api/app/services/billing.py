from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone

import httpx
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import (
    PaymentFulfillment,
    PaymentOrder,
    PaymentTransaction,
    PaymentWebhookEvent,
    Subscription,
    User,
)
from app.services.security import add_credits

def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


PLANS = {
    "free": {"id": "free", "name": "Free", "price_inr": 0, "credits": 30, "tagline": "Try the studio", "features": ["30 signup credits", "Draft + 3D preview", "720p preview", "Watermark-ready"]},
    "creator": {"id": "creator", "name": "Creator", "price_inr": 299, "credits": 250, "tagline": "For regular creators", "features": ["250 credits", "1080p exports", "Neural Hindi voice", "Scene regenerate", "No app watermark"]},
    "pro": {"id": "pro", "name": "Pro", "price_inr": 799, "credits": 800, "tagline": "Best value", "popular": True, "features": ["800 credits", "Long-form 3D video", "Regional language profiles", "Priority renders", "Premium provider-ready"]},
    "business": {"id": "business", "name": "Business", "price_inr": 1499, "credits": 1800, "tagline": "For brands & agencies", "features": ["1,800 credits", "Commercial projects", "Brand-ready workflow", "Multiple campaigns", "Priority support"]},
}


def public_plans() -> list[dict]:
    return list(PLANS.values())


def plan(plan_id: str) -> dict:
    item = PLANS.get(plan_id)
    if not item or plan_id == "free":
        raise HTTPException(400, "Paid plan not found")
    return item


def _record_transaction(
    db: Session,
    *,
    order: PaymentOrder,
    payment_id: str | None,
    status: str,
    method: str | None = None,
    amount_paise: int | None = None,
    currency: str = "INR",
    error_code: str | None = None,
    error_description: str | None = None,
) -> PaymentTransaction | None:
    if not payment_id:
        return None
    row = db.scalar(
        select(PaymentTransaction).where(
            PaymentTransaction.provider == order.provider,
            PaymentTransaction.provider_payment_id == payment_id,
        )
    )
    if row is None:
        row = PaymentTransaction(
            user_id=order.user_id,
            payment_order_id=order.id,
            provider=order.provider,
            provider_order_id=order.provider_order_id,
            provider_payment_id=payment_id,
        )
        db.add(row)
    row.status = status
    row.method = method or row.method
    row.amount_paise = int(amount_paise if amount_paise is not None else order.amount_paise)
    row.currency = currency or "INR"
    row.error_code = error_code
    row.error_description = error_description
    row.updated_at = _utcnow()
    return row


def create_checkout(db: Session, user: User, plan_id: str) -> dict:
    settings = get_settings()
    item = plan(plan_id)
    amount_paise = int(item["price_inr"] * 100)
    order = PaymentOrder(
        user_id=user.id,
        plan_id=plan_id,
        amount_paise=amount_paise,
        credits=item["credits"],
        provider=settings.billing_mode,
    )
    db.add(order)
    db.flush()

    if settings.billing_mode == "razorpay":
        if not settings.razorpay_key_id or not settings.razorpay_key_secret:
            db.rollback()
            raise HTTPException(503, "Razorpay is selected but API keys are missing")
        try:
            with httpx.Client(timeout=20.0) as client:
                response = client.post(
                    "https://api.razorpay.com/v1/orders",
                    auth=(settings.razorpay_key_id, settings.razorpay_key_secret),
                    json={
                        "amount": amount_paise,
                        "currency": "INR",
                        "receipt": f"bv_{order.id[:18]}",
                        "notes": {"user_id": user.id, "plan_id": plan_id, "internal_order_id": order.id},
                    },
                )
                response.raise_for_status()
                data = response.json()
        except Exception as exc:
            db.rollback()
            raise HTTPException(502, f"Razorpay order creation failed: {exc}") from exc
        order.provider_order_id = data["id"]
        db.commit()
        return {
            "mode": "razorpay",
            "order_id": order.id,
            "provider_order_id": order.provider_order_id,
            "key_id": settings.razorpay_key_id,
            "amount": amount_paise,
            "currency": "INR",
            "plan": item,
            "checkout": {
                "upi": "intent_or_qr",
                "cards": True,
                "netbanking": True,
                "note": "Available methods depend on methods enabled in your Razorpay account.",
            },
        }

    order.provider_order_id = f"mock_{order.id}"
    db.commit()
    return {
        "mode": "mock",
        "order_id": order.id,
        "provider_order_id": order.provider_order_id,
        "amount": amount_paise,
        "currency": "INR",
        "plan": item,
    }


def _activate_locked(
    db: Session,
    *,
    order_id: str,
    provider_payment_id: str | None = None,
    method: str | None = None,
    source: str = "checkout",
) -> dict:
    """Exactly-once grant, safe against client callback + duplicate webhooks."""
    order = db.scalar(select(PaymentOrder).where(PaymentOrder.id == order_id).with_for_update())
    if not order:
        raise HTTPException(404, "Order not found")
    user = db.get(User, order.user_id)
    if not user:
        raise HTTPException(404, "User not found")

    existing = db.scalar(select(PaymentFulfillment).where(PaymentFulfillment.payment_order_id == order.id))
    if existing or order.status == "paid":
        if provider_payment_id:
            _record_transaction(db, order=order, payment_id=provider_payment_id, status="captured", method=method)
            db.commit()
        return {"status": "already_paid", "plan_id": user.plan_id, "credits_added": 0}

    item = plan(order.plan_id)
    fulfillment = PaymentFulfillment(
        payment_order_id=order.id,
        user_id=user.id,
        provider_payment_id=provider_payment_id,
    )
    db.add(fulfillment)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        return {"status": "already_paid", "plan_id": user.plan_id, "credits_added": 0}

    order.status = "paid"
    order.provider_payment_id = provider_payment_id or order.provider_payment_id
    order.completed_at = _utcnow()
    user.plan_id = order.plan_id
    db.add(
        Subscription(
            user_id=user.id,
            plan_id=order.plan_id,
            status="active",
            provider=order.provider,
            provider_reference=provider_payment_id or order.provider_order_id,
            expires_at=_utcnow() + timedelta(days=30),
        )
    )
    add_credits(db, user.id, int(item["credits"]), "PURCHASE", f"{item['name']} plan credits", order.id)
    if provider_payment_id:
        _record_transaction(db, order=order, payment_id=provider_payment_id, status="captured", method=method)
    db.commit()
    return {
        "status": "paid",
        "plan_id": user.plan_id,
        "credits_added": item["credits"],
        "source": source,
    }


def complete_mock(db: Session, user: User, order_id: str) -> dict:
    settings = get_settings()
    if settings.billing_mode != "mock":
        raise HTTPException(400, "Mock checkout is disabled")
    order = db.get(PaymentOrder, order_id)
    if not order or order.user_id != user.id:
        raise HTTPException(404, "Order not found")
    return _activate_locked(db, order_id=order.id, provider_payment_id=f"mockpay_{order.id}", method="mock", source="mock")


def _fetch_razorpay_payment(payment_id: str) -> dict:
    settings = get_settings()
    try:
        with httpx.Client(timeout=20.0) as client:
            response = client.get(
                f"https://api.razorpay.com/v1/payments/{payment_id}",
                auth=(settings.razorpay_key_id, settings.razorpay_key_secret),
            )
            response.raise_for_status()
            return response.json()
    except Exception as exc:
        raise HTTPException(502, f"Unable to confirm Razorpay payment status: {exc}") from exc


def verify_razorpay(
    db: Session,
    user: User,
    *,
    order_id: str,
    razorpay_order_id: str,
    payment_id: str,
    signature: str,
) -> dict:
    settings = get_settings()
    if settings.billing_mode != "razorpay":
        raise HTTPException(400, "Razorpay checkout is disabled")
    if not settings.razorpay_key_secret:
        raise HTTPException(503, "Razorpay key secret is missing")

    order = db.get(PaymentOrder, order_id)
    if not order or order.user_id != user.id:
        raise HTTPException(404, "Order not found")
    if order.provider_order_id != razorpay_order_id:
        raise HTTPException(400, "Order mismatch")

    expected = hmac.new(
        settings.razorpay_key_secret.encode(),
        f"{razorpay_order_id}|{payment_id}".encode(),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise HTTPException(400, "Payment signature verification failed")

    payment = _fetch_razorpay_payment(payment_id)
    if payment.get("order_id") != razorpay_order_id:
        raise HTTPException(400, "Payment belongs to a different order")
    if int(payment.get("amount", -1)) != int(order.amount_paise) or payment.get("currency") != "INR":
        raise HTTPException(400, "Payment amount or currency mismatch")
    status = str(payment.get("status") or "")
    _record_transaction(
        db,
        order=order,
        payment_id=payment_id,
        status=status or "unknown",
        method=payment.get("method"),
        amount_paise=int(payment.get("amount") or 0),
        currency=str(payment.get("currency") or "INR"),
    )
    if status != "captured":
        db.commit()
        raise HTTPException(409, f"Payment is {status or 'not captured'}; entitlement will activate after capture/webhook")
    return _activate_locked(
        db,
        order_id=order.id,
        provider_payment_id=payment_id,
        method=payment.get("method"),
        source="checkout_verify",
    )


def _webhook_signature_ok(raw_body: bytes, signature: str, secret: str) -> bool:
    expected = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature or "")


def _extract_webhook_entities(payload: dict) -> tuple[dict, dict]:
    p = ((payload.get("payload") or {}).get("payment") or {}).get("entity") or {}
    o = ((payload.get("payload") or {}).get("order") or {}).get("entity") or {}
    return p, o


def process_razorpay_webhook(
    db: Session,
    *,
    raw_body: bytes,
    signature: str,
    event_id: str | None,
) -> dict:
    settings = get_settings()
    secret = settings.razorpay_webhook_secret
    if not secret:
        raise HTTPException(503, "Razorpay webhook secret is not configured")
    if not _webhook_signature_ok(raw_body, signature, secret):
        raise HTTPException(400, "Invalid Razorpay webhook signature")

    digest = hashlib.sha256(raw_body).hexdigest()
    dedupe_id = event_id or f"sha256:{digest}"
    existing = db.scalar(
        select(PaymentWebhookEvent).where(
            PaymentWebhookEvent.provider == "razorpay",
            PaymentWebhookEvent.provider_event_id == dedupe_id,
        )
    )
    if existing:
        return {"status": "duplicate", "event_id": dedupe_id, "event_type": existing.event_type}

    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except Exception as exc:
        raise HTTPException(400, "Invalid webhook JSON") from exc

    if settings.razorpay_expected_account_id and payload.get("account_id") != settings.razorpay_expected_account_id:
        raise HTTPException(400, "Webhook account mismatch")

    event_type = str(payload.get("event") or "unknown")
    event = PaymentWebhookEvent(
        provider="razorpay",
        provider_event_id=dedupe_id,
        event_type=event_type,
        payload_sha256=digest,
        status="received",
    )
    db.add(event)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        return {"status": "duplicate", "event_id": dedupe_id, "event_type": event_type}

    payment, provider_order = _extract_webhook_entities(payload)
    provider_order_id = payment.get("order_id") or provider_order.get("id")
    order = db.scalar(select(PaymentOrder).where(PaymentOrder.provider_order_id == provider_order_id)) if provider_order_id else None

    if not order:
        event.status = "ignored"
        event.error = "No matching internal order"
        event.processed_at = _utcnow()
        db.commit()
        return {"status": "ignored", "event_type": event_type, "event_id": dedupe_id}

    payment_id = payment.get("id")
    method = payment.get("method")
    amount = int(payment.get("amount") or provider_order.get("amount_paid") or 0)
    currency = str(payment.get("currency") or provider_order.get("currency") or "INR")

    if payment_id:
        _record_transaction(
            db,
            order=order,
            payment_id=payment_id,
            status=str(payment.get("status") or event_type.split(".")[-1]),
            method=method,
            amount_paise=amount,
            currency=currency,
            error_code=payment.get("error_code"),
            error_description=payment.get("error_description"),
        )

    if event_type in {"payment.captured", "order.paid"}:
        expected_amount = int(order.amount_paise)
        if amount and amount != expected_amount:
            event.status = "rejected"
            event.error = f"Amount mismatch: {amount} != {expected_amount}"
            event.processed_at = _utcnow()
            db.commit()
            raise HTTPException(400, "Webhook payment amount mismatch")
        if currency != "INR":
            event.status = "rejected"
            event.error = f"Currency mismatch: {currency}"
            event.processed_at = _utcnow()
            db.commit()
            raise HTTPException(400, "Webhook payment currency mismatch")
        result = _activate_locked(
            db,
            order_id=order.id,
            provider_payment_id=payment_id,
            method=method,
            source="webhook",
        )
        # _activate_locked commits, so reattach/reload event before final status update.
        event = db.get(PaymentWebhookEvent, event.id)
        event.status = "processed"
        event.processed_at = _utcnow()
        db.commit()
        return {**result, "event_type": event_type, "event_id": dedupe_id}

    if event_type == "payment.failed":
        if order.status != "paid":
            order.status = "failed"
        event.status = "processed"
    elif event_type == "payment.authorized":
        if order.status != "paid":
            order.status = "authorized"
        event.status = "processed"
    else:
        event.status = "ignored"
    event.processed_at = _utcnow()
    db.commit()
    return {"status": event.status, "event_type": event_type, "event_id": dedupe_id}
