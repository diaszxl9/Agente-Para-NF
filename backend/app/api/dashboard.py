from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models import Cliente, ContaPagar, ContaReceber, Fornecedor

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


class DashboardResponse(BaseModel):
    fornecedores: int
    clientes: int
    contas_pagar: int
    contas_receber: int


def _contar(db: Session, model) -> int:
    return db.scalar(select(func.count()).select_from(model).where(model.ativo.is_(True))) or 0


@router.get("", response_model=DashboardResponse)
def dashboard(db: Session = Depends(get_db)) -> DashboardResponse:
    return DashboardResponse(
        fornecedores=_contar(db, Fornecedor),
        clientes=_contar(db, Cliente),
        contas_pagar=_contar(db, ContaPagar),
        contas_receber=_contar(db, ContaReceber),
    )
