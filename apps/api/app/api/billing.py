from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.models import CreditLedger, PaymentOrder, PaymentTransaction, User
from app.schemas.auth import CheckoutRequest, MockCompleteRequest, VerifyPaymentRequest
from app.services.billing import (
    complete_mock,
    create_checkout,
    process_razorpay_webhook,
    public_plans,
    verify_razorpay,
)
from app.services.security import credit_balance, get_current_user

router = APIRouter(prefix="/v1/billing", tags=["billing"])


@router.get("/plans")
def plans():
    settings = get_settings()
    return {
        "billing_mode": settings.billing_mode,
        "plans": public_plans(),
        "payment_methods": ["upi_intent_or_qr", "card", "netbanking"] if settings.billing_mode == "razorpay" else ["mock"],
    }


@router.get("/account")
def account(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    ledger = list(db.scalars(select(CreditLedger).where(CreditLedger.user_id == user.id).order_by(CreditLedger.created_at.desc()).limit(30)).all())
    orders = list(db.scalars(select(PaymentOrder).where(PaymentOrder.user_id == user.id).order_by(PaymentOrder.created_at.desc()).limit(20)).all())
    txns = list(db.scalars(select(PaymentTransaction).where(PaymentTransaction.user_id == user.id).order_by(PaymentTransaction.created_at.desc()).limit(30)).all())
    return {
        "user": {"id": user.id, "name": user.name, "email": user.email, "plan_id": user.plan_id},
        "credits": credit_balance(db, user.id),
        "ledger": [{"id": x.id, "amount": x.amount, "kind": x.kind, "description": x.description, "created_at": x.created_at.isoformat()} for x in ledger],
        "orders": [{"id": x.id, "plan_id": x.plan_id, "status": x.status, "amount_paise": x.amount_paise, "provider": x.provider, "created_at": x.created_at.isoformat(), "completed_at": x.completed_at.isoformat() if x.completed_at else None} for x in orders],
        "payments": [{"id": x.id, "order_id": x.payment_order_id, "provider_payment_id": x.provider_payment_id, "status": x.status, "method": x.method, "amount_paise": x.amount_paise, "currency": x.currency, "error_description": x.error_description, "created_at": x.created_at.isoformat()} for x in txns],
    }


@router.post("/checkout")
def checkout(payload: CheckoutRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return create_checkout(db, user, payload.plan_id)


@router.post("/mock-complete")
def mock_complete(payload: MockCompleteRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return complete_mock(db, user, payload.order_id)


@router.post("/verify")
def verify(payload: VerifyPaymentRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return verify_razorpay(
        db,
        user,
        order_id=payload.order_id,
        razorpay_order_id=payload.razorpay_order_id,
        payment_id=payload.razorpay_payment_id,
        signature=payload.razorpay_signature,
    )


@router.post("/webhooks/razorpay")
async def razorpay_webhook(
    request: Request,
    x_razorpay_signature: str = Header(default=""),
    x_razorpay_event_id: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    # IMPORTANT: verify the signature over the raw bytes before JSON parsing.
    raw = await request.body()
    return process_razorpay_webhook(
        db,
        raw_body=raw,
        signature=x_razorpay_signature,
        event_id=x_razorpay_event_id,
    )
