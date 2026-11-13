import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.auth import repository as repo
from src.modules.auth.models import User
from src.shared.config import settings
from src.shared.jwt_toolkit import create_access_token
from src.shared.redis_client import redis_client
from src.shared.security import hash_password, verify_password
from src.modules.auth.validation import UserOut

# ---------------------------------------------------------------------------
# OTP helpers (internal)
# ---------------------------------------------------------------------------

OTP_TTL_SECONDS = 120


def _generate_otp() -> str:
    """6-digit zero-padded numeric code (000000-999999)."""
    return f"{secrets.randbelow(1_000_000):06d}"


def _otp_key(purpose: str, channel: str, identifier: str | int) -> str:
    """
    Stable Redis key:
      signup + email  -> otp:signup:email:foo@bar.com
      signup + phone  -> otp:signup:phone:+98912...
      change + email  -> otp:change:email:42        (user_id)
      change + phone  -> otp:change:phone:42
    """
    return f"otp:{purpose}:{channel}:{identifier}"


async def _store_otp(key: str, code: str, ttl_seconds: int = OTP_TTL_SECONDS) -> None:
    await redis_client.setex(key, ttl_seconds, code)


async def _consume_otp(key: str, submitted: str) -> None:
    """
    Raise 400 if missing/expired/wrong. Delete on success (single-use).
    """
    stored = await redis_client.get(key)
    if stored is None:
        raise HTTPException(400, "OTP expired or not requested")
    if stored != submitted:
        raise HTTPException(400, "Invalid OTP")
    await redis_client.delete(key)

# ---------------------------------------------------------------------------
# Token helpers (internal)
# ---------------------------------------------------------------------------

def _hash_refresh_token(raw: str) -> str:
    """SHA-256 of the raw refresh token — what we store in the DB."""
    return hashlib.sha256(raw.encode()).hexdigest()


