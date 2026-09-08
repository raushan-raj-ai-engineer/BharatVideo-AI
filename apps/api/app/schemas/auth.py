from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserRead(BaseModel):
    id: str
    name: str
    email: str
    plan_id: str
    credits: int
    created_at: datetime


class AuthResponse(BaseModel):
    token: str
    user: UserRead


class CheckoutRequest(BaseModel):
    plan_id: str = Field(min_length=2, max_length=40)


class MockCompleteRequest(BaseModel):
    order_id: str


class VerifyPaymentRequest(BaseModel):
    order_id: str
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str
