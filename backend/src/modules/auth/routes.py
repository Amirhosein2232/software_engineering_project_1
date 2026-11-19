from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.auth import service
from src.modules.auth.validation import (
    AccessTokenOut,
    ChangeEmailRequest,
    ChangePasswordRequest,
    ChangePhoneRequest,
    EmailOTPRequest,
    LoginRequest,
    OTPRequestOut,
    PhoneOTPRequest,
    ProfileUpdateRequest,
    SignupEmailRequest,
    SignupPhoneRequest,
    UserOut,
)
from src.shared.config import settings
from src.shared.database import get_db
from src.shared.dependencies import get_current_user
from src.modules.auth.models import User

router = APIRouter()

# ---------------------------------------------------------------------------
# Cookie + request helpers
# ---------------------------------------------------------------------------

REFRESH_COOKIE_NAME = "refresh_token"
REFRESH_COOKIE_PATH = "/"

def _set_refresh_cookie(response: Response, refresh_token: str) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=refresh_token,
        httponly=True,
        secure=False,      # True in production (HTTPS only)
        samesite="lax",
        max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
        path=REFRESH_COOKIE_PATH,
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(key=REFRESH_COOKIE_NAME, path=REFRESH_COOKIE_PATH)


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def _user_agent(request: Request) -> str | None:
    return request.headers.get("user-agent")

# ==========================================
# 1. OTP ENGINE (Unified Hub)
# ==========================================

