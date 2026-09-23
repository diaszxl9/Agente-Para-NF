import pytest
from sqlalchemy.exc import IntegrityError

from app.database import session as db_session
from app.models import Cliente, ContaReceber, Fornecedor, Parcela


@pytest.fixture
def sessao(client):
    # `client` dispara o init_db (criação das tabelas) no banco SQLite em memória dos testes.
    with db_session.SessionLocal() as session:
        yield session


def _conta_receber(sessao) -> ContaReceber:
    cliente = Cliente(nome="Cliente")
    sessao.add(cliente)
    sessao.flush()
    conta = ContaReceber(cliente_id=cliente.id, valor_total=100)
    sessao.add(conta)
    sessao.flush()
    return conta


def test_parcela_de_conta_a_receber_pode_ser_recebida(sessao):
    conta = _conta_receber(sessao)
    sessao.add(Parcela(conta_receber_id=conta.id, numero=1, valor=100, status="RECEBIDA"))
    sessao.commit()


def test_parcela_rejeita_status_inexistente(sessao):
    conta = _conta_receber(sessao)
    sessao.add(Parcela(conta_receber_id=conta.id, numero=1, valor=100, status="QUALQUER"))
    with pytest.raises(IntegrityError):
        sessao.commit()


def test_parcela_exige_exatamente_uma_conta(sessao):
    sessao.add(Parcela(numero=1, valor=10))
    with pytest.raises(IntegrityError):
        sessao.commit()
    sessao.rollback()
    assert sessao.query(Fornecedor).count() == 0
