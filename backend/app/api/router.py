from fastapi import APIRouter

from app.api import cadastros, dashboard, notas_fiscais

api_router = APIRouter(prefix="/api")


@api_router.get("/health", tags=["Sistema"])
def health() -> dict[str, str]:
    return {"status": "ok"}


api_router.include_router(notas_fiscais.router)
api_router.include_router(dashboard.router)
for router in cadastros.routers:
    api_router.include_router(router)
