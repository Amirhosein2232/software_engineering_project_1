from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional
import re

# ==========================================
# REUSABLE FIELD VALIDATORS (UTILS)
# ==========================================

# ==========================================
# REUSABLE RE-USABLE VALIDATION LOGIC
# ==========================================

def verify_iranian_phone(value: str) -> str:
    """Ensures the phone number matches standard formats (e.g., 09123456789 or +989123456789)."""
    pattern = r"^(0|\+98)?9\d{9}$"
    if not re.match(pattern, value):
        raise ValueError("Invalid phone number format. Must be a valid mobile number.")
    return value

def verify_password_strength(value: str) -> str:
    """Enforces a basic security policy for passwords."""
    if len(value) < 8:
        raise ValueError("Password must be at least 8 characters long.")
    return value

# ==========================================
# 1. OTP REQUEST MODELS
# ==========================================

class PhoneOTPRequest(BaseModel):
    phone_number: str = Field(..., description="The target phone number to receive the SMS")
    purpose: str = Field(..., description="Purpose: 'registration', 'profile_update', or 'password_reset'")

    @field_validator("phone_number")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        return verify_iranian_phone(v)

    @field_validator("purpose")
    @classmethod
    def validate_purpose(cls, v: str) -> str:
        allowed = ["registration", "profile_update", "password_reset"]
        if v not in allowed:
            raise ValueError(f"Purpose must be one of {allowed}")
        return v

class EmailOTPRequest(BaseModel):
    email: EmailStr = Field(..., description="The target email address to receive the verification code")
    purpose: str = Field(..., description="Purpose: 'registration', 'profile_update', or 'password_reset'")

    @field_validator("purpose")
    @classmethod
    def validate_purpose(cls, v: str) -> str:
        allowed = ["registration", "profile_update", "password_reset"]
        if v not in allowed:
            raise ValueError(f"Purpose must be one of {allowed}")
        return v

# ==========================================
# 2. SIGN UP / REGISTRATION MODELS
# ==========================================

class BaseSignUp(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, description="Unique login identifier")
    password: str = Field(..., description="Plain-text password to be hashed by the backend")
    full_name: str = Field(..., min_length=2, max_length=100)
    student_number: Optional[str] = Field(None, description="Optional academic identifier")
    otp: str = Field(..., min_length=4, max_length=6, description="The temporary verification code received")

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        return verify_password_strength(v)

class PhoneSignUpRequest(BaseSignUp):
    phone_number: str

    @field_validator("phone_number")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        return verify_iranian_phone(v)

class EmailSignUpRequest(BaseSignUp):
    email: EmailStr

# ==========================================
# 3. LOGIN & SESSION LIFE-CYCLE MODELS
# ==========================================

class LoginRequest(BaseModel):
    identifier: str = Field(..., description="Username, email, or phone number")
    password: str = Field(..., description="User account password")

class TokenRefreshRequest(BaseModel):
    refresh_token: str = Field(..., description="The cryptographically secure token checked against the Refresh_Tokens table")

