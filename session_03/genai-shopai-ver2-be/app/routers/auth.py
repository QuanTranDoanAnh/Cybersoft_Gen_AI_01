from fastapi import APIRouter, Depends, HTTPException, status

from app.schemas.auth import AuthResponse, LoginRequest, RegisterRequest, UserPublic
from app.services import auth_service

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _auth_response(user: dict) -> AuthResponse:
    return AuthResponse(access_token=auth_service.create_access_token(user["id"]), user=UserPublic(**user))


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest):
    try:
        user = auth_service.register_user(payload.email, payload.password, payload.display_name)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return _auth_response(user)


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest):
    user = auth_service.authenticate_user(payload.email, payload.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Email hoặc mật khẩu không đúng.")
    return _auth_response(user)


@router.get("/me", response_model=UserPublic)
def me(user: dict = Depends(auth_service.require_user)):
    return UserPublic(**user)
