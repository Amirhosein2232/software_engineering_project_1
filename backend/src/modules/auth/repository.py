from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.auth.models import RefreshToken, Role, User


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

async def get_user_by_id(db: AsyncSession, user_id: int) -> User | None:
    return await db.get(User, user_id)


async def get_user_by_username(db: AsyncSession, username: str) -> User | None:
    result = await db.execute(select(User).where(User.username == username))
    return result.scalar_one_or_none()


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_user_by_phone(db: AsyncSession, phone_number: str) -> User | None:
    result = await db.execute(select(User).where(User.phone_number == phone_number))
    return result.scalar_one_or_none()


async def create_user(
    db: AsyncSession,
    *,
    username: str,
    password_hash: str,
    role_id: int,
    email: str | None = None,
    phone_number: str | None = None,
    full_name: str | None = None,
    student_number: str | None = None,
) -> User:
    user = User(
        username=username,
        password_hash=password_hash,
        role_id=role_id,
        email=email,
        phone_number=phone_number,
        full_name=full_name,
        student_number=student_number,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def update_user_profile(
    db: AsyncSession,
    user: User,
    *,
    full_name: str | None = None,
    student_number: str | None = None,
) -> User:
    if full_name is not None:
        user.full_name = full_name
    if student_number is not None:
        user.student_number = student_number
    await db.commit()
    await db.refresh(user)
    return user


async def update_user_password(db: AsyncSession, user: User, password_hash: str) -> User:
    user.password_hash = password_hash
    await db.commit()
    await db.refresh(user)
    return user


async def update_user_email(db: AsyncSession, user: User, new_email: str) -> User:
    user.email = new_email
    await db.commit()
    await db.refresh(user)
    return user


async def update_user_phone(db: AsyncSession, user: User, new_phone: str) -> User:
    user.phone_number = new_phone
    await db.commit()
    await db.refresh(user)
    return user


async def set_user_active(db: AsyncSession, user: User, is_active: bool) -> User:
    user.is_active = is_active
    await db.commit()
    await db.refresh(user)
    return user


# ---------------------------------------------------------------------------
# Roles
# ---------------------------------------------------------------------------

async def get_role_by_name(db: AsyncSession, name: str) -> Role | None:
    result = await db.execute(select(Role).where(Role.name == name))
    return result.scalar_one_or_none()

async def get_role_by_id(db: AsyncSession, role_id: int) -> Role | None:
    return await db.get(Role, role_id)

# ---------------------------------------------------------------------------
# Refresh tokens
# ---------------------------------------------------------------------------

async def create_refresh_token(
    db: AsyncSession,
    *,
    user_id: int,
    token_hash: str,
    expires_at: datetime,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> RefreshToken:
    token = RefreshToken(
        user_id=user_id,
        token_hash=token_hash,
        expires_at=expires_at,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.add(token)
    await db.commit()
    await db.refresh(token)
    return token


async def get_refresh_token_by_hash(
    db: AsyncSession, token_hash: str
) -> RefreshToken | None:
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    return result.scalar_one_or_none()


async def revoke_refresh_token(db: AsyncSession, token: RefreshToken) -> None:
    token.is_revoked = True
    await db.commit()


async def revoke_all_user_refresh_tokens(db: AsyncSession, user_id: int) -> None:
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.user_id == user_id,
            RefreshToken.is_revoked.is_(False),
        )
    )
    tokens = result.scalars().all()
    for t in tokens:
        t.is_revoked = True
    await db.commit()