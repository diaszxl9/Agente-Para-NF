from app.config import get_settings


def test_sem_api_key_configurada_acesso_livre(client):
    assert get_settings().API_KEY == ""
    assert client.post("/api/notas-fiscais/extrair").status_code == 422  # passou da autenticação; falta o arquivo


def test_com_api_key_configurada_exige_header(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "API_KEY", "segredo-teste")

    sem_header = client.post("/api/notas-fiscais/extrair")
    assert sem_header.status_code == 401

    header_errado = client.post("/api/notas-fiscais/extrair", headers={"X-API-Key": "errado"})
    assert header_errado.status_code == 401

    header_certo = client.post("/api/notas-fiscais/extrair", headers={"X-API-Key": "segredo-teste"})
    assert header_certo.status_code == 422


def test_health_continua_publico_mesmo_com_api_key(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "API_KEY", "segredo-teste")
    assert client.get("/api/health").status_code == 200
