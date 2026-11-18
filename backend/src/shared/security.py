from pwdlib import PasswordHash

# Replaces the CryptContext from passlib
pwd_context = PasswordHash.recommended()

def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)