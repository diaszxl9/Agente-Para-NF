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

    def __init__(self, message: str, status_code: int = 502, codigo: str | None = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        # Identificador estável para o frontend reagir ao erro (ex.: pedir a chave de novo).
        self.codigo = codigo


# Enviado ao frontend quando o Gemini recusa a chave durante a extração.
CODIGO_CHAVE_RECUSADA = "gemini_api_key_recusada"

# A validação só consulta os metadados do modelo: resposta rápida e sem consumo de tokens.
_TIMEOUT_VALIDACAO_MS = 15_000
# Abaixo disso não vale começar uma nova chamada ao Gemini: ela não teria tempo de terminar.
_TEMPO_MINIMO_CHAMADA_S = 5.0


def _chave_invalida(exc: errors.APIError) -> bool:
    """Chave inexistente/malformada volta 400 (e não 401), com o motivo API_KEY_INVALID."""
    detalhes = f"{exc.message or ''} {getattr(exc, 'details', '')}".lower()
    return "api_key_invalid" in detalhes or "api key not valid" in detalhes


class GeminiService:
    """Cliente do Gemini com a API Key informada pelo usuário (nunca armazenada nem registrada em log).

    Uma instância é criada por requisição; o prazo total (GEMINI_TEMPO_MAXIMO_SECONDS) conta a partir daí e
    vale para todas as chamadas feitas por ela, inclusive retentativas.
    """

    def __init__(self, settings: Settings, api_key: str):
        self.model = settings.GEMINI_MODEL
        self._api_key = api_key
        self._timeout_s = float(settings.GEMINI_TIMEOUT_SECONDS)
        self._tentativas = max(1, settings.GEMINI_MAX_TENTATIVAS)
        nivel = settings.GEMINI_NIVEL_RACIOCINIO.strip()
        self._thinking = types.ThinkingConfig(thinking_level=nivel.upper()) if nivel else None
        self._prazo = time.monotonic() + settings.GEMINI_TEMPO_MAXIMO_SECONDS
        self._client: genai.Client | None = None

    def _tempo_restante(self) -> float:
        return self._prazo - time.monotonic()

    def _get_client(self) -> genai.Client:
        if not self._api_key:
            raise GeminiError("Informe e valide a Gemini API Key antes de continuar.", status_code=400)
        if self._client is None:
            self._client = genai.Client(
                api_key=self._api_key,
                http_options=types.HttpOptions(timeout=int(self._timeout_s * 1000)),
            )
        return self._client

    def validar_chave(self) -> bool:
        """Faz uma chamada de teste ao Gemini. False = chave recusada; demais falhas viram GeminiError."""
        client = self._get_client()
        try:
            client.models.get(
                model=self.model,
                config=types.GetModelConfig(http_options=types.HttpOptions(timeout=_TIMEOUT_VALIDACAO_MS)),
            )
        except errors.APIError as exc:
            logger.warning("Validação da API Key do Gemini recusada: code=%s", exc.code)
            # Chave inexistente/malformada volta 400 (API_KEY_INVALID); sem permissão, 401/403.
            if exc.code in (400, 401, 403):
                return False
            if exc.code == 429:
                raise GeminiError("Limite de uso do Gemini atingido. Tente novamente em instantes.", 429) from exc
            if exc.code == 404:
                raise GeminiError(
                    f"Modelo '{self.model}' não encontrado. Ajuste GEMINI_MODEL no servidor.", 502
                ) from exc
            raise GeminiError("O serviço do Gemini está indisponível no momento. Tente novamente.", 502) from exc
        except Exception as exc:  # timeout, DNS, rede, etc.
            logger.warning("Falha de conexão ao validar a API Key do Gemini: %s", type(exc).__name__)
            raise GeminiError(
                "Não foi possível se comunicar com o Gemini. Verifique a conexão e tente novamente.", 502
            ) from exc
        return True

    def gerar_json(self, pdf_bytes: bytes, prompt: str) -> str:
        """Envia o PDF + prompt e devolve o texto bruto retornado pela IA."""
        client = self._get_client()
        espera = _ESPERA_INICIAL_S
        for tentativa in range(1, self._tentativas + 1):
            restante = self._tempo_restante()
            if restante < _TEMPO_MINIMO_CHAMADA_S:
                raise GeminiError("A extração excedeu o tempo máximo. Tente novamente em instantes.", 504)
            timeout_ms = int(min(self._timeout_s, restante) * 1000)
            try:
                response = client.models.generate_content(
                    model=self.model,
                    contents=[types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"), prompt],
                    config=types.GenerateContentConfig(
                        temperature=0,
                        response_mime_type="application/json",
                        thinking_config=self._thinking,
                        http_options=types.HttpOptions(timeout=timeout_ms),
                    ),
                )
                break
            except errors.APIError as exc:
                logger.warning("Erro da API Gemini: code=%s (tentativa %s/%s)", exc.code, tentativa, self._tentativas)
                pode_repetir = tentativa < self._tentativas and self._tempo_restante() - espera >= _TEMPO_MINIMO_CHAMADA_S
                if exc.code in _CODIGOS_TRANSITORIOS and pode_repetir:
                    time.sleep(espera)
                    espera = min(espera * 2, _ESPERA_MAXIMA_S)
                    continue
                if exc.code == 429:
                    raise GeminiError("Limite de uso do Gemini atingido. Tente novamente em instantes.", 429) from exc
                if exc.code in (401, 403) or (exc.code == 400 and _chave_invalida(exc)):
                    raise GeminiError(
                        "A Gemini API Key foi recusada. Informe e valide a chave novamente.",
                        502,
                        codigo=CODIGO_CHAVE_RECUSADA,
                    ) from exc
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
