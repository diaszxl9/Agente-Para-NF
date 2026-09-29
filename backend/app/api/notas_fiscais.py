import logging
from pathlib import PurePosixPath

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from pydantic import BaseModel

from app.api.gemini import get_gemini_service
from app.config import Settings, get_settings
from app.rate_limit import limiter
from app.schemas.nota_fiscal import ExtracaoResponse
from app.services.categorias import CATEGORIAS
from app.services.extraction_service import extrair_nota_fiscal
from app.services.gemini_service import GeminiService
from app.services.sanitize import clean_text

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/notas-fiscais", tags=["Notas Fiscais"])

PDF_CONTENT_TYPES = {"application/pdf", "application/x-pdf", "application/octet-stream"}
MULTIPART_OVERHEAD_BYTES = 1024 * 1024


def _nome_seguro(filename: str | None) -> str:
    base = PurePosixPath((filename or "").replace("\\", "/")).name
    return clean_text(base, 200) or "nota-fiscal.pdf"


def validar_pdf(nome: str, content_type: str | None, data: bytes) -> None:
    if not nome.lower().endswith(".pdf"):
        raise HTTPException(status_code=415, detail="Envie um arquivo com extensão .pdf.")
    if content_type and content_type.split(";")[0].strip().lower() not in PDF_CONTENT_TYPES:
        raise HTTPException(status_code=415, detail="O tipo do arquivo não é PDF.")
    if not data:
        raise HTTPException(status_code=400, detail="O arquivo enviado está vazio.")
    if not data.startswith(b"%PDF-"):
        raise HTTPException(status_code=415, detail="O conteúdo do arquivo não é um PDF válido.")


class LimitesResponse(BaseModel):
    max_upload_mb: int


@router.get("/limites", response_model=LimitesResponse)
def limites(settings: Settings = Depends(get_settings)) -> LimitesResponse:
    """Limites configurados no servidor, para o frontend validar o arquivo antes de enviar."""
    return LimitesResponse(max_upload_mb=settings.MAX_UPLOAD_MB)


@router.post("/extrair", response_model=ExtracaoResponse)
@limiter.limit(lambda: get_settings().RATE_LIMIT_EXTRACAO)
def extrair(
    request: Request,
    arquivo: UploadFile = File(..., description="PDF da nota fiscal"),
    settings: Settings = Depends(get_settings),
    gemini: GeminiService = Depends(get_gemini_service),
) -> ExtracaoResponse:
    limite = settings.max_upload_bytes
    declarado = request.headers.get("content-length")
    if declarado and declarado.isdigit() and int(declarado) > limite + MULTIPART_OVERHEAD_BYTES:
        raise HTTPException(status_code=413, detail=f"O arquivo excede o limite de {settings.MAX_UPLOAD_MB} MB.")

    nome = _nome_seguro(arquivo.filename)
    data = arquivo.file.read(limite + 1)
    if len(data) > limite:
        raise HTTPException(status_code=413, detail=f"O arquivo excede o limite de {settings.MAX_UPLOAD_MB} MB.")
    validar_pdf(nome, arquivo.content_type, data)

    return extrair_nota_fiscal(data, nome, gemini, CATEGORIAS)
