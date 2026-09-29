from fastapi import APIRouter, Depends, Header, Request
from pydantic import BaseModel

from app.config import Settings, get_settings
from app.rate_limit import limiter
from app.services.gemini_service import GeminiService

router = APIRouter(prefix="/gemini", tags=["Gemini"])


def get_gemini_service(
    x_gemini_api_key: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> GeminiService:
    """A chave vem do usuário (header X-Gemini-Api-Key) a cada requisição; o servidor não a guarda."""
    return GeminiService(settings, (x_gemini_api_key or "").strip())


class ValidacaoResponse(BaseModel):
    valida: bool
    mensagem: str


@router.post("/validar", response_model=ValidacaoResponse)
@limiter.limit(lambda: get_settings().RATE_LIMIT_VALIDACAO)
def validar(request: Request, gemini: GeminiService = Depends(get_gemini_service)) -> ValidacaoResponse:
    if gemini.validar_chave():
        return ValidacaoResponse(valida=True, mensagem="API Key válida.")
    return ValidacaoResponse(valida=False, mensagem="API Key inválida. Verifique a chave informada.")
