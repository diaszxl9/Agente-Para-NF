import logging
import time

from google import genai
from google.genai import errors, types

from app.config import Settings

logger = logging.getLogger(__name__)

# Erros transitórios do lado do Google (ex.: 503 "high demand"): vale tentar de novo.
_CODIGOS_TRANSITORIOS = {500, 502, 503, 504}
_ESPERA_INICIAL_S = 1.0
_ESPERA_MAXIMA_S = 8.0


class GeminiError(Exception):
    """Erro de comunicação com o Gemini, já com mensagem apresentável ao usuário."""

    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class GeminiService:
    def __init__(self, settings: Settings):
        self.model = settings.GEMINI_MODEL
        self._api_key = settings.GEMINI_API_KEY
        self._timeout_ms = settings.GEMINI_TIMEOUT_SECONDS * 1000
        self._tentativas = max(1, settings.GEMINI_MAX_TENTATIVAS)
        self._client: genai.Client | None = None

    def _get_client(self) -> genai.Client:
        if not self._api_key:
            raise GeminiError(
                "GEMINI_API_KEY não configurada no servidor. Defina a variável no arquivo .env.",
                status_code=503,
            )
        if self._client is None:
            self._client = genai.Client(
                api_key=self._api_key,
                http_options=types.HttpOptions(timeout=self._timeout_ms),
            )
        return self._client

    def gerar_json(self, pdf_bytes: bytes, prompt: str) -> str:
        """Envia o PDF + prompt e devolve o texto bruto retornado pela IA."""
        client = self._get_client()
        espera = _ESPERA_INICIAL_S
        for tentativa in range(1, self._tentativas + 1):
            try:
                response = client.models.generate_content(
                    model=self.model,
                    contents=[types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"), prompt],
                    config=types.GenerateContentConfig(
                        temperature=0,
                        response_mime_type="application/json",
                    ),
                )
                break
            except errors.APIError as exc:
                logger.warning("Erro da API Gemini: code=%s (tentativa %s/%s)", exc.code, tentativa, self._tentativas)
                if exc.code in _CODIGOS_TRANSITORIOS and tentativa < self._tentativas:
                    time.sleep(espera)
                    espera = min(espera * 2, _ESPERA_MAXIMA_S)
                    continue
                if exc.code == 429:
                    raise GeminiError("Limite de uso do Gemini atingido. Tente novamente em instantes.", 429) from exc
                if exc.code in (401, 403):
                    raise GeminiError("A chave do Gemini foi recusada. Verifique GEMINI_API_KEY.", 502) from exc
                if exc.code == 404:
                    raise GeminiError(
                        f"Modelo '{self.model}' não encontrado. Ajuste GEMINI_MODEL no .env.", 502
                    ) from exc
                if exc.code == 400:
                    raise GeminiError("O Gemini não conseguiu processar este PDF.", 422) from exc
                raise GeminiError("O serviço de IA está indisponível no momento. Tente novamente.", 502) from exc
            except Exception as exc:  # timeout, rede, etc.
                logger.exception("Falha ao chamar o Gemini")
                raise GeminiError("Não foi possível se comunicar com o serviço de IA.", 502) from exc

        text = response.text
        if not text or not text.strip():
            raise GeminiError("O Gemini não retornou conteúdo para este documento.", 502)
        return text
