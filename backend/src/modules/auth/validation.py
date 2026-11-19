import re
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator


# ===========================================================================
# Reusable validators
# ===========================================================================

_IRAN_PHONE_RE = re.compile(r"^(?:\+98|0)?9\d{9}$")


def verify_iranian_phone(value: str) -> str:
    if not _IRAN_PHONE_RE.match(value):
        raise ValueError("Invalid Iranian mobile number")
    # Normalize to +989XXXXXXXXX
    digits = value.lstrip("+").replace(" ", "")
    if digits.startswith("98"):
        return f"+{digits}"
    if digits.startswith("0"):
        return f"+98{digits[1:]}"
    return f"+98{digits}"


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

class EmailOTPRequest(BaseModel):
    email: EmailStr = Field(
        ...,
        description="Email address to receive the 6-digit code. The endpoint "
                    "(signup vs change) already determines the purpose — do not "
                    "send a `purpose` field.",
        examples=["student@university.edu"],
    )


class PhoneOTPRequest(BaseModel):
    phone_number: str = Field(
        ...,
        description="Iranian mobile number. Accepted formats: "
                    "`09xxxxxxxxx`, `9xxxxxxxxx`, or `+989xxxxxxxxx`.",
        examples=["09123456789"],
    )

    @field_validator("phone_number")
    @classmethod
    def _check_phone(cls, v: str) -> str:
        return verify_iranian_phone(v)


# ===========================================================================
# Signup
# ===========================================================================

