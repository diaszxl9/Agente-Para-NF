import copy

import pytest

from app.db import conectar

NOTA = {
    "fornecedor": {"razao_social": "IGUAÇU MÁQUINAS LTDA", "fantasia": "IGUAÇU", "cnpj": "11.222.333/0001-81"},
    "faturado": {"nome_completo": "BELTRANO DA SILVA", "cpf": "529.982.247-25"},
    "nota_fiscal": {"numero": "123456", "data_emissao": "2026-09-21"},
    "itens": [{"descricao": "Óleo Diesel S10", "quantidade": 100}, {"descricao": "Filtro", "quantidade": 1}],
    "parcelas": [
        {"numero": 1, "data_vencimento": "2026-10-21", "valor": 1500.0},
        {"numero": 2, "data_vencimento": "2026-11-21", "valor": 1000.0},
    ],
    "valor_total": 2500.0,
    "despesas": [
        {"categoria": "MANUTENÇÃO E OPERAÇÃO", "subcategoria": "Combustíveis e Lubrificantes"},
        {"categoria": "MANUTENÇÃO E OPERAÇÃO", "subcategoria": "Pneus, Filtros, Correias"},
    ],
}


def nota(**alteracoes):
    dados = copy.deepcopy(NOTA)
    dados.update(alteracoes)
    return dados


def criar_pessoa(client, tipo, nome, documento):
    r = client.post("/api/pessoas", json={"tipo": tipo, "razao_social": nome, "documento": documento})
    assert r.status_code == 201, r.text
    return r.json()


def criar_classificacao(client, tipo, descricao):
    r = client.post("/api/classificacoes", json={"tipo": tipo, "descricao": descricao})
    assert r.status_code == 201, r.text
    return r.json()


def contar(tabela):
    conn = conectar()
    try:
        return conn.execute(f"SELECT COUNT(*) AS n FROM {tabela}").fetchone()["n"]
    finally:
        conn.close()


# ---------- Cadastros ----------
def test_manter_pessoa_inativar_e_reativar(client):
    p = criar_pessoa(client, "FORNECEDOR", "Fornecedor A", "11222333000181")
    assert p["status"] == "ATIVO" and p["documento"] == "11.222.333/0001-81"

    r = client.put(f"/api/pessoas/{p['id']}", json={"razao_social": "Fornecedor A2", "documento": p["documento"]})
    assert r.json()["razao_social"] == "Fornecedor A2"

    assert client.post(f"/api/pessoas/{p['id']}/inativar").json()["status"] == "INATIVO"
    assert client.post(f"/api/pessoas/{p['id']}/inativar").status_code == 409
    assert [x["id"] for x in client.get("/api/pessoas?tipo=FORNECEDOR&status=INATIVO").json()] == [p["id"]]
    assert client.post(f"/api/pessoas/{p['id']}/reativar").json()["status"] == "ATIVO"
    assert contar("pessoas") == 1  # nada é excluído


def test_nao_existe_rota_de_exclusao(client):
    p = criar_pessoa(client, "CLIENTE", "Cliente", "52998224725")
    c = criar_classificacao(client, "RECEITA", "Venda de grãos")
    assert client.delete(f"/api/pessoas/{p['id']}").status_code == 405
    assert client.delete(f"/api/classificacoes/{c['id']}").status_code == 405


def test_pessoa_duplicada_e_recusada_mesmo_inativa(client):
    p = criar_pessoa(client, "FATURADO", "Beltrano", "529.982.247-25")
    client.post(f"/api/pessoas/{p['id']}/inativar")
    r = client.post("/api/pessoas", json={"tipo": "FATURADO", "razao_social": "Outro", "documento": "52998224725"})
    assert r.status_code == 409
    assert "INATIVO" in r.json()["detail"]
    # O mesmo documento pode existir com outro papel (ex.: também cliente).
    criar_pessoa(client, "CLIENTE", "Beltrano", "52998224725")


