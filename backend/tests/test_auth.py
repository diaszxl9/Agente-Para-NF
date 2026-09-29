import time

from tests.conftest import FakeGemini

from app.auth import criar_token
from app.config import get_settings
from app.services.gemini_service import GeminiError


def login(client, usuario=None, senha=None):
    settings = get_settings()
    return client.post(
        "/api/auth/login",
        json={"usuario": usuario or settings.AUTH_USUARIO, "senha": senha or settings.AUTH_SENHA},
    )


def test_login_com_credenciais_corretas_devolve_token(anonimo):
    r = login(anonimo)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["usuario"] == get_settings().AUTH_USUARIO
    assert body["expira_em"] > time.time()

    token = body["token"]
    r = anonimo.post("/api/notas-fiscais/extrair", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 422  # autenticado; só falta o arquivo


def test_login_ignora_maiusculas_no_usuario(anonimo):
    assert login(anonimo, usuario=f" {get_settings().AUTH_USUARIO.upper()} ").status_code == 200


def test_login_com_senha_errada(anonimo):
    r = login(anonimo, senha="errada")
    assert r.status_code == 401
    assert r.json()["detail"] == "Usuário ou senha inválidos."


def test_rotas_protegidas_exigem_login(anonimo):
    assert anonimo.post("/api/notas-fiscais/extrair").status_code == 401
    assert anonimo.post("/api/gemini/validar").status_code == 401
    assert anonimo.get("/api/health").status_code == 200


def test_token_adulterado_ou_expirado_e_recusado(anonimo, monkeypatch):
    settings = get_settings()
    token, _ = criar_token("professor", settings)
    adulterado = token[:-2] + ("AA" if not token.endswith("AA") else "BB")

    monkeypatch.setattr(settings, "AUTH_SESSAO_HORAS", -1)
    expirado, _ = criar_token("professor", settings)

    for t in (adulterado, expirado, "lixo", ""):
        r = anonimo.post("/api/gemini/validar", headers={"Authorization": f"Bearer {t}"})
        assert r.status_code == 401


def test_validar_api_key_valida(client, usar_gemini):
    usar_gemini(FakeGemini(["valida"]))
    r = client.post("/api/gemini/validar", headers={"X-Gemini-Api-Key": "chave"})
    assert r.status_code == 200
    assert r.json() == {"valida": True, "mensagem": "API Key válida."}


def test_validar_api_key_invalida(client, usar_gemini):
    usar_gemini(FakeGemini(["invalida"]))
    r = client.post("/api/gemini/validar", headers={"X-Gemini-Api-Key": "chave"})
    assert r.status_code == 200
    assert r.json() == {"valida": False, "mensagem": "API Key inválida. Verifique a chave informada."}


def test_validar_api_key_erro_de_conexao(client, usar_gemini):
    usar_gemini(FakeGemini(erro=GeminiError("Não foi possível se comunicar com o Gemini.", 502)))
    r = client.post("/api/gemini/validar", headers={"X-Gemini-Api-Key": "chave"})
    assert r.status_code == 502
    assert "comunicar" in r.json()["detail"]



def test_env_com_credenciais_vazias_usa_os_padroes(monkeypatch):
    """Copiar o .env.example com "AUTH_USUARIO=" vazio não pode quebrar o login nem liberar senha vazia."""
    from app.auth import credenciais_validas
    from app.config import Settings

    monkeypatch.setenv("AUTH_USUARIO", "")
    monkeypatch.setenv("AUTH_SENHA", "")
    settings = Settings(_env_file=None)
    assert settings.AUTH_USUARIO == "professor"
    assert credenciais_validas("professor", "avaliacao123", settings)
    assert not credenciais_validas("", "", settings)


def test_sem_credenciais_configuradas_ninguem_entra(monkeypatch):
    from app.auth import credenciais_validas
    from app.config import Settings

    settings = Settings(AUTH_USUARIO=" ", AUTH_SENHA="", _env_file=None)
    assert not credenciais_validas(" ", "", settings)
    assert not credenciais_validas("", "", settings)
