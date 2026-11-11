from fastapi import APIRouter, Depends

router = APIRouter()

from fastapi import APIRouter, Depends

router = APIRouter()

# ==========================================
# 1. OTP ENGINE (Unified Hub)
# ==========================================

@router.post("/request_otp/sms")
async def request_otp_for_phonenumber():
    """
    Accepts phone number and purpose (registration, update, reset).
    Caches the code under a unique composite key and dispatches SMS.
    """
    pass

@router.post("/request_otp/email")
async def request_otp_for_email():
    """
    Accepts email address and purpose (registration, update, reset).
    Caches the code under a unique composite key and dispatches Email.
    """
    pass

# ==========================================
# 2. REGISTRATION PIPELINE
# ==========================================

@router.post("/sign_up/phone")
async def sign_up_phone_request():
    """Verifies cached registration OTP, commits new User to DB."""
    pass

@router.post("/sign_up/email")
async def sign_up_email_request():
    """Verifies cached registration OTP, commits new User to DB."""
    pass

# ==========================================
# 3. SESSION LIFECYCLE
# ==========================================

@router.post("/login")
async def login_request():
    pass

@router.post("/refresh-token")
async def request_access_token():
    pass

@router.post("/logout")
async def logout_request():
    pass

# ==========================================
# 4. PROFILE & ACCOUNT SECURITY
# ==========================================

@router.get("/me")
async def get_my_profile():
    """Fetches profile metrics for the logged-in user."""
    pass

@router.patch("/me")
async def change_my_profile():
    """
    Safely handles basic non-critical metadata updates ONLY 
    (e.g., updating full_name or user preferences).
    """
    pass

@router.put("/change_password")
async def change_my_password():
    """Validates the old password before hashing and saving the new one."""
    pass

@router.put("/change_phone")
async def change_my_phone():
    """
    Validates the provided change profile OTP against the cache 
    before committing the new phone number to the Users table.
    """
    pass

@router.put("/change_email")
async def change_my_email():
    """
    Validates the provided change profile OTP against the cache 
    before committing the new email to the Users table.
    """
    pass