def test_documento_invalido(client):
    r = client.post("/api/pessoas", json={"tipo": "CLIENTE", "razao_social": "X", "documento": "123"})
    assert r.status_code == 422
    assert "CPF" in r.json()["detail"][0]["msg"]


def test_classificacao_duplicada_ignora_acentos_e_caixa(client):
    criar_classificacao(client, "DESPESA", "MANUTENÇÃO E OPERAÇÃO")
    r = client.post("/api/classificacoes", json={"tipo": "DESPESA", "descricao": "manutencao e operacao"})
    assert r.status_code == 409
    criar_classificacao(client, "RECEITA", "manutencao e operacao")  # outro tipo: permitido


# ---------- Contas ----------
def test_conta_a_receber_com_varias_classificacoes_e_parcelas(client):
    cli = criar_pessoa(client, "CLIENTE", "Cliente", "52998224725")
    r1 = criar_classificacao(client, "RECEITA", "Venda de soja")
    r2 = criar_classificacao(client, "RECEITA", "Venda de milho")
    r = client.post(
        "/api/contas",
        json={
            "tipo": "RECEBER",
            "pessoa_id": cli["id"],
            "descricao": "Venda safra",
            "valor_total": 300,
            "classificacao_ids": [r1["id"], r2["id"]],
            "parcelas": [
                {"data_vencimento": "2026-11-01", "valor": 100},
                {"data_vencimento": "2026-12-01", "valor": 200},
            ],
        },
    )
    assert r.status_code == 201, r.text
    mov = r.json()
    assert len(mov["classificacoes"]) == 2
    assert [p["data_vencimento"] for p in mov["parcelas"]] == ["2026-11-01", "2026-12-01"]
    assert mov["parcelas"][0]["identificacao"] == "1/2"

    parcela = mov["parcelas"][0]["id"]
    assert client.post(f"/api/contas/parcelas/{parcela}/quitar").json()["parcelas"][0]["situacao"] == "QUITADA"
    assert client.post(f"/api/contas/{mov['id']}/inativar").json()["status"] == "INATIVO"
    assert client.post(f"/api/contas/parcelas/{parcela}/reabrir").status_code == 409


@pytest.mark.parametrize(
    "alteracao, trecho",
    [
        ({"valor_total": 999}, "soma das parcelas"),
        ({"classificacao_ids": []}, "classificacao_ids"),
        ({"parcelas": []}, "parcelas"),
        ({"parcelas": [{"valor": 300}]}, "data_vencimento"),
        ({"parcelas": [{"data_vencimento": "2026-11-01", "valor": -1}]}, "valor"),
    ],
)
def test_validacoes_da_conta(client, alteracao, trecho):
    forn = criar_pessoa(client, "FORNECEDOR", "F", "11222333000181")
    desp = criar_classificacao(client, "DESPESA", "Frete")
    body = {
        "tipo": "PAGAR",
        "pessoa_id": forn["id"],
        "descricao": "Frete",
        "valor_total": 300,
        "classificacao_ids": [desp["id"]],
        "parcelas": [{"data_vencimento": "2026-11-01", "valor": 300}],
        **alteracao,
    }
    r = client.post("/api/contas", json=body)
    assert r.status_code == 422
    assert trecho in r.text
    assert contar("movimentocontas") == 0


def test_conta_a_pagar_exige_fornecedor_e_classificacao_de_despesa(client):
    cli = criar_pessoa(client, "CLIENTE", "C", "52998224725")
    rec = criar_classificacao(client, "RECEITA", "Venda")
    body = {
        "tipo": "PAGAR",
        "pessoa_id": cli["id"],
        "descricao": "x",
        "valor_total": 10,
        "classificacao_ids": [rec["id"]],
        "parcelas": [{"data_vencimento": "2026-11-01", "valor": 10}],
    }
    assert "não é fornecedor" in client.post("/api/contas", json=body).json()["detail"]
    forn = criar_pessoa(client, "FORNECEDOR", "F", "11222333000181")
    assert "não é de despesa" in client.post("/api/contas", json={**body, "pessoa_id": forn["id"]}).json()["detail"]


def test_busca_por_mais_de_um_elemento(client):
    criar_pessoa(client, "FORNECEDOR", "Iguaçu Máquinas LTDA", "11222333000181")
    criar_pessoa(client, "FORNECEDOR", "Iguaçu Peças LTDA", "11444777000161")
    inativo = criar_pessoa(client, "FORNECEDOR", "Máquinas Sul", "52998224725")
    client.post(f"/api/pessoas/{inativo['id']}/inativar")

    def nomes(busca, status=None):
        params = {"tipo": "FORNECEDOR", "busca": busca, **({"status": status} if status else {})}
        return sorted(p["razao_social"] for p in client.get("/api/pessoas", params=params).json())

    assert nomes("iguacu maquinas") == ["Iguaçu Máquinas LTDA"]  # todos os termos, sem acento/caixa
    assert nomes("ltda 11.444") == ["Iguaçu Peças LTDA"]  # nome + parte do CNPJ formatado
    assert nomes("maquinas") == ["Iguaçu Máquinas LTDA", "Máquinas Sul"]  # a busca encontra também os inativos
    assert nomes("maquinas", "ATIVO") == ["Iguaçu Máquinas LTDA"]

    criar_classificacao(client, "DESPESA", "Manutenção e Operação")
    criar_classificacao(client, "DESPESA", "Manutenção predial")
    r = client.get("/api/classificacoes", params={"tipo": "DESPESA", "busca": "manutencao operacao"})
    assert [c["descricao"] for c in r.json()] == ["Manutenção e Operação"]


def _conta_a_pagar(client):
    forn = criar_pessoa(client, "FORNECEDOR", "Fornecedor A", "11222333000181")
    d1 = criar_classificacao(client, "DESPESA", "Frete")
    d2 = criar_classificacao(client, "DESPESA", "Combustível")
    r = client.post(
        "/api/contas",
        json={
            "tipo": "PAGAR",
            "pessoa_id": forn["id"],
            "numero_nota": "999",
            "descricao": "Frete de setembro",
            "valor_total": 100,
            "classificacao_ids": [d1["id"]],
            "parcelas": [{"data_vencimento": "2026-11-01", "valor": 100}],
        },
    )
    assert r.status_code == 201, r.text
    return r.json(), forn, d1, d2


def test_editar_conta_substitui_classificacoes_e_parcelas(client):
    mov, forn, d1, d2 = _conta_a_pagar(client)
    body = {
        "pessoa_id": forn["id"],
        "numero_nota": "999",
        "descricao": "Frete e combustível",
        "valor_total": 300,
        "classificacao_ids": [d1["id"], d2["id"]],
        "parcelas": [
            {"data_vencimento": "2026-11-01", "valor": 100},
            {"data_vencimento": "2026-12-01", "valor": 200},
        ],
    }
    r = client.put(f"/api/contas/{mov['id']}", json=body)
    assert r.status_code == 200, r.text
    editado = r.json()
    assert editado["status"] == "ATIVO" and editado["tipo"] == "PAGAR"
    assert editado["descricao"] == "Frete e combustível"
    assert len(editado["classificacoes"]) == 2 and len(editado["parcelas"]) == 2
    assert contar("movimentocontas") == 1 and contar("parcelacontas") == 2

    assert [m["id"] for m in client.get("/api/contas", params={"busca": "combustivel 999"}).json()] == [mov["id"]]
    assert client.get("/api/contas", params={"busca": "combustivel 123"}).json() == []

    # Parcela quitada ou movimento excluído (inativo) bloqueiam a edição.
    client.post(f"/api/contas/parcelas/{editado['parcelas'][0]['id']}/quitar")
    assert client.put(f"/api/contas/{mov['id']}", json=body).status_code == 409
    client.post(f"/api/contas/parcelas/{editado['parcelas'][0]['id']}/reabrir")
    client.post(f"/api/contas/{mov['id']}/inativar")
    assert "INATIVO" in client.put(f"/api/contas/{mov['id']}", json=body).json()["detail"]


