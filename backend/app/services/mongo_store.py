"""Armazenamento documental opcional (MongoDB).

Só é usado se MONGODB_URL estiver definida. Qualquer falha é registrada e ignorada:
o MySQL continua sendo a fonte principal e a extração nunca depende do Mongo.
"""

import hashlib
import logging
from datetime import datetime, timezone
from typing import Any

from app.config import get_settings

logger = logging.getLogger(__name__)

_collection = None


def _get_collection():
    global _collection
    settings = get_settings()
    if not settings.MONGODB_URL:
        return None
    if _collection is None:
        from pymongo import MongoClient

        client = MongoClient(settings.MONGODB_URL, serverSelectionTimeoutMS=2000)
        _collection = client[settings.MONGODB_DB]["documentos_nf"]
    return _collection


def salvar_documento(
    nome_arquivo: str,
    pdf_bytes: bytes,
    resposta_gemini: str,
    json_processado: dict[str, Any] | None,
    modelo: str,
    status: str,
) -> str | None:
    try:
        collection = _get_collection()
        if collection is None:
            return None
        result = collection.insert_one(
            {
                "nome_arquivo": nome_arquivo,
                "tamanho_bytes": len(pdf_bytes),
                "sha256": hashlib.sha256(pdf_bytes).hexdigest(),
                "modelo": modelo,
                "resposta_gemini": resposta_gemini,
                "json_processado": json_processado,
                "status": status,
                "processado_em": datetime.now(timezone.utc),
            }
        )
        return str(result.inserted_id)
    except Exception:
        logger.warning("Não foi possível gravar o documento no MongoDB (ignorado).", exc_info=True)
        return None
