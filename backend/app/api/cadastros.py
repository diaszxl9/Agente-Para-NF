"""Manter Fornecedor/Cliente/Faturado e Tipos de Receita/Despesa. Sem DELETE: só inativar e reativar."""

from fastapi import APIRouter, Depends, Query

from app.db import Conexao, get_db
from app.schemas.financeiro import (
    ClassificacaoIn,
    ClassificacaoOut,
    ClassificacaoUpdate,
    PessoaIn,
    PessoaOut,
    PessoaUpdate,
    Status,
    TipoClassificacao,
    TipoPessoa,
)
from app.services import cadastros_service as service

pessoas = APIRouter(prefix="/pessoas", tags=["Pessoas"])
classificacoes = APIRouter(prefix="/classificacoes", tags=["Classificações"])


@pessoas.get("", response_model=list[PessoaOut])
def listar_pessoas(
    tipo: TipoPessoa | None = None,
    status: Status | None = None,
    busca: str | None = Query(default=None, max_length=100),
    conn: Conexao = Depends(get_db),
) -> list[PessoaOut]:
    return service.listar_pessoas(conn, tipo, status, busca)


@pessoas.get("/{pessoa_id}", response_model=PessoaOut)
def obter_pessoa(pessoa_id: int, conn: Conexao = Depends(get_db)) -> PessoaOut:
    return service.obter_pessoa(conn, pessoa_id)


@pessoas.post("", response_model=PessoaOut, status_code=201)
def criar_pessoa(body: PessoaIn, conn: Conexao = Depends(get_db)) -> PessoaOut:
    with conn:
        return service.criar_pessoa(conn, body)


@pessoas.put("/{pessoa_id}", response_model=PessoaOut)
def atualizar_pessoa(pessoa_id: int, body: PessoaUpdate, conn: Conexao = Depends(get_db)) -> PessoaOut:
    with conn:
        return service.atualizar_pessoa(conn, pessoa_id, body)


@pessoas.post("/{pessoa_id}/inativar", response_model=PessoaOut)
def inativar_pessoa(pessoa_id: int, conn: Conexao = Depends(get_db)) -> PessoaOut:
    with conn:
        return service.alterar_status_pessoa(conn, pessoa_id, "INATIVO")


@pessoas.post("/{pessoa_id}/reativar", response_model=PessoaOut)
def reativar_pessoa(pessoa_id: int, conn: Conexao = Depends(get_db)) -> PessoaOut:
    with conn:
        return service.alterar_status_pessoa(conn, pessoa_id, "ATIVO")


@classificacoes.get("", response_model=list[ClassificacaoOut])
def listar_classificacoes(
    tipo: TipoClassificacao | None = None,
    status: Status | None = None,
    busca: str | None = Query(default=None, max_length=100),
    conn: Conexao = Depends(get_db),
) -> list[ClassificacaoOut]:
    return service.listar_classificacoes(conn, tipo, status, busca)


@classificacoes.post("", response_model=ClassificacaoOut, status_code=201)
def criar_classificacao(body: ClassificacaoIn, conn: Conexao = Depends(get_db)) -> ClassificacaoOut:
    with conn:
        return service.criar_classificacao(conn, body)


@classificacoes.put("/{classificacao_id}", response_model=ClassificacaoOut)
def atualizar_classificacao(
    classificacao_id: int, body: ClassificacaoUpdate, conn: Conexao = Depends(get_db)
) -> ClassificacaoOut:
    with conn:
        return service.atualizar_classificacao(conn, classificacao_id, body)


@classificacoes.post("/{classificacao_id}/inativar", response_model=ClassificacaoOut)
def inativar_classificacao(classificacao_id: int, conn: Conexao = Depends(get_db)) -> ClassificacaoOut:
    with conn:
        return service.alterar_status_classificacao(conn, classificacao_id, "INATIVO")


@classificacoes.post("/{classificacao_id}/reativar", response_model=ClassificacaoOut)
def reativar_classificacao(classificacao_id: int, conn: Conexao = Depends(get_db)) -> ClassificacaoOut:
    with conn:
        return service.alterar_status_classificacao(conn, classificacao_id, "ATIVO")
