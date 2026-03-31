from pydantic import BaseModel

from app.domain.models import UserProfileSnapshot


class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    email: str | None = None
    password: str


class AuthResponse(BaseModel):
    token: str
    user: UserProfileSnapshot
