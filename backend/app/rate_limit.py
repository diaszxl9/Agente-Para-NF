import hmac

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import get_settings


def _chave_cliente(request: Request) -> str:
    """Agrupa pela API key somente quando ela é a chave configurada no servidor; senão, por IP.

    O header X-API-Key nunca pode ser usado como chave do bucket sem validação: sem API_KEY configurada
    (ou com um valor qualquer), um cliente burlaria o limite enviando um valor diferente a cada requisição.
    """
    configurada = get_settings().API_KEY
    enviada = request.headers.get("x-api-key")
    if configurada and enviada and hmac.compare_digest(enviada, configurada):
        return "api-key"
    return get_remote_address(request)


limiter = Limiter(key_func=_chave_cliente)