async def _issue_tokens(
    db: AsyncSession,
    user: User,
    role_name: str,
    *,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> tuple[str, str]:
    """Return (access_token, raw_refresh_token). Stores refresh hash in DB."""
    access = create_access_token(user.id, role_name)

    raw_refresh = secrets.token_urlsafe(48)
    expires_at = datetime.now(timezone.utc) + timedelta(
        days=settings.refresh_token_expire_days
    )
    await repo.create_refresh_token(
        db,
        user_id=user.id,
        token_hash=_hash_refresh_token(raw_refresh),
        expires_at=expires_at,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return access, raw_refresh


async def _get_student_role_id(db: AsyncSession) -> int:
    role = await repo.get_role_by_name(db, "student")
    if role is None:
        raise HTTPException(500, "Server misconfigured: 'student' role missing")
    return role.id

# ---------------------------------------------------------------------------
# Login helper
# ---------------------------------------------------------------------------

async def _get_role_name(db: AsyncSession, role_id: int) -> str:
    role = await repo.get_role_by_id(db, role_id)
    if role is None:
        raise HTTPException(500, "Server misconfigured: role missing")
    return role.name

# ---------------------------------------------------------------------------
# OTP request
# ---------------------------------------------------------------------------

async def request_otp_service(
    db: AsyncSession,
    *,
    purpose: str,          # "signup" | "change"
    channel: str,          # "email" | "phone"
    contact: str,          # the email or phone number
    user_id: int | None = None,   # required when purpose == "change"
) -> None:
    if channel not in ("email", "phone"):
        raise HTTPException(400, "Invalid channel")
    if purpose not in ("signup", "change"):
        raise HTTPException(400, "Invalid purpose")
    if purpose == "change" and user_id is None:
        raise HTTPException(400, "user_id is required for purpose='change'")

    # For signup: the contact must NOT already exist
    if purpose == "signup":
        if channel == "email":
            if await repo.get_user_by_email(db, contact):
                raise HTTPException(409, "Email already registered")
        else:
            if await repo.get_user_by_phone(db, contact):
                raise HTTPException(409, "Phone already registered")

    # For change: use user_id as the key identifier (not contact), so an
    # attacker cannot request a change-OTP for someone else's contact string.
    identifier = user_id if purpose == "change" else contact
    key = _otp_key(purpose, channel, identifier)

    code = _generate_otp()
    await _store_otp(key, code)

    # TODO: replace with real SMS/email sender later.
    # For now, log so you can test locally.
    print(f"[OTP] purpose={purpose} channel={channel} to={contact} code={code}")

# ---------------------------------------------------------------------------
# Signup
# ---------------------------------------------------------------------------

async def signup_by_email_service(
    db: AsyncSession,
    *,
    username: str,
    password: str,
    email: str,
    otp_code: str,
    full_name: str | None = None,
    student_number: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> tuple[str, str]:
    # 1. Verify the OTP first — nothing else matters if it's wrong
    await _consume_otp(_otp_key("signup", "email", email), otp_code)

    # 2. Business checks (give clean errors instead of IntegrityError)
    if await repo.get_user_by_username(db, username):
        raise HTTPException(409, "Username already taken")
    if await repo.get_user_by_email(db, email):
        raise HTTPException(409, "Email already registered")
    if student_number and await repo.get_user_by_student_number(db, student_number):
        raise HTTPException(409, "Student number already registered")

    # 3. Role is forced server-side
    role_id = await _get_student_role_id(db)

    # 4. Create the user; catch the race condition the DB can still hit
    try:
        user = await repo.create_user(
            db,
            username=username,
            password_hash=hash_password(password),
            role_id=role_id,
            email=email,
            full_name=full_name,
            student_number=student_number,
        )
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409, "Conflict: duplicate user data")

    # 5. Return tokens — signup also logs the user in
    return await _issue_tokens(
        db, user, "student",
        ip_address=ip_address,
        user_agent=user_agent,
    )

async def signup_by_phone_service(
    db: AsyncSession,
    *,
    username: str,
    password: str,
    phone_number: str,
    otp_code: str,
    full_name: str | None = None,
    student_number: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> tuple[str, str]:
    await _consume_otp(_otp_key("signup", "phone", phone_number), otp_code)

    if await repo.get_user_by_username(db, username):
        raise HTTPException(409, "Username already taken")
    if await repo.get_user_by_phone(db, phone_number):
        raise HTTPException(409, "Phone already registered")
    if student_number and await repo.get_user_by_student_number(db, student_number):
        raise HTTPException(409, "Student number already registered")

    role_id = await _get_student_role_id(db)

    try:
        user = await repo.create_user(
            db,
            username=username,
            password_hash=hash_password(password),
            role_id=role_id,
            phone_number=phone_number,
            full_name=full_name,
            student_number=student_number,
        )
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409, "Conflict: duplicate user data")

    return await _issue_tokens(
        db, user, "student",
        ip_address=ip_address,
        user_agent=user_agent,
    )

# ---------------------------------------------------------------------------
# Session lifecycle
# ---------------------------------------------------------------------------

async def login_service(
    db: AsyncSession,
    *,
    username: str,
    password: str,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> tuple[str, str]:
    # 1. Find user (same error message for missing user and wrong password —
    #    never reveal which one is wrong, or you leak account existence)
    user = await repo.get_user_by_username(db, username)
    if user is None or not verify_password(password, user.password_hash):
        raise HTTPException(401, "Invalid credentials")

    # 2. Reject disabled accounts
    if not user.is_active:
        raise HTTPException(403, "Account disabled")

    # 3. Get role for the JWT claim
    role_name = await _get_role_name(db, user.role_id)

    # 4. Issue tokens (stores refresh hash, returns raw)
    return await _issue_tokens(
        db, user, role_name,
        ip_address=ip_address,
        user_agent=user_agent,
    )


async def refresh_service(
    db: AsyncSession,
    *,
    refresh_token: str,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> tuple[str, str]:
    # 1. Look up the stored hash
    token_hash = _hash_refresh_token(refresh_token)
    stored = await repo.get_refresh_token_by_hash(db, token_hash)

    # 2. Validate existence + not revoked + not expired
    if stored is None or stored.is_revoked:
        raise HTTPException(401, "Invalid refresh token")
    if stored.expires_at <= datetime.now(timezone.utc):
        raise HTTPException(401, "Refresh token expired")

    # 3. Load the user (may have been deactivated since issuance)
    user = await repo.get_user_by_id(db, stored.user_id)
    if user is None or not user.is_active:
        raise HTTPException(401, "User unavailable")

    # 4. Rotate: revoke the OLD token, then issue a NEW pair
    await repo.revoke_refresh_token(db, stored)
    role_name = await _get_role_name(db, user.role_id)
    return await _issue_tokens(
        db, user, role_name,
        ip_address=ip_address,
        user_agent=user_agent,
    )


async def logout_service(
    db: AsyncSession,
    *,
    refresh_token: str,
) -> None:
    # Idempotent: unknown/revoked token = no-op, no 404 leak
    token_hash = _hash_refresh_token(refresh_token)
    stored = await repo.get_refresh_token_by_hash(db, token_hash)
    if stored is not None and not stored.is_revoked:
        await repo.revoke_refresh_token(db, stored)

# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------

async def get_me_service(db: AsyncSession, user: User) -> UserOut:
    role = await repo.get_role_by_id(db, user.role_id)
    if role is None:
        raise HTTPException(500, "Server misconfigured: role missing")
    return UserOut(
        id=user.id,
        username=user.username,
        email=user.email,
        phone_number=user.phone_number,
        full_name=user.full_name,
        student_number=user.student_number,
        role_name=role.name,
        is_active=user.is_active,
        created_at=user.created_at,
    )


async def update_profile_service(
    db: AsyncSession,
    user: User,
    *,
    full_name: str | None = None,
    student_number: str | None = None,
) -> UserOut:
    if student_number is not None and student_number != user.student_number:
        existing = await repo.get_user_by_student_number(db, student_number)
        if existing is not None and existing.id != user.id:
            raise HTTPException(409, "Student number already registered")
    try:
        updated = await repo.update_user_profile(
            db, user, full_name=full_name, student_number=student_number
        )
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409, "Student number already registered")

    role = await repo.get_role_by_id(db, updated.role_id)
    if role is None:
        raise HTTPException(500, "Server misconfigured: role missing")

    return UserOut(
        id=updated.id, username=updated.username, email=updated.email,
        phone_number=updated.phone_number, full_name=updated.full_name,
        student_number=updated.student_number,
        role_name=role.name,
        is_active=updated.is_active, created_at=updated.created_at,
    )
# ---------------------------------------------------------------------------
# Account security
# ---------------------------------------------------------------------------

async def change_password_service(
    db: AsyncSession,
    user: User,
    *,
    old_password: str,
    new_password: str,
) -> None:
    if not verify_password(old_password, user.password_hash):
        raise HTTPException(401, "Old password is incorrect")

    if old_password == new_password:
        raise HTTPException(400, "New password must differ from old password")

    await repo.update_user_password(db, user, hash_password(new_password))

    # Security: a password change invalidates every existing session.
    await repo.revoke_all_user_refresh_tokens(db, user.id)


async def change_email_service(
    db: AsyncSession,
    user: User,
    *,
    new_email: str,
    otp_code: str,
) -> User:
    # 1. Verify OTP (bound to this user via the key)
    await _consume_otp(_otp_key("change", "email", user.id), otp_code)

    # 2. If the new email is unchanged, no-op (avoid 409 on "I clicked save twice")
    if new_email == user.email:
        return user

    # 3. Reject if already taken by another user
    if await repo.get_user_by_email(db, new_email):
        raise HTTPException(409, "Email already registered")

    # 4. Update + DB-level race guard
    try:
        return await repo.update_user_email(db, user, new_email)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409, "Email already registered")


async def change_phone_service(
    db: AsyncSession,
    user: User,
    *,
    new_phone: str,
    otp_code: str,
) -> User:
    await _consume_otp(_otp_key("change", "phone", user.id), otp_code)

    if new_phone == user.phone_number:
        return user

    if await repo.get_user_by_phone(db, new_phone):
        raise HTTPException(409, "Phone already registered")

    try:
        return await repo.update_user_phone(db, user, new_phone)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409, "Phone already registered")