def test_editar_conta_mantem_classificacao_inativa_ja_vinculada(client):
    mov, forn, d1, d2 = _conta_a_pagar(client)
    client.post(f"/api/classificacoes/{d1['id']}/inativar")
    client.post(f"/api/classificacoes/{d2['id']}/inativar")
    body = {
        "pessoa_id": forn["id"],
        "descricao": "Outra descrição",
        "valor_total": 100,
        "classificacao_ids": [d1["id"]],
        "parcelas": [{"data_vencimento": "2026-11-01", "valor": 100}],
    }
    assert client.put(f"/api/contas/{mov['id']}", json=body).status_code == 200
    r = client.put(f"/api/contas/{mov['id']}", json={**body, "classificacao_ids": [d2["id"]]})
    assert r.status_code == 422 and "INATIVA" in r.json()["detail"]


# ---------- Segunda etapa: análise + lançamento ----------
def test_cenario_1_tudo_existe(client):
    forn = criar_pessoa(client, "FORNECEDOR", "IGUAÇU MÁQUINAS LTDA", "11222333000181")
    fat = criar_pessoa(client, "FATURADO", "BELTRANO DA SILVA", "52998224725")
    desp = criar_classificacao(client, "DESPESA", "MANUTENÇÃO E OPERAÇÃO")

    analise = client.post("/api/lancamentos/analisar", json=NOTA).json()
    assert analise["fornecedor"].items() >= {"existe": True, "id": forn["id"], "acao": "UTILIZAR"}.items()
    assert analise["faturado"]["id"] == fat["id"]
    assert analise["despesas"] == [
        {"entidade": "DESPESA", "descricao": "MANUTENÇÃO E OPERAÇÃO", "existe": True, "id": desp["id"],
         "status": "ATIVO", "acao": "UTILIZAR"}
    ]
    assert analise["pendencias"] == []

    r = client.post("/api/lancamentos", json={"dados": NOTA})
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["mensagem"] == "Registro lançado com sucesso."
    mov = body["movimento"]
    assert mov["tipo"] == "PAGAR"
    assert mov["pessoa"]["id"] == forn["id"] and mov["faturado"]["id"] == fat["id"]
    assert [c["id"] for c in mov["classificacoes"]] == [desp["id"]]
    assert [(p["numero"], p["data_vencimento"], p["valor"]) for p in mov["parcelas"]] == [
        (1, "2026-10-21", 1500.0),
        (2, "2026-11-21", 1000.0),
    ]
    assert contar("pessoas") == 2 and contar("classificacao") == 1  # sem duplicatas

    # A mesma nota não é lançada duas vezes.
    assert client.post("/api/lancamentos", json={"dados": NOTA}).status_code == 422
    assert contar("movimentocontas") == 1


def test_cenario_2_fornecedor_nao_existe(client):
    fat = criar_pessoa(client, "FATURADO", "BELTRANO DA SILVA", "52998224725")
    criar_classificacao(client, "DESPESA", "Manutenção e Operação")

    analise = client.post("/api/lancamentos/analisar", json=NOTA).json()
    assert analise["fornecedor"]["existe"] is False and analise["fornecedor"]["acao"] == "CRIAR"

    body = client.post("/api/lancamentos", json={"dados": NOTA}).json()
    novo = client.get("/api/pessoas?tipo=FORNECEDOR").json()
    assert len(novo) == 1 and novo[0]["documento"] == "11.222.333/0001-81" and novo[0]["fantasia"] == "IGUAÇU"
    assert body["movimento"]["pessoa"]["id"] == novo[0]["id"]
    assert body["movimento"]["faturado"]["id"] == fat["id"]
    assert any("Fornecedor criado" in a for a in body["acoes"])


