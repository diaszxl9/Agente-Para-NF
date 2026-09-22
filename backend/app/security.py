import hmac

from fastapi import Depends, Header, HTTPException

from app.config import Settings, get_settings


def require_api_key(
    x_api_key: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> None:
    """Exige o header X-API-Key quando API_KEY está configurada no servidor.

    Sem API_KEY definida no .env, o acesso continua liberado (compatível com o
    comportamento atual) — defina API_KEY para proteger a API.
    """
    if not settings.API_KEY:
        return
    if not x_api_key or not hmac.compare_digest(x_api_key, settings.API_KEY):
        raise HTTPException(status_code=401, detail="Chave de API inválida ou ausente.")
