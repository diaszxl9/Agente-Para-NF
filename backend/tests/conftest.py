import pytest
from fastapi.testclient import TestClient

from app.api.gemini import get_gemini_service
from app.auth import criar_token
from app.config import get_settings
from app.main import app
from app.rate_limit import limiter
from app.services.gemini_service import GeminiError

PDF_MINIMO = b"%PDF-1.4\n1 0 obj<</Type/Catalog>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF\n"


class FakeGemini:
    model = "gemini-fake"

    def __init__(self, respostas: list[str] | None = None, erro: GeminiError | None = None):
        self.respostas = list(respostas or [])
        self.erro = erro
        self.chamadas = 0
        self.ultimo_prompt = ""

    def validar_chave(self) -> bool:
        self.chamadas += 1
        if self.erro:
            raise self.erro
        return self.respostas.pop(0) == "valida"

    def gerar_json(self, pdf_bytes: bytes, prompt: str) -> str:
        self.chamadas += 1
        self.ultimo_prompt = prompt
        if self.erro:
            raise self.erro
        return self.respostas.pop(0)


@pytest.fixture(autouse=True)
def limiter_zerado():
    """O contador do rate limit é global (memória do processo): zera para um teste não afetar o outro."""
    limiter.reset()
    yield


def auth_headers() -> dict[str, str]:
    token, _ = criar_token(get_settings().AUTH_USUARIO, get_settings())
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def client():
    """Cliente já autenticado (login feito). Use `anonimo` para testar requisições sem sessão."""
    with TestClient(app, headers=auth_headers()) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def anonimo():
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def usar_gemini():
    def _usar(fake: FakeGemini) -> FakeGemini:
        app.dependency_overrides[get_gemini_service] = lambda: fake
        return fake

    return _usar
