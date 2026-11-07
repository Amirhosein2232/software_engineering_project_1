from fastapi import APIRouter, Depends

router = APIRouter(prefix="/api/auth")

@router.post("/sign_up")
async def sign_up_request() :
    pass

@router.post("/request_otp_sms")
async def request_otp_for_phonenumber() :
    pass

@router.post("/request_otp_email")
async def request_otp_for_email() :
    pass

@router.post("/login")
async def login_request() :
    pass

@router.post("/logout")
async def logout_request() :
    pass

@router.get("/me")
async def get_my_profile() :
    pass

@router.patch("/me")
async def change_my_profile() :
    pass

@router.put("change_password")
async def change_my_password() :
    pass

@router.post("new_access_token")
async def request_access_token() :
    pass