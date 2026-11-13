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
REFRESH_COOKIE_PATH = "/auth/refresh"

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

@router.post("/request_otp/signup/email", response_model=OTPRequestOut)
async def request_otp_signup_email(
    payload: EmailOTPRequest,
    db: AsyncSession = Depends(get_db),
):
    await service.request_otp_service(
        db, purpose="signup", channel="email", contact=payload.email
    )
    return OTPRequestOut()


@router.post("/request_otp/signup/phone", response_model=OTPRequestOut)
async def request_otp_signup_phone(
    payload: PhoneOTPRequest,
    db: AsyncSession = Depends(get_db),
):
    await service.request_otp_service(
        db, purpose="signup", channel="phone", contact=payload.phone_number
    )
    return OTPRequestOut()


@router.post("/request_otp/change/email", response_model=OTPRequestOut)
async def request_otp_change_email(
    payload: EmailOTPRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await service.request_otp_service(
        db,
        purpose="change",
        channel="email",
        contact=payload.email,
        user_id=user.id,
    )
    return OTPRequestOut()


@router.post("/request_otp/change/phone", response_model=OTPRequestOut)
async def request_otp_change_phone(
    payload: PhoneOTPRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
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

@router.post("/sign_up/email", response_model=AccessTokenOut)
async def sign_up_email(
    payload: SignupEmailRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
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


@router.post("/sign_up/phone", response_model=AccessTokenOut)
async def sign_up_phone(
    payload: SignupPhoneRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
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

@router.post("/login", response_model=AccessTokenOut)
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    access, refresh = await service.login_service(
        db,
        username=payload.username,
        password=payload.password,
        ip_address=_client_ip(request),
        user_agent=_user_agent(request),
    )
    _set_refresh_cookie(response, refresh)
    return AccessTokenOut(access_token=access)


@router.post("/refresh-token", response_model=AccessTokenOut)
async def refresh_token_endpoint(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
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


@router.post("/logout", status_code=204)
async def logout(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    raw_refresh = request.cookies.get(REFRESH_COOKIE_NAME)
    if raw_refresh is not None:
        await service.logout_service(db, refresh_token=raw_refresh)
    _clear_refresh_cookie(response)
    return Response(status_code=204)

# ==========================================
# 4. PROFILE & ACCOUNT SECURITY
# ==========================================

@router.get("/me", response_model=UserOut)
async def get_my_profile(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await service.get_me_service(db, user)


@router.patch("/me", response_model=UserOut)
async def update_my_profile(
    payload: ProfileUpdateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await service.update_profile_service(
        db, user,
        full_name=payload.full_name,
        student_number=payload.student_number,
    )


@router.put("/change/password", status_code=204)
async def change_my_password(
    payload: ChangePasswordRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await service.change_password_service(
        db, user,
        old_password=payload.old_password,
        new_password=payload.new_password,
    )
    return Response(status_code=204)


@router.put("/change/email", response_model=UserOut)
async def change_my_email(
    payload: ChangeEmailRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    updated = await service.change_email_service(
        db, user,
        new_email=payload.new_email,
        otp_code=payload.otp_code,
    )
    # Reuse get_me_service to build the UserOut (single source of truth)
    return await service.get_me_service(db, updated)


@router.put("/change/phone", response_model=UserOut)
async def change_my_phone(
    payload: ChangePhoneRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    updated = await service.change_phone_service(
        db, user,
        new_phone=payload.new_phone,
        otp_code=payload.otp_code,
    )
    return await service.get_me_service(db, updated)