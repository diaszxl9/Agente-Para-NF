import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from app.api.router import api_router
from app.auth import credenciais_configuradas
from app.config import get_settings
from app.rate_limit import limiter
from app.services.gemini_service import GeminiError

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    if not credenciais_configuradas(settings):
        logger.error("AUTH_USUARIO/AUTH_SENHA não configurados: nenhum login será aceito. Defina-os no .env.")
    if not settings.AUTH_SECRET:
        logger.warning(
            "AUTH_SECRET não configurado: usando um segredo temporário, e as sessões de login deixam de valer "
            "quando o servidor reinicia. Defina AUTH_SECRET no ambiente de produção."
        )
    if not settings.API_KEY:
        logger.warning(
            "API_KEY não configurada: a API está acessível sem autenticação. "
            "Defina API_KEY no .env para exigir o header X-API-Key."
        )
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Extração de NF com IA", version="0.1.0", lifespan=lifespan)

    app.state.limiter = limiter

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )

    @app.exception_handler(GeminiError)
    async def gemini_error_handler(_: Request, exc: GeminiError):
        content = {"detail": exc.message}
        if exc.codigo:
            content["codigo"] = exc.codigo
        return JSONResponse(status_code=exc.status_code, content=content)

    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_handler(_: Request, __: RateLimitExceeded):
        return JSONResponse(
            status_code=429, content={"detail": "Muitas requisições em pouco tempo. Aguarde e tente novamente."}
        )

    @app.exception_handler(Exception)
    async def unhandled_handler(_: Request, exc: Exception):
        logger.exception("Erro não tratado", exc_info=exc)
        return JSONResponse(status_code=500, content={"detail": "Erro interno do servidor."})

    app.include_router(api_router)
    return app


app = create_app()
