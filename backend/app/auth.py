"""Login simples da aplicação: um usuário configurado no .env e um token de sessão assinado (HMAC).

O token é stateless (não há sessão guardada no servidor), então funciona com vários processos/instâncias
desde que todos usem o mesmo AUTH_SECRET.
"""

import base64
import hashlib
import hmac
import json
import secrets
import time

from fastapi import Depends, Header, HTTPException

from app.config import Settings, get_settings

# Usado somente quando AUTH_SECRET não está definido: tokens deixam de valer quando o processo reinicia.
_SEGREDO_PROCESSO = secrets.token_bytes(32)


def _segredo(settings: Settings) -> bytes:
    return settings.AUTH_SECRET.encode() if settings.AUTH_SECRET else _SEGREDO_PROCESSO


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64_decode(texto: str) -> bytes:
    return base64.urlsafe_b64decode(texto + "=" * (-len(texto) % 4))


def _assinar(payload: str, settings: Settings) -> str:
    return _b64(hmac.new(_segredo(settings), payload.encode(), hashlib.sha256).digest())


def credenciais_configuradas(settings: Settings) -> bool:
    return bool(settings.AUTH_USUARIO.strip() and settings.AUTH_SENHA)


def credenciais_validas(usuario: str, senha: str, settings: Settings) -> bool:
    # Sem credenciais configuradas, ninguém entra (nem com usuário e senha vazios).
    if not credenciais_configuradas(settings) or not usuario.strip() or not senha:
        return False
    usuario_ok = hmac.compare_digest(usuario.strip().lower().encode(), settings.AUTH_USUARIO.strip().lower().encode())
    senha_ok = hmac.compare_digest(senha.encode(), settings.AUTH_SENHA.encode())
    return usuario_ok and senha_ok


def criar_token(usuario: str, settings: Settings) -> tuple[str, int]:
    """Devolve (token, expiração em epoch segundos)."""
    expira_em = int(time.time()) + settings.AUTH_SESSAO_HORAS * 3600
    payload = _b64(json.dumps({"sub": usuario, "exp": expira_em}).encode())
    return f"{payload}.{_assinar(payload, settings)}", expira_em


def ler_token(token: str, settings: Settings) -> str | None:
    """Devolve o usuário do token, ou None se a assinatura for inválida ou a sessão tiver expirado."""
    payload, _, assinatura = token.partition(".")
    if not payload or not assinatura or not hmac.compare_digest(assinatura, _assinar(payload, settings)):
        return None
    try:
        dados = json.loads(_b64_decode(payload))
    except ValueError:
        return None
    if not isinstance(dados, dict) or not isinstance(dados.get("exp"), int) or dados["exp"] < time.time():
        return None
    usuario = dados.get("sub")
    return usuario if isinstance(usuario, str) else None


def require_usuario(
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> str:
    esquema, _, token = (authorization or "").partition(" ")
    usuario = ler_token(token.strip(), settings) if esquema.lower() == "bearer" else None
    if not usuario:
        raise HTTPException(status_code=401, detail="Sessão expirada ou inválida. Faça login novamente.")
    return usuario
