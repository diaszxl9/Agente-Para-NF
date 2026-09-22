from fastapi import APIRouter, Depends

from app.api import cadastros, dashboard, notas_fiscais
from app.security import require_api_key

api_router = APIRouter(prefix="/api")


@api_router.get("/health", tags=["Sistema"])
def health() -> dict[str, str]:
    return {"status": "ok"}


_protegido = [Depends(require_api_key)]

api_router.include_router(notas_fiscais.router, dependencies=_protegido)
api_router.include_router(dashboard.router, dependencies=_protegido)
for router in cadastros.routers:
    api_router.include_router(router, dependencies=_protegido)
