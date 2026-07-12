from pydantic import BaseModel, EmailStr, Field


class UserPublic(BaseModel):
    id: str
    email: EmailStr
    display_name: str


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    display_name: str = Field(min_length=2, max_length=80)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserPublic
