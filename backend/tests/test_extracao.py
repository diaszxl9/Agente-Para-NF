import json

from tests.conftest import PDF_MINIMO, FakeGemini

from app.services.gemini_service import GeminiError

JSON_OK = {
    "fornecedor": {"razao_social": "EMPRESA FORNECEDORA LTDA", "fantasia": "EMPRESA FORNECEDORA", "cnpj": "11222333000181"},
    "faturado": {"nome_completo": "CLIENTE EXEMPLO", "cpf": "52998224725"},
    "nota_fiscal": {"numero": "123456", "data_emissao": "21/09/2026"},
    "itens": [{"descricao": "Óleo Diesel S10", "quantidade": "100,00"}],
    "parcelas": [{"numero": 1, "data_vencimento": "2026-10-21", "valor": 2500.0}],
    "valor_total": 2500.0,
    "despesas": [{"categoria": "manutencao e operacao", "subcategoria": "Combustíveis e Lubrificantes"}],
}


def enviar(client, conteudo=PDF_MINIMO, nome="nf.pdf", tipo="application/pdf", headers=None):
    return client.post(
        "/api/notas-fiscais/extrair", files={"arquivo": (nome, conteudo, tipo)}, headers=headers
    )


def test_extracao_sucesso(client, usar_gemini):
    fake = usar_gemini(FakeGemini([json.dumps(JSON_OK)]))
    r = enviar(client)
    assert r.status_code == 200, r.text
    body = r.json()
    dados = body["dados"]
    assert dados["fornecedor"]["cnpj"] == "11.222.333/0001-81"
    assert dados["faturado"]["cpf"] == "529.982.247-25"
    assert dados["nota_fiscal"] == {"numero": "123456", "data_emissao": "2026-09-21"}
    assert dados["itens"] == [{"descricao": "Óleo Diesel S10", "quantidade": 100.0}]
    assert dados["valor_total"] == 2500.0
    assert dados["parcelas"] == [{"numero": 1, "data_vencimento": "2026-10-21", "valor": 2500.0}]
    assert dados["despesas"] == [{"categoria": "MANUTENÇÃO E OPERAÇÃO", "subcategoria": "Combustíveis e Lubrificantes"}]
    assert body["arquivo"] == {"nome": "nf.pdf", "tamanho_bytes": len(PDF_MINIMO)}
    assert "INSUMOS AGRÍCOLAS" in fake.ultimo_prompt  # categorias permitidas vão no prompt


def test_categoria_inventada_pela_ia_e_descartada(client, usar_gemini):
    dados = {**JSON_OK, "despesas": [{"categoria": "COISAS ALEATÓRIAS", "subcategoria": "Nada"}]}
    usar_gemini(FakeGemini([json.dumps(dados)]))
    assert enviar(client).json()["dados"]["despesas"] == []


def test_categoria_inferida_pela_subcategoria(client, usar_gemini):
    dados = {**JSON_OK, "despesas": [{"categoria": None, "subcategoria": "Sementes"}]}
    usar_gemini(FakeGemini([json.dumps(dados)]))
    assert enviar(client).json()["dados"]["despesas"] == [{"categoria": "INSUMOS AGRÍCOLAS", "subcategoria": "Sementes"}]


def test_sem_parcelas_gera_uma_parcela_com_o_total(client, usar_gemini):
    dados = {**JSON_OK, "parcelas": []}
    usar_gemini(FakeGemini([json.dumps(dados)]))
    assert enviar(client).json()["dados"]["parcelas"] == [{"numero": 1, "data_vencimento": None, "valor": 2500.0}]


def test_campos_ausentes_ficam_null_e_nada_e_inventado(client, usar_gemini):
    usar_gemini(FakeGemini(["{}"]))
    dados = enviar(client).json()["dados"]
    assert dados["fornecedor"] == {"razao_social": None, "fantasia": None, "cnpj": None}
    assert dados["valor_total"] is None
    assert dados["parcelas"] == [] and dados["itens"] == []


def test_json_em_cerca_markdown_e_aceito(client, usar_gemini):
    usar_gemini(FakeGemini(["```json\n" + json.dumps(JSON_OK) + "\n```"]))
    assert enviar(client).status_code == 200


