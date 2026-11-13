import re
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


# ===========================================================================
# Reusable validators
# ===========================================================================

_IRAN_PHONE_RE = re.compile(r"^(?:\+98|0)?9\d{9}$")


def verify_iranian_phone(value: str) -> str:
    """Accept 09xxxxxxxxx, 9xxxxxxxxx, or +989xxxxxxxxx."""
    if not _IRAN_PHONE_RE.match(value):
        raise ValueError("Invalid Iranian mobile number")
    return value


def verify_password_strength(value: str) -> str:
    if len(value) < 8:
        raise ValueError("Password must be at least 8 characters")
    if not any(c.isalpha() for c in value):
        raise ValueError("Password must contain at least one letter")
    if not any(c.isdigit() for c in value):
        raise ValueError("Password must contain at least one digit")
    return value


# ===========================================================================
# OTP request
# ===========================================================================

# Service purpose values: "signup" | "change"
_PURPOSES = ("signup", "change")


class EmailOTPRequest(BaseModel):
    email: EmailStr
    purpose: str = Field(..., description="'signup' or 'change'")

    @field_validator("purpose")
    @classmethod
    def _check_purpose(cls, v: str) -> str:
        if v not in _PURPOSES:
            raise ValueError(f"purpose must be one of {_PURPOSES}")
        return v


class PhoneOTPRequest(BaseModel):
    phone_number: str
    purpose: str = Field(..., description="'signup' or 'change'")

    @field_validator("phone_number")
    @classmethod
    def _check_phone(cls, v: str) -> str:
        return verify_iranian_phone(v)

    @field_validator("purpose")
    @classmethod
    def _check_purpose(cls, v: str) -> str:
        if v not in _PURPOSES:
            raise ValueError(f"purpose must be one of {_PURPOSES}")
        return v


# ===========================================================================
# Signup
# ===========================================================================

class _BaseSignup(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str
    otp_code: str = Field(..., min_length=6, max_length=6)
    full_name: Optional[str] = Field(None, max_length=100)
    student_number: Optional[str] = Field(None, max_length=50)

    @field_validator("password")
    @classmethod
    def _pw(cls, v: str) -> str:
        return verify_password_strength(v)


class SignupEmailRequest(_BaseSignup):
    email: EmailStr


class SignupPhoneRequest(_BaseSignup):
    phone_number: str

    @field_validator("phone_number")
    @classmethod
    def _phone(cls, v: str) -> str:
        return verify_iranian_phone(v)


# ===========================================================================
# Login
# ===========================================================================

class LoginRequest(BaseModel):
    username: str = Field(..., description="Username")
    password: str

# ===========================================================================
# Profile
# ===========================================================================

class ProfileUpdateRequest(BaseModel):
    full_name: Optional[str] = Field(None, max_length=100)
    student_number: Optional[str] = Field(None, max_length=50)


# ===========================================================================
# Account security (OTP-protected changes)
# ===========================================================================

class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def _pw(cls, v: str) -> str:
        return verify_password_strength(v)


class ChangeEmailRequest(BaseModel):
    new_email: EmailStr
    otp_code: str = Field(..., min_length=6, max_length=6)


class ChangePhoneRequest(BaseModel):
    new_phone: str
    otp_code: str = Field(..., min_length=6, max_length=6)

    @field_validator("new_phone")
    @classmethod
    def _phone(cls, v: str) -> str:
        return verify_iranian_phone(v)


# ===========================================================================
# Response models
# ===========================================================================

class UserOut(BaseModel):
    """Public view of a user. Never includes password_hash or role_id."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: Optional[str]
    phone_number: Optional[str]
    full_name: Optional[str]
    student_number: Optional[str]
    role_name: str
    is_active: bool
    created_at: datetime


class AccessTokenOut(BaseModel):
    """For the browser flow: only the access token in the body."""
    access_token: str
    token_type: str = "bearer"


class OTPRequestOut(BaseModel):
    """What /request_otp/* returns. 'sent' is always True unless it errored."""
    sent: bool = True
    message: str = "OTP sent"