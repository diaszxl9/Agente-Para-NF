import pytest
from google.genai import errors

from app.config import Settings
from app.services import gemini_service
from app.services.gemini_service import GeminiError, GeminiService


class _Resp:
    def __init__(self, text):
        self.text = text


class _FakeModels:
    def __init__(self, result):
        self.result = result
        self.kwargs = None

    def generate_content(self, **kwargs):
        self.kwargs = kwargs
        if isinstance(self.result, Exception):
            raise self.result
        return _Resp(self.result)


class _FakeClient:
    instance = None

    def __init__(self, **kwargs):
        self.init_kwargs = kwargs
        self.models = _FakeModels(_FakeClient.result)
        _FakeClient.instance = self


@pytest.fixture
def servico(monkeypatch):
    monkeypatch.setattr(gemini_service.genai, "Client", _FakeClient)
    monkeypatch.setattr(gemini_service.time, "sleep", lambda _s: None)
    return GeminiService(Settings(GEMINI_MODEL="modelo-x", _env_file=None), "chave-teste")


def test_envia_pdf_inline_com_json_e_temperatura_zero(servico):
    _FakeClient.result = '{"ok": true}'
    assert servico.gerar_json(b"%PDF-1.4 conteudo", "meu prompt") == '{"ok": true}'

    kwargs = _FakeClient.instance.models.kwargs
    assert kwargs["model"] == "modelo-x"
    parte_pdf, prompt = kwargs["contents"]
    assert parte_pdf.inline_data.mime_type == "application/pdf"
    assert parte_pdf.inline_data.data == b"%PDF-1.4 conteudo"
    assert prompt == "meu prompt"
    assert kwargs["config"].response_mime_type == "application/json"
    assert kwargs["config"].temperature == 0


@pytest.mark.parametrize(
    "codigo, status",
    [(429, 429), (401, 502), (403, 502), (404, 502), (400, 422), (500, 502)],
)
def test_mapeia_erros_da_api(servico, codigo, status):
    cls = errors.ClientError if codigo < 500 else errors.ServerError
    _FakeClient.result = cls(codigo, {"error": {"message": "segredo interno"}})
    with pytest.raises(GeminiError) as info:
        servico.gerar_json(b"%PDF-", "p")
    assert info.value.status_code == status
    assert "segredo interno" not in info.value.message


def test_falha_de_rede_vira_erro_amigavel(servico):
    _FakeClient.result = TimeoutError("timeout")
    with pytest.raises(GeminiError) as info:
        servico.gerar_json(b"%PDF-", "p")
    assert info.value.status_code == 502


def test_resposta_vazia(servico):
    _FakeClient.result = "   "
    with pytest.raises(GeminiError):
        servico.gerar_json(b"%PDF-", "p")


def test_sem_chave_nao_cria_cliente():
    servico = GeminiService(Settings(_env_file=None), "")
    with pytest.raises(GeminiError) as info:
        servico.gerar_json(b"%PDF-", "p")
    assert info.value.status_code == 400


def test_usa_a_chave_informada_pelo_usuario(servico):
    _FakeClient.result = '{"ok": true}'
    servico.gerar_json(b"%PDF-", "p")
    assert _FakeClient.instance.init_kwargs["api_key"] == "chave-teste"


def test_validar_chave_valida(servico, monkeypatch):
    chamadas = []
    monkeypatch.setattr(_FakeModels, "get", lambda self, **kw: chamadas.append(kw), raising=False)
    assert servico.validar_chave() is True
    assert chamadas[0]["model"] == "modelo-x"


@pytest.mark.parametrize("codigo", [400, 401, 403])
def test_validar_chave_recusada(servico, monkeypatch, codigo):
    def get(self, **kwargs):
        raise errors.ClientError(codigo, {"error": {"message": "API key not valid"}})

    monkeypatch.setattr(_FakeModels, "get", get, raising=False)
    assert servico.validar_chave() is False