def test_cenario_3_nada_existe(client):
    analise = client.post("/api/lancamentos/analisar", json=NOTA).json()
    assert not analise["fornecedor"]["existe"] and not analise["faturado"]["existe"]
    assert not analise["despesas"][0]["existe"]

    r = client.post("/api/lancamentos", json={"dados": NOTA})
    assert r.status_code == 201, r.text
    assert contar("pessoas") == 2 and contar("classificacao") == 1
    assert contar("movimentocontas") == 1 and contar("parcelacontas") == 2

    # Uma nova análise agora encontra tudo com os IDs criados.
    analise = client.post("/api/lancamentos/analisar", json=NOTA).json()
    assert analise["fornecedor"]["existe"] and analise["faturado"]["existe"] and analise["despesas"][0]["existe"]


def test_cenario_4_cadastro_inativo_exige_confirmacao_e_reativa(client):
    forn = criar_pessoa(client, "FORNECEDOR", "IGUAÇU MÁQUINAS LTDA", "11222333000181")
    client.post(f"/api/pessoas/{forn['id']}/inativar")

    analise = client.post("/api/lancamentos/analisar", json=NOTA).json()
    assert analise["fornecedor"].items() >= {"existe": True, "id": forn["id"], "status": "INATIVO", "acao": "REATIVAR"}.items()

    r = client.post("/api/lancamentos", json={"dados": NOTA})
    assert r.status_code == 409 and r.json()["codigo"] == "cadastro_inativo"
    assert contar("movimentocontas") == 0 and contar("pessoas") == 1  # nada gravado, sem duplicata

    r = client.post("/api/lancamentos", json={"dados": NOTA, "reativar_inativos": True})
    assert r.status_code == 201, r.text
    assert r.json()["movimento"]["pessoa"]["id"] == forn["id"]
    assert client.get(f"/api/pessoas/{forn['id']}").json()["status"] == "ATIVO"
    assert contar("pessoas") == 2  # o fornecedor original (reativado) + o faturado novo


def test_lancamento_com_pendencias_nao_grava_nada(client):
    dados = nota(parcelas=[{"numero": 1, "data_vencimento": None, "valor": 2500.0}], despesas=[])
    analise = client.post("/api/lancamentos/analisar", json=dados).json()
    assert any("vencimento" in p for p in analise["pendencias"])
    assert any("classificação" in p for p in analise["pendencias"])

    r = client.post("/api/lancamentos", json={"dados": dados})
    assert r.status_code == 422
    assert contar("pessoas") == 0 and contar("movimentocontas") == 0


def test_fornecedor_sem_documento_e_pendencia(client):
    dados = nota(fornecedor={"razao_social": "SEM CNPJ LTDA", "fantasia": None, "cnpj": None})
    analise = client.post("/api/lancamentos/analisar", json=dados).json()
    assert analise["fornecedor"]["acao"] == "INDISPONIVEL"
    # Sem documento, a consulta usa o nome: se já existir com esse nome, é utilizado.
    criar_pessoa(client, "FORNECEDOR", "Sem CNPJ Ltda", "11222333000181")
    analise = client.post("/api/lancamentos/analisar", json=dados).json()
    assert analise["fornecedor"]["existe"] is True


def test_erro_no_meio_do_lancamento_desfaz_tudo(client, monkeypatch):
    from app.services import contas_service

    def falhar(*_args, **_kwargs):
        raise RuntimeError("falha simulada ao criar o movimento")

    monkeypatch.setattr(contas_service, "criar_movimento", falhar)
    with pytest.raises(RuntimeError):
        client.post("/api/lancamentos", json={"dados": NOTA})
    # Fornecedor, faturado e despesa tinham sido criados na transação: todos foram desfeitos.
    assert contar("pessoas") == 0 and contar("classificacao") == 0 and contar("movimentocontas") == 0


def test_rotas_financeiras_exigem_login(anonimo):
    assert anonimo.get("/api/pessoas").status_code == 401
    assert anonimo.post("/api/lancamentos/analisar", json=NOTA).status_code == 401
