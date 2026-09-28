from fastapi import APIRouter, Depends

from app.api import notas_fiscais
from app.security import require_api_key

api_router = APIRouter(prefix="/api")


@api_router.get("/health", tags=["Sistema"])
def health() -> dict[str, str]:
    return {"status": "ok"}


api_router.include_router(notas_fiscais.router, dependencies=[Depends(require_api_key)])