def test_json_invalido_tenta_de_novo_e_depois_falha(client, usar_gemini):
    fake = usar_gemini(FakeGemini(["isto não é json", "nem isto"]))
    r = enviar(client)
    assert r.status_code == 502
    assert fake.chamadas == 2
    assert "inválida" in r.json()["detail"]


def test_json_invalido_na_primeira_e_valido_na_segunda(client, usar_gemini):
    fake = usar_gemini(FakeGemini(["lixo", json.dumps(JSON_OK)]))
    assert enviar(client).status_code == 200
    assert fake.chamadas == 2


def test_erro_do_gemini_e_repassado_sem_vazar_detalhes(client, usar_gemini):
    usar_gemini(FakeGemini(erro=GeminiError("Limite de uso do Gemini atingido.", 429)))
    r = enviar(client)
    assert r.status_code == 429
    assert r.json()["detail"] == "Limite de uso do Gemini atingido."


def test_rejeita_extensao_errada(client, usar_gemini):
    fake = usar_gemini(FakeGemini())
    assert enviar(client, nome="nf.txt", tipo="text/plain").status_code == 415
    assert fake.chamadas == 0


def test_rejeita_conteudo_que_nao_e_pdf(client, usar_gemini):
    fake = usar_gemini(FakeGemini())
    assert enviar(client, conteudo=b"MZ\x90\x00 executavel", nome="nf.pdf").status_code == 415
    assert fake.chamadas == 0


def test_rejeita_arquivo_vazio(client, usar_gemini):
    usar_gemini(FakeGemini())
    assert enviar(client, conteudo=b"").status_code == 400


def test_rejeita_arquivo_acima_do_limite(client, usar_gemini, monkeypatch):
    from app.config import get_settings

    usar_gemini(FakeGemini())
    monkeypatch.setattr(get_settings(), "MAX_UPLOAD_MB", 1)
    grande = b"%PDF-" + b"0" * (1024 * 1024 + 10)
    assert enviar(client, conteudo=grande).status_code == 413


def test_nome_do_arquivo_e_sanitizado(client, usar_gemini):
    usar_gemini(FakeGemini([json.dumps(JSON_OK)]))
    r = enviar(client, nome="..\\..\\pasta\\nf.pdf")
    assert r.json()["arquivo"]["nome"] == "nf.pdf"


def test_sem_chave_gemini_retorna_503(client, monkeypatch):
    from app.config import get_settings

    monkeypatch.setattr(get_settings(), "GEMINI_API_KEY", "")
    from app.api.notas_fiscais import get_gemini_service

    get_gemini_service.cache_clear()
    r = enviar(client)
    assert r.status_code == 503
    assert "GEMINI_API_KEY" in r.json()["detail"]
    get_gemini_service.cache_clear()


def test_rate_limit_bloqueia_apos_o_limite(client, usar_gemini, monkeypatch):
    from app.config import get_settings

    monkeypatch.setattr(get_settings(), "RATE_LIMIT_EXTRACAO", "2/minute")
    fake = usar_gemini(FakeGemini([json.dumps(JSON_OK), json.dumps(JSON_OK)]))

    assert enviar(client).status_code == 200
    assert enviar(client).status_code == 200
    bloqueado = enviar(client)
    assert bloqueado.status_code == 429
    assert fake.chamadas == 2  # a 3ª requisição nem chega a chamar o Gemini


def test_rate_limit_nao_e_burlado_com_x_api_key_aleatorio(client, usar_gemini, monkeypatch):
    """Sem API_KEY configurada, variar o header X-API-Key não pode gerar um bucket novo a cada requisição."""
    from app.config import get_settings

    assert get_settings().API_KEY == ""
    monkeypatch.setattr(get_settings(), "RATE_LIMIT_EXTRACAO", "2/minute")
    fake = usar_gemini(FakeGemini([json.dumps(JSON_OK), json.dumps(JSON_OK)]))

    assert enviar(client, headers={"X-API-Key": "falsa-1"}).status_code == 200
    assert enviar(client, headers={"X-API-Key": "falsa-2"}).status_code == 200
    assert enviar(client, headers={"X-API-Key": "falsa-3"}).status_code == 429
    assert fake.chamadas == 2
