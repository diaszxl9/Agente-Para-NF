import pytest
from fastapi.testclient import TestClient

from app.api.notas_fiscais import get_gemini_service
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


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def usar_gemini():
    def _usar(fake: FakeGemini) -> FakeGemini:
        app.dependency_overrides[get_gemini_service] = lambda: fake
        return fake

    return _usar
