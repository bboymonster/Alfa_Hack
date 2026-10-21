from datetime import UTC, datetime, timedelta
from typing import Annotated
from uuid import uuid4

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.schemas import LoginRequest, RegisterRequest, TokenResponse, User
from app.store import StoredUser, password_hash

router = APIRouter(prefix="/api/auth", tags=["Авторизация"])
bearer = HTTPBearer(auto_error=False)


def unauthorized() -> HTTPException:
    return HTTPException(
        status_code=401,
        detail="Нужен действующий Bearer-токен. Войдите через /api/auth/login.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def current_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> User:
    if credentials is None:
        raise unauthorized()
    try:
        payload = jwt.decode(
            credentials.credentials,
            request.app.state.settings.jwt_secret_key,
            algorithms=["HS256"],
            options={"require": ["sub", "exp", "iat"]},
        )
    except jwt.InvalidTokenError:
        raise unauthorized() from None
    stored = request.app.state.store.user_by_id(payload["sub"])
    if stored is None:
        raise unauthorized()
    return stored.profile


CurrentUser = Annotated[User, Depends(current_user)]


def issue_token(request: Request, user: User) -> TokenResponse:
    settings = request.app.state.settings
    now = datetime.now(UTC)
    seconds = settings.access_token_expire_minutes * 60
    token = jwt.encode(
        {"sub": user.id, "iat": now, "exp": now + timedelta(seconds=seconds)},
        settings.jwt_secret_key,
        algorithm="HS256",
    )
    return TokenResponse(access_token=token, expires_in=seconds, user=user)


@router.post("/login", response_model=TokenResponse, summary="Войти и получить JWT")
def login(body: LoginRequest, request: Request) -> TokenResponse:
    store = request.app.state.store
    stored = store.users.get(body.email.casefold())
    hashed = stored.hashed_password if stored else store.dummy_password_hash
    valid = password_hash.verify(body.password, hashed)
    if stored is None or not valid:
        raise HTTPException(
            status_code=401,
            detail="Неверный логин или пароль.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return issue_token(request, stored.profile)


@router.post(
    "/register", response_model=TokenResponse, status_code=201, summary="Создать демо-аккаунт"
)
def register(body: RegisterRequest, request: Request) -> TokenResponse:
    store = request.app.state.store
    if body.company_id not in store.companies:
        raise HTTPException(status_code=404, detail="Компания не найдена.")
    email = str(body.email).casefold()
    hashed = password_hash.hash(body.password)
    with store.lock:
        if email in store.users:
            raise HTTPException(status_code=409, detail="Этот email уже зарегистрирован.")
        user = User(
            id=str(uuid4()),
            email=email,
            full_name=body.full_name,
            role=body.role,
            current_company_id=body.company_id,
            allowed_company_ids=[body.company_id],
        )
        store.users[email] = StoredUser(profile=user, hashed_password=hashed)
    return issue_token(request, user)


@router.get("/me", response_model=User, summary="Получить профиль текущего пользователя")
def me(user: CurrentUser) -> User:
    return user
