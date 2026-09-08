import hashlib
import hmac
import json

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.main import app
from app.models import PaymentFulfillment, PaymentOrder, PaymentTransaction, PaymentWebhookEvent, User
import app.services.billing as billing_service

client = TestClient(app)


def register(email: str):
    r = client.post('/v1/auth/register', json={'name':'Payment Tester','email':email,'password':'strongpass123'})
    assert r.status_code == 201
    return r.json()


def make_order(user_id: str, *, provider_order_id='order_test_v08', plan_id='creator') -> str:
    db = SessionLocal()
    try:
        order = PaymentOrder(
            user_id=user_id,
            plan_id=plan_id,
            amount_paise=29900,
            credits=250,
            provider='razorpay',
            provider_order_id=provider_order_id,
            status='created',
        )
        db.add(order); db.commit(); db.refresh(order)
        return order.id
    finally:
        db.close()


def test_razorpay_webhook_captured_is_idempotent_and_records_method():
    body = register('webhook-v08@example.com')
    uid = body['user']['id']; token = body['token']
    internal_order_id = make_order(uid, provider_order_id='order_webhook_1')
    before = client.get('/v1/billing/account', headers={'Authorization':f'Bearer {token}'}).json()['credits']

    payload = {
        'entity':'event', 'account_id':'acc_test', 'event':'payment.captured',
        'payload': {'payment': {'entity': {
            'id':'pay_webhook_1', 'order_id':'order_webhook_1', 'amount':29900,
            'currency':'INR', 'status':'captured', 'method':'upi'
        }}}
    }
    raw = json.dumps(payload, separators=(',', ':')).encode()
    signature = hmac.new(b'test-webhook-secret', raw, hashlib.sha256).hexdigest()
    headers = {'X-Razorpay-Signature':signature, 'X-Razorpay-Event-Id':'evt_v08_1', 'Content-Type':'application/json'}

    first = client.post('/v1/billing/webhooks/razorpay', content=raw, headers=headers)
    assert first.status_code == 200, first.text
    assert first.json()['status'] == 'paid'
    after = client.get('/v1/billing/account', headers={'Authorization':f'Bearer {token}'}).json()
    assert after['credits'] - before == 250
    assert any(p['method'] == 'upi' and p['status'] == 'captured' for p in after['payments'])

    second = client.post('/v1/billing/webhooks/razorpay', content=raw, headers=headers)
    assert second.status_code == 200
    assert second.json()['status'] == 'duplicate'
    final = client.get('/v1/billing/account', headers={'Authorization':f'Bearer {token}'}).json()['credits']
    assert final == after['credits']

    db = SessionLocal()
    try:
        assert db.scalar(select(PaymentFulfillment).where(PaymentFulfillment.payment_order_id == internal_order_id)) is not None
        assert len(list(db.scalars(select(PaymentWebhookEvent).where(PaymentWebhookEvent.provider_event_id == 'evt_v08_1')).all())) == 1
        assert len(list(db.scalars(select(PaymentTransaction).where(PaymentTransaction.provider_payment_id == 'pay_webhook_1')).all())) == 1
    finally:
        db.close()


def test_razorpay_webhook_rejects_bad_signature():
    body = register('bad-webhook-v08@example.com')
    make_order(body['user']['id'], provider_order_id='order_bad_sig')
    payload = {'entity':'event','event':'payment.captured','payload':{'payment':{'entity':{'id':'pay_bad_sig','order_id':'order_bad_sig','amount':29900,'currency':'INR','status':'captured','method':'card'}}}}
    raw = json.dumps(payload, separators=(',', ':')).encode()
    r = client.post('/v1/billing/webhooks/razorpay', content=raw, headers={'X-Razorpay-Signature':'wrong','X-Razorpay-Event-Id':'evt_bad_sig','Content-Type':'application/json'})
    assert r.status_code == 400


def test_checkout_verify_requires_captured_provider_status(monkeypatch):
    body = register('verify-v08@example.com')
    uid=body['user']['id']; token=body['token']
    internal_order_id=make_order(uid, provider_order_id='order_verify_v08')
    settings=get_settings(); old_mode=settings.billing_mode; old_secret=settings.razorpay_key_secret
    settings.billing_mode='razorpay'; settings.razorpay_key_secret='test-key-secret'
    payment_id='pay_verify_v08'
    signature=hmac.new(b'test-key-secret', f'order_verify_v08|{payment_id}'.encode(), hashlib.sha256).hexdigest()
    monkeypatch.setattr(billing_service, '_fetch_razorpay_payment', lambda _: {
        'id':payment_id,'order_id':'order_verify_v08','amount':29900,'currency':'INR','status':'authorized','method':'card'
    })
    try:
        r=client.post('/v1/billing/verify', headers={'Authorization':f'Bearer {token}'}, json={
            'order_id':internal_order_id,'razorpay_order_id':'order_verify_v08','razorpay_payment_id':payment_id,'razorpay_signature':signature
        })
        assert r.status_code == 409
        db=SessionLocal()
        try:
            order=db.get(PaymentOrder,internal_order_id); assert order.status != 'paid'
            assert db.scalar(select(PaymentFulfillment).where(PaymentFulfillment.payment_order_id==internal_order_id)) is None
        finally: db.close()
    finally:
        settings.billing_mode=old_mode; settings.razorpay_key_secret=old_secret


def test_checkout_verify_captured_fulfils_exactly_once(monkeypatch):
    body = register('captured-v08@example.com')
    uid=body['user']['id']; token=body['token']
    internal_order_id=make_order(uid, provider_order_id='order_captured_v08')
    settings=get_settings(); old_mode=settings.billing_mode; old_secret=settings.razorpay_key_secret
    settings.billing_mode='razorpay'; settings.razorpay_key_secret='test-key-secret'
    payment_id='pay_captured_v08'
    signature=hmac.new(b'test-key-secret', f'order_captured_v08|{payment_id}'.encode(), hashlib.sha256).hexdigest()
    monkeypatch.setattr(billing_service, '_fetch_razorpay_payment', lambda _: {
        'id':payment_id,'order_id':'order_captured_v08','amount':29900,'currency':'INR','status':'captured','method':'netbanking'
    })
    h={'Authorization':f'Bearer {token}'}
    before=client.get('/v1/billing/account',headers=h).json()['credits']
    payload={'order_id':internal_order_id,'razorpay_order_id':'order_captured_v08','razorpay_payment_id':payment_id,'razorpay_signature':signature}
    try:
        first=client.post('/v1/billing/verify',headers=h,json=payload); assert first.status_code==200
        second=client.post('/v1/billing/verify',headers=h,json=payload); assert second.status_code==200
        assert second.json()['credits_added']==0
        after=client.get('/v1/billing/account',headers=h).json()['credits']
        assert after-before==250
    finally:
        settings.billing_mode=old_mode; settings.razorpay_key_secret=old_secret
