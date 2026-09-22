from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address


def _chave_cliente(request: Request) -> str:
    """Agrupa por API key quando presente; senão, por IP (evita punir um escritório
    inteiro atrás do mesmo IP quando a API está protegida por chave)."""
    api_key = request.headers.get("x-api-key")
    return f"key:{api_key}" if api_key else get_remote_address(request)


limiter = Limiter(key_func=_chave_cliente)
