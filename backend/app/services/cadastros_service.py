"""Pessoas (fornecedor, cliente, faturado) e classificações (tipos de receita e despesa).

As funções não fazem commit: quem chama controla a transação (`with conn:`), o que permite compor várias operações
numa única transação no lançamento da nota. Nada é excluído: o status alterna entre ATIVO e INATIVO.
"""

import sqlite3

from app.schemas.financeiro import (
    ClassificacaoIn,
    ClassificacaoOut,
    ClassificacaoUpdate,
    PessoaIn,
    PessoaOut,
    PessoaUpdate,
)
from app.services.erros import NaoEncontradoError, NegocioError
from app.services.sanitize import corresponde_busca, format_documento, normalize_key, only_digits

NOME_TIPO_PESSOA = {"FORNECEDOR": "Fornecedor", "CLIENTE": "Cliente", "FATURADO": "Faturado"}
NOME_TIPO_CLASSIFICACAO = {"DESPESA": "Tipo de despesa", "RECEITA": "Tipo de receita"}


# ---------- Pessoas ----------
def _pessoa(row: sqlite3.Row) -> PessoaOut:
    return PessoaOut(**{**dict(row), "documento": format_documento(row["documento"]) or row["documento"]})


def listar_pessoas(
    conn: sqlite3.Connection, tipo: str | None = None, status: str | None = None, busca: str | None = None
) -> list[PessoaOut]:
    sql, params = "SELECT * FROM pessoas WHERE 1 = 1", []
    if tipo:
        sql += " AND tipo = ?"
        params.append(tipo)
    if status:
        sql += " AND status = ?"
        params.append(status)
    pessoas = [_pessoa(r) for r in conn.execute(sql + " ORDER BY razao_social COLLATE NOCASE", params)]
    return [p for p in pessoas if corresponde_busca(busca, p.razao_social, p.fantasia, p.documento)]


def obter_pessoa(conn: sqlite3.Connection, pessoa_id: int) -> PessoaOut:
    row = conn.execute("SELECT * FROM pessoas WHERE id = ?", (pessoa_id,)).fetchone()
    if not row:
        raise NaoEncontradoError(f"Pessoa ID {pessoa_id} não encontrada.")
    return _pessoa(row)


def buscar_pessoa(
    conn: sqlite3.Connection, tipo: str, documento: str | None = None, nome: str | None = None
) -> PessoaOut | None:
    """Procura por documento (CPF/CNPJ); sem documento, pelo nome normalizado (sem acentos/caixa)."""
    digitos = only_digits(documento or "")
    if digitos:
        row = conn.execute("SELECT * FROM pessoas WHERE tipo = ? AND documento = ?", (tipo, digitos)).fetchone()
        return _pessoa(row) if row else None
    if nome:
        chave = normalize_key(nome)
        for row in conn.execute("SELECT * FROM pessoas WHERE tipo = ? ORDER BY id", (tipo,)):
            if normalize_key(row["razao_social"]) == chave or (
                row["fantasia"] and normalize_key(row["fantasia"]) == chave
            ):
                return _pessoa(row)
    return None


def _erro_pessoa_duplicada(existente: PessoaOut) -> NegocioError:
    nome = NOME_TIPO_PESSOA[existente.tipo]
    extra = " Ele está INATIVO: reative o cadastro existente." if existente.status == "INATIVO" else ""
    return NegocioError(
        f"{nome} com o documento {existente.documento} já cadastrado (ID {existente.id}).{extra}", 409
    )


def criar_pessoa(conn: sqlite3.Connection, dados: PessoaIn) -> PessoaOut:
    existente = buscar_pessoa(conn, dados.tipo, dados.documento)
    if existente:
        raise _erro_pessoa_duplicada(existente)
    cur = conn.execute(
        "INSERT INTO pessoas (tipo, razao_social, fantasia, documento) VALUES (?, ?, ?, ?)",
        (dados.tipo, dados.razao_social, dados.fantasia, dados.documento),
    )
    return obter_pessoa(conn, cur.lastrowid)


def atualizar_pessoa(conn: sqlite3.Connection, pessoa_id: int, dados: PessoaUpdate) -> PessoaOut:
    atual = obter_pessoa(conn, pessoa_id)
    existente = buscar_pessoa(conn, atual.tipo, dados.documento)
    if existente and existente.id != pessoa_id:
        raise _erro_pessoa_duplicada(existente)
    conn.execute(
        "UPDATE pessoas SET razao_social = ?, fantasia = ?, documento = ? WHERE id = ?",
        (dados.razao_social, dados.fantasia, dados.documento, pessoa_id),
    )
    return obter_pessoa(conn, pessoa_id)


