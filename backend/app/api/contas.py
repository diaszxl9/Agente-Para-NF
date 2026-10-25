"""Contas a pagar/receber, parcelas e o lançamento da nota fiscal extraída (segunda etapa)."""

import sqlite3

from fastapi import APIRouter, Depends, Query

from app.db import get_db
from app.schemas.financeiro import (
    AnaliseResponse,
    LancamentoRequest,
    LancamentoResponse,
    MovimentoIn,
    MovimentoOut,
    MovimentoUpdate,
    Status,
    TipoMovimento,
)
from app.schemas.nota_fiscal import NotaFiscalExtraida
from app.services import contas_service as service
from app.services import lancamento_service

contas = APIRouter(prefix="/contas", tags=["Contas a pagar/receber"])
lancamentos = APIRouter(prefix="/lancamentos", tags=["Lançamento da nota"])


@contas.get("", response_model=list[MovimentoOut])
def listar(
    tipo: TipoMovimento | None = None,
    status: Status | None = None,
    busca: str | None = Query(default=None, max_length=100),
    conn: sqlite3.Connection = Depends(get_db),
) -> list[MovimentoOut]:
    return service.listar_movimentos(conn, tipo, status, busca)


@contas.get("/{movimento_id}", response_model=MovimentoOut)
def obter(movimento_id: int, conn: sqlite3.Connection = Depends(get_db)) -> MovimentoOut:
    return service.obter_movimento(conn, movimento_id)


@contas.post("", response_model=MovimentoOut, status_code=201)
def criar(body: MovimentoIn, conn: sqlite3.Connection = Depends(get_db)) -> MovimentoOut:
    with conn:
        return service.criar_movimento(conn, body)


@contas.put("/{movimento_id}", response_model=MovimentoOut)
def atualizar(movimento_id: int, body: MovimentoUpdate, conn: sqlite3.Connection = Depends(get_db)) -> MovimentoOut:
    with conn:
        return service.atualizar_movimento(conn, movimento_id, body)


@contas.post("/{movimento_id}/inativar", response_model=MovimentoOut)
def inativar(movimento_id: int, conn: sqlite3.Connection = Depends(get_db)) -> MovimentoOut:
    with conn:
        return service.alterar_status_movimento(conn, movimento_id, "INATIVO")


@contas.post("/{movimento_id}/reativar", response_model=MovimentoOut)
def reativar(movimento_id: int, conn: sqlite3.Connection = Depends(get_db)) -> MovimentoOut:
    with conn:
        return service.alterar_status_movimento(conn, movimento_id, "ATIVO")


@contas.post("/parcelas/{parcela_id}/quitar", response_model=MovimentoOut)
def quitar_parcela(parcela_id: int, conn: sqlite3.Connection = Depends(get_db)) -> MovimentoOut:
    with conn:
        return service.alterar_situacao_parcela(conn, parcela_id, "QUITADA")


@contas.post("/parcelas/{parcela_id}/reabrir", response_model=MovimentoOut)
def reabrir_parcela(parcela_id: int, conn: sqlite3.Connection = Depends(get_db)) -> MovimentoOut:
    with conn:
        return service.alterar_situacao_parcela(conn, parcela_id, "ABERTA")


@lancamentos.post("/analisar", response_model=AnaliseResponse)
def analisar(body: NotaFiscalExtraida, conn: sqlite3.Connection = Depends(get_db)) -> AnaliseResponse:
    """Consulta fornecedor, faturado e classificações da nota extraída. Não grava nada."""
    return lancamento_service.analisar(conn, body)


@lancamentos.post("", response_model=LancamentoResponse, status_code=201)
def lancar(body: LancamentoRequest, conn: sqlite3.Connection = Depends(get_db)) -> LancamentoResponse:
    """Cria o que não existe, o movimento (PAGAR) e as parcelas, numa única transação."""
    return lancamento_service.lancar(conn, body.dados, body.reativar_inativos)