@pytest.mark.parametrize(
    "erro, status",
    [
        (errors.ClientError(429, {"error": {"message": "quota"}}), 429),
        (errors.ServerError(503, {"error": {"message": "indisponivel"}}), 502),
        (ConnectionError("sem rede"), 502),
    ],
)
def test_validar_chave_erros_de_conexao_ou_api(servico, monkeypatch, erro, status):
    def get(self, **kwargs):
        raise erro

    monkeypatch.setattr(_FakeModels, "get", get, raising=False)
    with pytest.raises(GeminiError) as info:
        servico.validar_chave()
    assert info.value.status_code == status


def test_repete_em_503_transitorio_e_acaba_funcionando(servico, monkeypatch):
    respostas = [
        errors.ServerError(503, {"error": {"message": "high demand"}}),
        errors.ServerError(503, {"error": {"message": "high demand"}}),
        '{"ok": true}',
    ]

    def gerar(**kwargs):
        r = respostas.pop(0)
        if isinstance(r, Exception):
            raise r
        return _Resp(r)

    _FakeClient.result = None
    monkeypatch.setattr(_FakeModels, "generate_content", lambda self, **kw: gerar(**kw))
    assert servico.gerar_json(b"%PDF-", "p") == '{"ok": true}'
    assert respostas == []


def test_503_persistente_esgota_tentativas(servico, monkeypatch):
    chamadas = []

    def gerar(self, **kwargs):
        chamadas.append(1)
        raise errors.ServerError(503, {"error": {"message": "high demand"}})

    _FakeClient.result = None
    monkeypatch.setattr(_FakeModels, "generate_content", gerar)
    with pytest.raises(GeminiError) as info:
        servico.gerar_json(b"%PDF-", "p")
    assert info.value.status_code == 502
    assert len(chamadas) == 4


def test_erro_de_cliente_nao_e_repetido(servico, monkeypatch):
    chamadas = []

    def gerar(self, **kwargs):
        chamadas.append(1)
        raise errors.ClientError(400, {"error": {"message": "pdf ruim"}})

    _FakeClient.result = None
    monkeypatch.setattr(_FakeModels, "generate_content", gerar)
    with pytest.raises(GeminiError):
        servico.gerar_json(b"%PDF-", "p")
    assert len(chamadas) == 1


def test_chave_invalida_na_extracao_nao_vira_erro_de_pdf(servico):
    """O Gemini devolve 400 (API_KEY_INVALID) para chave inválida, não 401."""
    _FakeClient.result = errors.ClientError(
        400, {"error": {"message": "API key not valid. Please pass a valid API key.", "status": "INVALID_ARGUMENT"}}
    )
    with pytest.raises(GeminiError) as info:
        servico.gerar_json(b"%PDF-", "p")
    assert info.value.status_code == 502
    assert info.value.codigo == gemini_service.CODIGO_CHAVE_RECUSADA


def test_prazo_total_esgotado_nao_chama_o_gemini(servico, monkeypatch):
    chamadas = []
    monkeypatch.setattr(_FakeModels, "generate_content", lambda self, **kw: chamadas.append(1))
    servico._prazo = gemini_service.time.monotonic()  # prazo já vencido
    with pytest.raises(GeminiError) as info:
        servico.gerar_json(b"%PDF-", "p")
    assert info.value.status_code == 504
    assert chamadas == []


def test_timeout_da_chamada_respeita_o_prazo_restante(servico):
    _FakeClient.result = '{"ok": true}'
    servico._prazo = gemini_service.time.monotonic() + 30
    servico.gerar_json(b"%PDF-", "p")
    timeout = _FakeClient.instance.models.kwargs["config"].http_options.timeout
    assert 25_000 <= timeout <= 30_000


def test_nao_repete_503_se_o_prazo_nao_permite(servico, monkeypatch):
    chamadas = []

    def gerar(self, **kwargs):
        chamadas.append(1)
        servico._prazo = gemini_service.time.monotonic() + 3  # sobra menos que o mínimo para outra chamada
        raise errors.ServerError(503, {"error": {"message": "high demand"}})

    monkeypatch.setattr(_FakeModels, "generate_content", gerar)
    with pytest.raises(GeminiError):
        servico.gerar_json(b"%PDF-", "p")
    assert len(chamadas) == 1
