from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[1]
ROOT_DIR = BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(ROOT_DIR / ".env", BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        # "AUTH_USUARIO=" (vazio) no .env usa o valor padrão em vez de uma string vazia.
        env_ignore_empty=True,
    )

    # A Gemini API Key NÃO fica no servidor: o usuário informa na tela e ela chega a cada requisição.
    GEMINI_MODEL: str = "gemini-3.6-flash"
    GEMINI_TIMEOUT_SECONDS: int = 120  # limite de cada chamada ao Gemini
    # 1 = sem retentativas: cada extração faz no máximo 1 chamada ao Gemini (cotas gratuitas são de poucas por minuto).
    GEMINI_MAX_TENTATIVAS: int = 1  # 1 chamada + retentativas em erros 5xx transitórios
    # Nível de raciocínio ("thinking") do modelo: minimal/low/medium/high. Tokens de raciocínio são cobrados e
    # contam na cota; para extrair dados o mínimo basta. Vazio = padrão do modelo (modelos anteriores ao Gemini 3
    # não aceitam este parâmetro).
    GEMINI_NIVEL_RACIOCINIO: str = "minimal"
    # Tempo máximo de uma extração inteira (todas as chamadas e retentativas somadas). O frontend espera um
    # pouco mais que isso (EXTRACTION_TIMEOUT_MS em notaFiscalService.ts); se aumentar aqui, aumente lá também.
    GEMINI_TEMPO_MAXIMO_SECONDS: int = 240

    API_KEY: str = ""

    # Login da aplicação (credenciais de avaliação; troque em produção pelas variáveis de ambiente).
    AUTH_USUARIO: str = "professor"
    AUTH_SENHA: str = "avaliacao123"
    # Segredo que assina os tokens de sessão. Vazio = gerado ao iniciar (sessões caem a cada reinício).
    AUTH_SECRET: str = ""
    AUTH_SESSAO_HORAS: int = 8

    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"
    MAX_UPLOAD_MB: int = 10

    RATE_LIMIT_EXTRACAO: str = "5/minute"
    RATE_LIMIT_LOGIN: str = "10/minute"
    RATE_LIMIT_VALIDACAO: str = "20/minute"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def max_upload_bytes(self) -> int:
        return self.MAX_UPLOAD_MB * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()