class _BaseSignup(BaseModel):
    username: str = Field(
        ...,
        min_length=3,
        max_length=50,
        description="Unique login name. 3–50 characters.",
        examples=["ali_ahmadi"],
    )
    password: str = Field(
        ...,
        description="At least 8 characters, containing **both a letter and a digit**.",
        examples=["MyStrongPass123"],
    )
    otp_code: str = Field(
        ...,
        min_length=6,
        max_length=6,
        description="The 6-digit code you received after calling "
                    "`/request_otp/signup/...`. Single-use, expires in 2 minutes.",
        examples=["123456"],
    )
    full_name: Optional[str] = Field(
        None,
        max_length=100,
        description="Optional display name.",
        examples=["Ali Ahmadi"],
    )
    student_number: Optional[str] = Field(
        None,
        min_length=11,
        max_length=11,
        description="Optional. If provided, must be **exactly 11 digits** and unique.",
        examples=["40123456789"],
    )

    @field_validator("password")
    @classmethod
    def _pw(cls, v: str) -> str:
        return verify_password_strength(v)

    @field_validator("student_number")
    @classmethod
    def _student_number(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        if not v.isdigit():
            raise ValueError("Student number must contain only digits")
        return v

    @field_validator("otp_code")
    @classmethod
    def _otp_digits(cls, v: str) -> str:
        if not v.isdigit():
            raise ValueError("OTP must be exactly 6 digits")
        return v

class SignupEmailRequest(_BaseSignup):
    email: EmailStr = Field(
        ...,
        description="Must match the email you requested the signup OTP for.",
        examples=["student@university.edu"],
    )


class SignupPhoneRequest(_BaseSignup):
    phone_number: str = Field(
        ...,
        description="Must match the phone number you requested the signup OTP for. "
                    "Accepted formats: `09xxxxxxxxx`, `9xxxxxxxxx`, `+989xxxxxxxxx`.",
        examples=["09123456789"],
    )

    @field_validator("phone_number")
    @classmethod
    def _phone(cls, v: str) -> str:
        return verify_iranian_phone(v)


# ===========================================================================
# Login
# ===========================================================================

class LoginRequest(BaseModel):
    username: str = Field(
        ...,
        description="The username chosen at signup.",
        examples=["ali_ahmadi"],
    )
    password: str = Field(
        ...,
        description="Plain password. Will be verified against the stored hash.",
        examples=["MyStrongPass123"],
    )


# ===========================================================================
# Profile
# ===========================================================================

class ProfileUpdateRequest(BaseModel):
    full_name: Optional[str] = Field(
        None,
        max_length=100,
        description="New display name. Omit to leave unchanged.",
        examples=["Ali Ahmadi"],
    )
    student_number: Optional[str] = Field(
        None,
        min_length=11,
        max_length=11,
        description="New student number. If provided, must be exactly 11 digits "
                    "and not already used by another account. Omit to leave unchanged. "
                    "**Note:** changing email or phone is NOT done here — use "
                    "`/change/email` or `/change/phone` (they require an OTP).",
        examples=["40123456789"],
    )

    @field_validator("student_number")
    @classmethod
    def _student_number(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        if not v.isdigit():
            raise ValueError("Student number must contain only digits")
        return v

    @model_validator(mode="after")
    def _at_least_one(self):
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")
        return self


# ===========================================================================
# Account security (OTP-protected changes)
# ===========================================================================

class ChangePasswordRequest(BaseModel):
    old_password: str = Field(
        ...,
        description="Your current password (second factor before allowing the change).",
        examples=["MyStrongPass123"],
    )
    new_password: str = Field(
        ...,
        description="The code sent to the **new** email address via "
                    "`/request_otp/change/email`. Single-use, 2-minute expiry.",
        examples=["NewStrongPass456"],
    )

    @field_validator("new_password")
    @classmethod
    def _pw(cls, v: str) -> str:
        return verify_password_strength(v)

    @model_validator(mode="after")
    def _must_differ(self): 
        if self.old_password == self.new_password:
            raise ValueError("New password must differ from old password")
        return self


class ChangeEmailRequest(BaseModel):
    new_email: EmailStr = Field(
        ...,
        description="The new email address.",
        examples=["new.email@university.edu"],
    )
    otp_code: str = Field(
        ...,
        min_length=6,
        max_length=6,
        description="The code sent to the **current** account via "
                    "`/request_otp/change/email`. Single-use, 2-minute expiry.",
        examples=["123456"],
    )

    @field_validator("otp_code")
    @classmethod
    def _otp_digits(cls, v: str) -> str:
        if not v.isdigit():
            raise ValueError("OTP must be exactly 6 digits")
        return v


class ChangePhoneRequest(BaseModel):
    new_phone: str = Field(
        ...,
        description="The new phone number. Accepted formats: "
                    "`09xxxxxxxxx`, `9xxxxxxxxx`, `+989xxxxxxxxx`.",
        examples=["09123456789"],
    )
    otp_code: str = Field(
        ...,
        min_length=6,
        max_length=6,
        description="The code sent via `/request_otp/change/phone`. Single-use, "
                    "2-minute expiry.",
        examples=["123456"],
    )

    @field_validator("new_phone")
    @classmethod
    def _phone(cls, v: str) -> str:
        return verify_iranian_phone(v)

    @field_validator("otp_code")
    @classmethod
    def _otp_digits(cls, v: str) -> str:
        if not v.isdigit():
            raise ValueError("OTP must be exactly 6 digits")
        return v
    


# ===========================================================================
# Response models
# ===========================================================================

class UserOut(BaseModel):
    """Public view of a user. Never includes password_hash or role_id."""
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., examples=[1])
    username: str = Field(..., examples=["ali_ahmadi"])
    email: Optional[str] = Field(None, examples=["student@university.edu"])
    phone_number: Optional[str] = Field(None, examples=["09123456789"])
    full_name: Optional[str] = Field(None, examples=["Ali Ahmadi"])
    student_number: Optional[str] = Field(None, examples=["40123456789"])
    role_name: str = Field(
        ...,
        description="One of: `student`, `operator`, `admin`.",
        examples=["student"],
    )
    is_active: bool = Field(..., examples=[True])
    created_at: datetime = Field(..., examples=["2026-11-18T12:00:00Z"])


class AccessTokenOut(BaseModel):
    """For the browser flow: only the access token in the body."""
    access_token: str = Field(
        ...,
        description="JWT to include in the `Authorization: Bearer <token>` header "
                    "on every protected request.",
        examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."],
    )
    token_type: str = Field("bearer", examples=["bearer"])


class OTPRequestOut(BaseModel):
    sent: bool = Field(True, examples=[True])
    message: str = Field("OTP sent", examples=["OTP sent"])