@router.post("/request_otp/signup/email", tags=['OTP ENGINE'], response_model=OTPRequestOut)
async def request_otp_signup_email(
    payload: EmailOTPRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    **Step 1 of email signup: send a verification code.**

    Use this when a new user wants to register with an email address.

    **What you send:** `{ "email": "student@university.edu" }`

    **What happens:** the server generates a 6-digit code, stores it in
    Redis for **2 minutes**, and "sends" it to the email address. In this
    project, the code is printed to the **server console** (not a real
    email — swap in a real email provider later).

    **What you get back:** `{ "sent": true, "message": "OTP sent" }`

    **Errors:**
    - `409 Conflict` — email is already registered. The frontend should
      tell the user "this email is already in use — try logging in instead."
    - `422 Unprocessable Entity` — invalid email format.

    **Next step:** user submits `POST /auth/sign_up/email` with the code.
    """
    await service.request_otp_service(
        db, purpose="signup", channel="email", contact=payload.email
    )
    return OTPRequestOut()


@router.post("/request_otp/signup/phone", tags=['OTP ENGINE'], response_model=OTPRequestOut)
async def request_otp_signup_phone(
    payload: PhoneOTPRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    **Step 1 of phone signup: send a verification code.**

    Use this when a new user wants to register with a phone number.

    **What you send:** `{ "phone_number": "09123456789" }`
    (accepted formats: `09xxxxxxxxx`, `9xxxxxxxxx`, `+989xxxxxxxxx`)

    **What happens:** the server generates a 6-digit code, stores it in
    Redis for **2 minutes**, and "sends" it via SMS. In this project, the
    code is printed to the **server console**.

    **What you get back:** `{ "sent": true, "message": "OTP sent" }`

    **Errors:**
    - `409 Conflict` — phone number is already registered.
    - `422 Unprocessable Entity` — invalid phone format.

    **Next step:** user submits `POST /auth/sign_up/phone` with the code.
    """
    await service.request_otp_service(
        db, purpose="signup", channel="phone", contact=payload.phone_number
    )
    return OTPRequestOut()


@router.post("/request_otp/change/email", tags=['OTP ENGINE'], response_model=OTPRequestOut)
async def request_otp_change_email(
    payload: EmailOTPRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    **Step 1 of email change: send a verification code to the NEW email.**

    **Requires authentication** — the user must be logged in. This prevents
    an attacker from requesting OTPs for arbitrary users.

    **What you send:** `{ "email": "new.email@university.edu" }` —
    the **new** email address the user wants to switch to.

    **What happens:** the server generates a 6-digit code, stores it in
    Redis (keyed by your user id, valid for 2 minutes), and "sends" it to
    the new email address. In this project, the code is printed to the
    **server console**.

    **What you get back:** `{ "sent": true, "message": "OTP sent" }`

    **Errors:**
    - `401 Unauthorized` — no valid access token.
    - `422 Unprocessable Entity` — invalid email format.

    **Next step:** user submits `PUT /auth/change/email` with the new email
    and the code.
    """
    await service.request_otp_service(
        db,
        purpose="change",
        channel="email",
        contact=payload.email,
        user_id=user.id,
    )
    return OTPRequestOut()


@router.post("/request_otp/change/phone", tags=['OTP ENGINE'], response_model=OTPRequestOut)
async def request_otp_change_phone(
    payload: PhoneOTPRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    **Step 1 of phone change: send a verification code to the NEW phone.**

    **Requires authentication** — the user must be logged in.

    **What you send:** `{ "phone_number": "09123456789" }` —
    the **new** phone number the user wants to switch to.

    **What happens:** the server generates a 6-digit code, stores it in
    Redis (keyed by your user id, valid for 2 minutes), and "sends" it via
    SMS. In this project, the code is printed to the **server console**.

    **What you get back:** `{ "sent": true, "message": "OTP sent" }`

    **Errors:**
    - `401 Unauthorized` — no valid access token.
    - `422 Unprocessable Entity` — invalid phone format.

    **Next step:** user submits `PUT /auth/change/phone` with the new phone
    and the code.
    """
    await service.request_otp_service(
        db,
        purpose="change",
        channel="phone",
        contact=payload.phone_number,
        user_id=user.id,
    )
    return OTPRequestOut()

# ==========================================
# 2. REGISTRATION PIPELINE
# ==========================================

@router.post("/sign_up/email", tags=['REGISTRATION'], response_model=AccessTokenOut)
async def sign_up_email(
    payload: SignupEmailRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """
    **Step 2 of email signup: create the account.**

    Use this after the user has received their OTP from
    `POST /auth/request_otp/signup/email`.

    **What you send:**
    - `username` — 3–50 characters, unique
    - `password` — at least 8 chars, with a letter and a digit
    - `email` — must match the email you requested the OTP for
    - `otp_code` — the 6-digit code from the previous step
    - `full_name` (optional)
    - `student_number` (optional, 11 digits if provided)

    **What happens:** the server verifies the OTP, checks uniqueness, hashes
    the password, and creates the user with the **`student` role** (forced —
    the client cannot choose a role here).

    **What you get back:** `{ "access_token": "eyJ...", "token_type": "bearer" }`
    — the refresh token is set as an **HttpOnly cookie** automatically.

    **What to do with the response:** store the access token in memory
    (NOT localStorage), attach it as `Authorization: Bearer <token>` on
    future requests, and navigate the user to their dashboard.

    **Errors:**
    - `400 Bad Request` — OTP is wrong or expired. The user must request
      a new code.
    - `409 Conflict` — username, email, or student_number already taken.
    - `422 Unprocessable Entity` — validation failed (weak password,
      malformed email, etc.).
    """
    access, refresh = await service.signup_by_email_service(
        db,
        username=payload.username,
        password=payload.password,
        email=payload.email,
        otp_code=payload.otp_code,
        full_name=payload.full_name,
        student_number=payload.student_number,
        ip_address=_client_ip(request),
        user_agent=_user_agent(request),
    )
    _set_refresh_cookie(response, refresh)
    return AccessTokenOut(access_token=access)


@router.post("/sign_up/phone", tags=['REGISTRATION'], response_model=AccessTokenOut)
async def sign_up_phone(
    payload: SignupPhoneRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """
    **Step 2 of phone signup: create the account.**

    Use this after the user has received their OTP from
    `POST /auth/request_otp/signup/phone`.

    **What you send:**
    - `username` — 3–50 characters, unique
    - `password` — at least 8 chars, with a letter and a digit
    - `phone_number` — must match the phone you requested the OTP for
    - `otp_code` — the 6-digit code from the previous step
    - `full_name` (optional)
    - `student_number` (optional, 11 digits if provided)

    **What happens:** the server verifies the OTP, checks uniqueness, hashes
    the password, and creates the user with the **`student` role** (forced —
    the client cannot choose a role here).

    **What you get back:** `{ "access_token": "eyJ...", "token_type": "bearer" }`
    — the refresh token is set as an **HttpOnly cookie** automatically.

    **What to do with the response:** store the access token in memory,
    attach it as `Authorization: Bearer <token>` on future requests, and
    navigate the user to their dashboard.

    **Errors:**
    - `400 Bad Request` — OTP is wrong or expired.
    - `409 Conflict` — username, phone, or student_number already taken.
    - `422 Unprocessable Entity` — validation failed.
    """
    access, refresh = await service.signup_by_phone_service(
        db,
        username=payload.username,
        password=payload.password,
        phone_number=payload.phone_number,
        otp_code=payload.otp_code,
        full_name=payload.full_name,
        student_number=payload.student_number,
        ip_address=_client_ip(request),
        user_agent=_user_agent(request),
    )
    _set_refresh_cookie(response, refresh)
    return AccessTokenOut(access_token=access)


# ==========================================
# 3. SESSION LIFECYCLE
# ==========================================

@router.post("/login", tags=['SESSION LIFECYCLE'], response_model=AccessTokenOut)
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):    
    """
    **Log in with username and password.**

    **What you send:**
    - `username`
    - `password`

    **What happens:** the server looks up the user, verifies the password
    against the stored hash, checks the account is active, and issues tokens.

    **What you get back:** `{ "access_token": "eyJ...", "token_type": "bearer" }`
    — the refresh token is set as an **HttpOnly cookie** automatically.

    **How to use the access token:** attach it as
    `Authorization: Bearer <access_token>` on every protected request.
    It expires after **15 minutes** — use `POST /auth/refresh-token` to
    get a new one without re-entering the password.

    **Errors:**
    - `401 Unauthorized` — wrong username or password. The message is
      intentionally the same for both cases (prevents username enumeration).
    - `403 Forbidden` — the account has been deactivated by an admin.
    """
    access, refresh = await service.login_service(
        db,
        username=payload.username,
        password=payload.password,
        ip_address=_client_ip(request),
        user_agent=_user_agent(request),
    )
    _set_refresh_cookie(response, refresh)
    return AccessTokenOut(access_token=access)


@router.post("/refresh-token", tags=['SESSION LIFECYCLE'], response_model=AccessTokenOut)
async def refresh_token_endpoint(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """
    **Get a new access token using the refresh cookie.**

    The access token expires after 15 minutes. When it does, the frontend
    calls this endpoint (the browser sends the `refresh_token` HttpOnly
    cookie automatically) to get a fresh access token **without asking the
    user to log in again**.

    **What you send:** nothing in the body. The refresh token is read from
    the `refresh_token` cookie the browser sends automatically.

    **What happens:**
    1. The server validates the refresh token against its hash in the
       database.
    2. The old refresh token is **revoked** (rotation).
    3. A new access token and a new refresh token are issued.

    **What you get back:** `{ "access_token": "eyJ...", "token_type": "bearer" }`
    — a **new** refresh cookie is set automatically (the old one is invalid now).

    **Frontend behavior:** call this silently whenever a request returns
    `401` with "expired access token", then retry the original request.
    Do not show this to the user — it's transparent.

    **Errors:**
    - `401 Unauthorized` — missing, invalid, revoked, or expired refresh
      token. The user must log in again.
    """
    raw_refresh = request.cookies.get(REFRESH_COOKIE_NAME)
    if raw_refresh is None:
        from fastapi import HTTPException
        raise HTTPException(401, "Missing refresh token cookie")

    access, new_refresh = await service.refresh_service(
        db,
        refresh_token=raw_refresh,
        ip_address=_client_ip(request),
        user_agent=_user_agent(request),
    )
    _set_refresh_cookie(response, new_refresh)
    return AccessTokenOut(access_token=access)


@router.post("/logout", tags=['SESSION LIFECYCLE'], status_code=204)
async def logout(request: Request, response: Response, db=Depends(get_db)):
    """
    **Log out the current session.**

    **What you send:** nothing. The refresh token is read from the cookie.

    **What happens:**
    1. The current refresh token is marked as revoked in the database.
    2. The `refresh_token` cookie is cleared from the browser.

    **What you get back:** `204 No Content` — no JSON body.

    **Important:** this only logs out **this session**. If the user is
    logged in on their phone and their laptop, only the current device is
    logged out. Other sessions stay active. (There is no "log out all
    devices" endpoint in this project — if needed, it would require a
    separate route.)

    **Frontend behavior:** after calling this, clear the access token from
    memory and navigate to the login page. Subsequent protected requests
    will fail with `401` until the user logs in again.
    """
    raw_refresh = request.cookies.get(REFRESH_COOKIE_NAME)
    if raw_refresh is not None:
        await service.logout_service(db, refresh_token=raw_refresh)
    _clear_refresh_cookie(response)
    response.status_code = 204
    return response

# ==========================================
# 4. PROFILE & ACCOUNT SECURITY
# ==========================================

@router.get("/me", tags=['PROFILE'], response_model=UserOut)
async def get_my_profile(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    **Get the logged-in user's profile.**

    **Requires authentication** — send `Authorization: Bearer <token>`.

    **What you get back:** the user's own profile:
    - `id`, `username`, `email`, `phone_number`
    - `full_name`, `student_number`
    - `role_name` — `student`, `operator`, or `admin`
    - `is_active`, `created_at`

    **Note:** `password_hash` and `role_id` are **never** returned — only
    `role_name` (the human-readable role). The frontend can use
    `role_name` to branch UI: show the student dashboard for `student`,
    operator dashboard for `operator`, etc.

    **Errors:**
    - `401 Unauthorized` — no valid access token.
    - `404 Not Found` — user was deleted after the token was issued
      (rare — only if the row was removed, which normally doesn't happen;
      deactivated users still exist with `is_active = false`).
    """
    return await service.get_me_service(db, user)


@router.patch("/me", tags=['PROFILE'], response_model=UserOut)
async def update_my_profile(
    payload: ProfileUpdateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    **Update your display name and/or student number.**

    **What you send:** only the fields you want to change.

    To change only the name: { "full_name": "New Name" }

    To change both: { "full_name": "New Name", "student_number": "40123456789" }

    Omitted fields stay unchanged. **At least one field is required** —
    an empty `{}` is rejected with `422`.

    **What you can change here:**
    - `full_name` — display name
    - `student_number` — 11 digits, must be unique

    **What you CANNOT change here:**
    - `email` — use `PUT /change/email` (needs OTP)
    - `phone_number` — use `PUT /change/phone` (needs OTP)
    - `password` — use `PUT /change/password`
    - `username`, `role`, `is_active` — admin-only or immutable

    **What you get back:** the updated profile (`UserOut`).

    **Errors:**
    - `401 Unauthorized` — no valid access token.
    - `409 Conflict` — new student_number is already used by another user.
    - `422 Unprocessable Entity` — empty body, or student_number is not 11 digits.
    """
    return await service.update_profile_service(
        db, user,
        full_name=payload.full_name,
        student_number=payload.student_number,
    )


@router.put("/change/password", tags=['PROFILE'], status_code=204)
async def change_my_password(
    payload: ChangePasswordRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    **Change your password.**

    **What you send:**
    - `old_password` — your current password (proves it's really you)
    - `new_password` — at least 8 chars, with a letter and a digit, and
      **must differ** from the old one

    **What happens:**
    1. The server verifies `old_password` against the stored hash.
    2. The new password is hashed and saved.
    3. **All active sessions are logged out** — every refresh token
       belonging to you is revoked. This protects the account if it was
       compromised: the attacker is kicked out.

    **What you get back:** `204 No Content` — no JSON body.

    **Frontend behavior:** after a successful call, the user's current
    access token is still valid (for up to 15 minutes), but the refresh
    token is dead. The user will be logged out as soon as the access token
    expires. **Show a message:** "Password changed. You will need to log
    in again soon." Better UX: clear the access token and redirect to login
    immediately.

    **Errors:**
    - `400 Bad Request` — new password is the same as the old one.
    - `401 Unauthorized` — old password is wrong, or no valid access token.
    - `422 Unprocessable Entity` — new password is too weak.
    """
    await service.change_password_service(
        db, user,
        old_password=payload.old_password,
        new_password=payload.new_password,
    )
    return Response(status_code=204)


@router.put("/change/email", tags=['PROFILE'], response_model=UserOut)
async def change_my_email(
    payload: ChangeEmailRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    **Step 1 of email change: send a verification code to the NEW email.**

    **Requires authentication** — the user must be logged in. This prevents
    an attacker from requesting OTPs for arbitrary users.

    **What you send:** `{ "email": "new.email@university.edu" }` —
    the **new** email address the user wants to switch to.

    **What happens:** the server generates a 6-digit code, stores it in
    Redis (keyed by your user id, valid for 2 minutes), and "sends" it to
    the new email address. In this project, the code is printed to the
    **server console**.

    **What you get back:** `{ "sent": true, "message": "OTP sent" }`

    **Errors:**
    - `401 Unauthorized` — no valid access token.
    - `422 Unprocessable Entity` — invalid email format.

    **Next step:** user submits `PUT /auth/change/email` with the new email
    and the code.
    """
    updated = await service.change_email_service(
        db, user,
        new_email=payload.new_email,
        otp_code=payload.otp_code,
    )
    # Reuse get_me_service to build the UserOut (single source of truth)
    return await service.get_me_service(db, updated)


@router.put("/change/phone", tags=['PROFILE'], response_model=UserOut)
async def change_my_phone(
    payload: ChangePhoneRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    **Step 2 of phone change: confirm the new phone with the OTP.**

    Use this after `POST /auth/request_otp/change/phone` has sent a code
    to the **new** phone number.

    **What you send:**
    - `new_phone` — the same phone you requested the OTP for
      (accepted formats: `09xxxxxxxxx`, `9xxxxxxxxx`, `+989xxxxxxxxx`)
    - `otp_code` — the 6-digit code from that phone

    **What happens:**
    1. The server verifies the OTP (keyed by your user id).
    2. The phone is updated in the database (normalized to `+989...`).
    3. The OTP is deleted (single-use).

    **What you get back:** the updated profile (`UserOut`) with the new
    `phone_number`.

    **Errors:**
    - `400 Bad Request` — OTP is wrong or expired.
    - `401 Unauthorized` — no valid access token.
    - `409 Conflict` — the new phone is already used by another user.
    - `422 Unprocessable Entity` — malformed phone number.
    """
    updated = await service.change_phone_service(
        db, user,
        new_phone=payload.new_phone,
        otp_code=payload.otp_code,
    )
    return await service.get_me_service(db, updated)