def alterar_status_pessoa(conn: sqlite3.Connection, pessoa_id: int, status: str) -> PessoaOut:
    atual = obter_pessoa(conn, pessoa_id)
    if atual.status == status:
        raise NegocioError(f"{NOME_TIPO_PESSOA[atual.tipo]} ID {pessoa_id} já está {status}.", 409)
    conn.execute("UPDATE pessoas SET status = ? WHERE id = ?", (status, pessoa_id))
    return obter_pessoa(conn, pessoa_id)


# ---------- Classificações ----------
def _classificacao(row: sqlite3.Row) -> ClassificacaoOut:
    return ClassificacaoOut(**{k: row[k] for k in ("id", "tipo", "descricao", "status", "data_cadastro")})


def listar_classificacoes(
    conn: sqlite3.Connection, tipo: str | None = None, status: str | None = None, busca: str | None = None
) -> list[ClassificacaoOut]:
    sql, params = "SELECT * FROM classificacao WHERE 1 = 1", []
    if tipo:
        sql += " AND tipo = ?"
        params.append(tipo)
    if status:
        sql += " AND status = ?"
        params.append(status)
    classificacoes = [_classificacao(r) for r in conn.execute(sql + " ORDER BY descricao COLLATE NOCASE", params)]
    return [c for c in classificacoes if corresponde_busca(busca, c.descricao)]


def obter_classificacao(conn: sqlite3.Connection, classificacao_id: int) -> ClassificacaoOut:
    row = conn.execute("SELECT * FROM classificacao WHERE id = ?", (classificacao_id,)).fetchone()
    if not row:
        raise NaoEncontradoError(f"Classificação ID {classificacao_id} não encontrada.")
    return _classificacao(row)


def buscar_classificacao(conn: sqlite3.Connection, tipo: str, descricao: str) -> ClassificacaoOut | None:
    row = conn.execute(
        "SELECT * FROM classificacao WHERE tipo = ? AND chave = ?", (tipo, normalize_key(descricao))
    ).fetchone()
    return _classificacao(row) if row else None


def _erro_classificacao_duplicada(existente: ClassificacaoOut) -> NegocioError:
    extra = " Ela está INATIVA: reative o cadastro existente." if existente.status == "INATIVO" else ""
    return NegocioError(
        f"{NOME_TIPO_CLASSIFICACAO[existente.tipo]} \"{existente.descricao}\" já cadastrado (ID {existente.id}).{extra}",
        409,
    )


def criar_classificacao(conn: sqlite3.Connection, dados: ClassificacaoIn) -> ClassificacaoOut:
    existente = buscar_classificacao(conn, dados.tipo, dados.descricao)
    if existente:
        raise _erro_classificacao_duplicada(existente)
    cur = conn.execute(
        "INSERT INTO classificacao (tipo, descricao, chave) VALUES (?, ?, ?)",
        (dados.tipo, dados.descricao, normalize_key(dados.descricao)),
    )
    return obter_classificacao(conn, cur.lastrowid)


def atualizar_classificacao(
    conn: sqlite3.Connection, classificacao_id: int, dados: ClassificacaoUpdate
) -> ClassificacaoOut:
    atual = obter_classificacao(conn, classificacao_id)
    existente = buscar_classificacao(conn, atual.tipo, dados.descricao)
    if existente and existente.id != classificacao_id:
        raise _erro_classificacao_duplicada(existente)
    conn.execute(
        "UPDATE classificacao SET descricao = ?, chave = ? WHERE id = ?",
        (dados.descricao, normalize_key(dados.descricao), classificacao_id),
    )
    return obter_classificacao(conn, classificacao_id)


def alterar_status_classificacao(conn: sqlite3.Connection, classificacao_id: int, status: str) -> ClassificacaoOut:
    atual = obter_classificacao(conn, classificacao_id)
    if atual.status == status:
        raise NegocioError(f"Classificação ID {classificacao_id} já está {status}.", 409)
    conn.execute("UPDATE classificacao SET status = ? WHERE id = ?", (status, classificacao_id))
    return obter_classificacao(conn, classificacao_id)
