import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from sqlalchemy.exc import IntegrityError, InterfaceError, OperationalError

from app.api.router import api_router
from app.config import get_settings
from app.database.session import init_db
from app.rate_limit import limiter
from app.services.gemini_service import GeminiError

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    if not get_settings().API_KEY:
        logger.warning(
            "API_KEY não configurada: a API está acessível sem autenticação. "
            "Defina API_KEY no .env para exigir o header X-API-Key."
        )
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Gestão Financeira — Extração de NF com IA", version="0.1.0", lifespan=lifespan)

    app.state.limiter = limiter

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_methods=["GET", "POST", "PUT", "PATCH", "OPTIONS"],
        allow_headers=["*"],
    )

    @app.exception_handler(GeminiError)
    async def gemini_error_handler(_: Request, exc: GeminiError):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})

    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_handler(_: Request, __: RateLimitExceeded):
        return JSONResponse(
            status_code=429, content={"detail": "Muitas requisições em pouco tempo. Aguarde e tente novamente."}
        )

    @app.exception_handler(IntegrityError)
    async def integrity_error_handler(_: Request, __: IntegrityError):
        return JSONResponse(
            status_code=409, content={"detail": "Já existe um registro com estes dados (valor duplicado)."}
        )

    @app.exception_handler(OperationalError)
    @app.exception_handler(InterfaceError)
    async def db_unavailable_handler(_: Request, exc: Exception):
        logger.warning("Banco de dados indisponível: %s", exc.__class__.__name__)
        return JSONResponse(
            status_code=503, content={"detail": "Banco de dados indisponível. Verifique o MySQL e o DATABASE_URL."}
        )

    @app.exception_handler(Exception)
    async def unhandled_handler(_: Request, exc: Exception):
        logger.exception("Erro não tratado", exc_info=exc)
        return JSONResponse(status_code=500, content={"detail": "Erro interno do servidor."})

    app.include_router(api_router)
    return app


app = create_app()
