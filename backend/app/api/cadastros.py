from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models import Cliente, Faturado, Fornecedor, TipoDespesa, TipoReceita
from app.schemas.cadastros import (
    ClienteIn,
    ClienteOut,
    FaturadoIn,
    FaturadoOut,
    FornecedorIn,
    FornecedorOut,
    TipoDespesaIn,
    TipoDespesaOut,
    TipoReceitaIn,
    TipoReceitaOut,
)


def crud_router(*, prefix, tag, model, schema_in, schema_out, search_fields, order_by) -> APIRouter:
    """CRUD sem DELETE: 'excluir' = inativar (ativo=False); reativar = ativo=True."""
    router = APIRouter(prefix=prefix, tags=[tag])

    def obter(db: Session, item_id: int):
        item = db.get(model, item_id)
        if item is None:
            raise HTTPException(status_code=404, detail="Registro não encontrado.")
        return item

    @router.get("", response_model=list[schema_out])
    def listar(
        status: Literal["ativos", "inativos", "todos"] = "ativos",
        q: str | None = Query(default=None, max_length=100),
        limit: int = Query(default=200, ge=1, le=500),
        offset: int = Query(default=0, ge=0),
        db: Session = Depends(get_db),
    ):
        stmt = select(model)
        if status == "ativos":
            stmt = stmt.where(model.ativo.is_(True))
        elif status == "inativos":
            stmt = stmt.where(model.ativo.is_(False))
        if q and q.strip():
            termo = f"%{q.strip()}%"
            stmt = stmt.where(or_(*[getattr(model, campo).like(termo) for campo in search_fields]))
        stmt = stmt.order_by(*[getattr(model, c) for c in order_by]).limit(limit).offset(offset)
        return db.scalars(stmt).all()

    @router.get("/{item_id}", response_model=schema_out)
    def detalhar(item_id: int, db: Session = Depends(get_db)):
        return obter(db, item_id)

    @router.post("", response_model=schema_out, status_code=201)
    def criar(payload: schema_in, db: Session = Depends(get_db)):
        item = model(**payload.model_dump())
        db.add(item)
        db.commit()
        db.refresh(item)
        return item

    @router.put("/{item_id}", response_model=schema_out)
    def atualizar(item_id: int, payload: schema_in, db: Session = Depends(get_db)):
        item = obter(db, item_id)
        for campo, valor in payload.model_dump().items():
            setattr(item, campo, valor)
        db.commit()
        db.refresh(item)
        return item

    @router.patch("/{item_id}/inativar", response_model=schema_out)
    def inativar(item_id: int, db: Session = Depends(get_db)):
        item = obter(db, item_id)
        item.ativo = False
        db.commit()
        db.refresh(item)
        return item

    @router.patch("/{item_id}/reativar", response_model=schema_out)
    def reativar(item_id: int, db: Session = Depends(get_db)):
        item = obter(db, item_id)
        item.ativo = True
        db.commit()
        db.refresh(item)
        return item

    return router


routers = [
    crud_router(
        prefix="/fornecedores",
        tag="Fornecedores",
        model=Fornecedor,
        schema_in=FornecedorIn,
        schema_out=FornecedorOut,
        search_fields=("razao_social", "nome_fantasia", "cnpj"),
        order_by=("razao_social",),
    ),
    crud_router(
        prefix="/clientes",
        tag="Clientes",
        model=Cliente,
        schema_in=ClienteIn,
        schema_out=ClienteOut,
        search_fields=("nome", "cpf_cnpj"),
        order_by=("nome",),
    ),
    crud_router(
        prefix="/faturados",
        tag="Faturados",
        model=Faturado,
        schema_in=FaturadoIn,
        schema_out=FaturadoOut,
        search_fields=("nome_completo", "cpf"),
        order_by=("nome_completo",),
    ),
    crud_router(
        prefix="/tipos-despesa",
        tag="Tipos de Despesa",
        model=TipoDespesa,
        schema_in=TipoDespesaIn,
        schema_out=TipoDespesaOut,
        search_fields=("grupo", "nome"),
        order_by=("grupo", "id"),
    ),
    crud_router(
        prefix="/tipos-receita",
        tag="Tipos de Receita",
        model=TipoReceita,
        schema_in=TipoReceitaIn,
        schema_out=TipoReceitaOut,
        search_fields=("nome",),
        order_by=("nome",),
    ),
]
