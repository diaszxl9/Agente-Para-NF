from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app.auth import credenciais_validas, criar_token
from app.config import Settings, get_settings
from app.rate_limit import limiter

router = APIRouter(prefix="/auth", tags=["Autenticação"])


class LoginRequest(BaseModel):
    usuario: str = Field(max_length=200)
    senha: str = Field(max_length=200)


class LoginResponse(BaseModel):
    token: str
    usuario: str
    expira_em: int


@router.post("/login", response_model=LoginResponse)
@limiter.limit(lambda: get_settings().RATE_LIMIT_LOGIN)
def login(request: Request, body: LoginRequest, settings: Settings = Depends(get_settings)) -> LoginResponse:
    if not credenciais_validas(body.usuario, body.senha, settings):
        raise HTTPException(status_code=401, detail="Usuário ou senha inválidos.")
    token, expira_em = criar_token(settings.AUTH_USUARIO, settings)
    return LoginResponse(token=token, usuario=settings.AUTH_USUARIO, expira_em=expira_em)
