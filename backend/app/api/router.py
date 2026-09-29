from fastapi import APIRouter, Depends

from app.api import auth, gemini, notas_fiscais
from app.auth import require_usuario
from app.security import require_api_key

api_router = APIRouter(prefix="/api")


@api_router.get("/health", tags=["Sistema"])
def health() -> dict[str, str]:
    return {"status": "ok"}


api_router.include_router(auth.router, dependencies=[Depends(require_api_key)])

_protegidas = [Depends(require_api_key), Depends(require_usuario)]
api_router.include_router(gemini.router, dependencies=_protegidas)
api_router.include_router(notas_fiscais.router, dependencies=_protegidas)
