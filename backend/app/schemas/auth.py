"""Auth request/response shapes."""

from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field

from app.core.security import StrongPassword


class LoginRequest(BaseModel):
    email: EmailStr
    # Login stays loose — policy is enforced only when *setting* a password.
    password: str = Field(min_length=1, max_length=128)


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds (900 for 15 min)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: StrongPassword


class ChangePasswordRequest(BaseModel):
    """Self-service password change (api-contract.md §1.7).

    Requires the *current* password for verification.
    """

    current_password: str = Field(min_length=1, max_length=128)
    new_password: StrongPassword
