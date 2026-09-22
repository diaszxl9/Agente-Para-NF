def test_tipos_despesa_seed_com_categorias_padrao(client):
    itens = client.get("/api/tipos-despesa?status=todos&limit=500").json()
    assert len(itens) == 34
    grupos = {i["grupo"] for i in itens}
    assert len(grupos) == 9 and "SEGUROS E PROTEÇÃO" in grupos


def test_novo_tipo_despesa_vai_para_o_prompt(client, usar_gemini):
    import json

    from tests.conftest import PDF_MINIMO, FakeGemini

    client.post("/api/tipos-despesa", json={"grupo": "pecuária", "nome": "Vacinas"})
    fake = usar_gemini(FakeGemini([json.dumps({})]))
    client.post("/api/notas-fiscais/extrair", files={"arquivo": ("nf.pdf", PDF_MINIMO, "application/pdf")})
    assert "PECUÁRIA: Vacinas" in fake.ultimo_prompt


def test_fornecedor_crud_e_inativacao_logica(client):
    r = client.post("/api/fornecedores", json={"razao_social": "  ACME LTDA ", "cnpj": "11222333000181"})
    assert r.status_code == 201
    f = r.json()
    assert f["razao_social"] == "ACME LTDA" and f["cnpj"] == "11.222.333/0001-81" and f["ativo"] is True

    assert client.put(f"/api/fornecedores/{f['id']}", json={"razao_social": "ACME S/A"}).json()["razao_social"] == "ACME S/A"

    assert client.patch(f"/api/fornecedores/{f['id']}/inativar").json()["ativo"] is False
    assert client.get("/api/fornecedores").json() == []
    assert len(client.get("/api/fornecedores?status=inativos").json()) == 1
    assert client.get(f"/api/fornecedores/{f['id']}").status_code == 200

    assert client.patch(f"/api/fornecedores/{f['id']}/reativar").json()["ativo"] is True
    assert len(client.get("/api/fornecedores").json()) == 1


def test_nao_existe_exclusao_fisica(client):
    f = client.post("/api/fornecedores", json={"razao_social": "X"}).json()
    assert client.delete(f"/api/fornecedores/{f['id']}").status_code == 405


def test_cnpj_duplicado_retorna_409_e_invalido_422(client):
    body = {"razao_social": "A", "cnpj": "11.222.333/0001-81"}
    assert client.post("/api/fornecedores", json=body).status_code == 201
    assert client.post("/api/fornecedores", json=body).status_code == 409
    assert client.post("/api/fornecedores", json={"razao_social": "B", "cnpj": "123"}).status_code == 422
    assert client.post("/api/fornecedores", json={"razao_social": "   "}).status_code == 422


def test_cliente_faturado_tipo_receita(client):
    assert client.post("/api/clientes", json={"nome": "Cli", "cpf_cnpj": "52998224725"}).json()["cpf_cnpj"] == "529.982.247-25"
    assert client.post("/api/faturados", json={"nome_completo": "Fulano", "cpf": "529.982.247-25"}).status_code == 201
    assert client.post("/api/tipos-receita", json={"nome": "Venda de Soja"}).status_code == 201
    assert client.post("/api/tipos-receita", json={"nome": "Venda de Soja"}).status_code == 409


def test_busca_e_404(client):
    client.post("/api/fornecedores", json={"razao_social": "Alfa Sementes"})
    client.post("/api/fornecedores", json={"razao_social": "Beta Diesel"})
    assert [f["razao_social"] for f in client.get("/api/fornecedores?q=diesel").json()] == ["Beta Diesel"]
    assert client.get("/api/fornecedores/999").status_code == 404


def test_dashboard_conta_registros_reais(client):
    assert client.get("/api/dashboard").json() == {"fornecedores": 0, "clientes": 0, "contas_pagar": 0, "contas_receber": 0}
    client.post("/api/fornecedores", json={"razao_social": "A"})
    assert client.get("/api/dashboard").json()["fornecedores"] == 1


def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}
