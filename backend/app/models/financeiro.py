from datetime import date
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, ForeignKey, Index, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import AtivoMixin, Base, TimestampMixin

STATUS_CONTA_PAGAR = ("ABERTA", "PAGA", "CANCELADA")
STATUS_CONTA_RECEBER = ("ABERTA", "RECEBIDA", "CANCELADA")
# Uma parcela pertence a uma conta a pagar (PAGA) OU a uma conta a receber (RECEBIDA).
STATUS_PARCELA = ("ABERTA", "PAGA", "RECEBIDA", "CANCELADA")


def _status_in(coluna: str, valores: tuple[str, ...]) -> str:
    return f"{coluna} IN ({','.join(repr(v) for v in valores)})"


class NotaFiscal(Base, TimestampMixin):
    __tablename__ = "notas_fiscais"
    __table_args__ = (
        UniqueConstraint("fornecedor_id", "numero", name="uq_nota_fornecedor_numero"),
        Index("ix_notas_fiscais_data_emissao", "data_emissao"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    numero: Mapped[str] = mapped_column(String(60), nullable=False)
    data_emissao: Mapped[date | None] = mapped_column(Date)
    valor_total: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    fornecedor_id: Mapped[int | None] = mapped_column(ForeignKey("fornecedores.id"))
    faturado_id: Mapped[int | None] = mapped_column(ForeignKey("faturados.id"))
    arquivo_nome: Mapped[str | None] = mapped_column(String(255))
    documento_mongo_id: Mapped[str | None] = mapped_column(String(64))

    itens: Mapped[list["ItemNota"]] = relationship(back_populates="nota_fiscal", cascade="all, delete-orphan")


class ItemNota(Base, TimestampMixin):
    __tablename__ = "itens_nota"

    id: Mapped[int] = mapped_column(primary_key=True)
    nota_fiscal_id: Mapped[int] = mapped_column(ForeignKey("notas_fiscais.id"), nullable=False, index=True)
    descricao: Mapped[str] = mapped_column(String(500), nullable=False)
    quantidade: Mapped[Decimal | None] = mapped_column(Numeric(15, 4))

    nota_fiscal: Mapped[NotaFiscal] = relationship(back_populates="itens")


class ContaPagar(Base, TimestampMixin, AtivoMixin):
    __tablename__ = "contas_pagar"
    __table_args__ = (
        CheckConstraint(_status_in("status", STATUS_CONTA_PAGAR), name="ck_contas_pagar_status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    nota_fiscal_id: Mapped[int | None] = mapped_column(ForeignKey("notas_fiscais.id"), index=True)
    fornecedor_id: Mapped[int] = mapped_column(ForeignKey("fornecedores.id"), nullable=False, index=True)
    faturado_id: Mapped[int | None] = mapped_column(ForeignKey("faturados.id"), index=True)
    descricao: Mapped[str | None] = mapped_column(String(255))
    valor_total: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="ABERTA", server_default="ABERTA", nullable=False)

    despesas: Mapped[list["ContaPagarDespesa"]] = relationship(
        back_populates="conta_pagar", cascade="all, delete-orphan"
    )
    parcelas: Mapped[list["Parcela"]] = relationship(
        back_populates="conta_pagar", cascade="all, delete-orphan", order_by="Parcela.numero"
    )


class ContaReceber(Base, TimestampMixin, AtivoMixin):
    __tablename__ = "contas_receber"
    __table_args__ = (
        CheckConstraint(_status_in("status", STATUS_CONTA_RECEBER), name="ck_contas_receber_status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    cliente_id: Mapped[int] = mapped_column(ForeignKey("clientes.id"), nullable=False, index=True)
    descricao: Mapped[str | None] = mapped_column(String(255))
    valor_total: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="ABERTA", server_default="ABERTA", nullable=False)

    receitas: Mapped[list["ContaReceberReceita"]] = relationship(
        back_populates="conta_receber", cascade="all, delete-orphan"
    )
    parcelas: Mapped[list["Parcela"]] = relationship(
        back_populates="conta_receber", cascade="all, delete-orphan", order_by="Parcela.numero"
    )


class Parcela(Base, TimestampMixin):
    """Parcela de uma conta a pagar OU de uma conta a receber (exatamente uma das duas)."""

    __tablename__ = "parcelas"
    __table_args__ = (
        CheckConstraint(
            "(conta_pagar_id IS NOT NULL AND conta_receber_id IS NULL) OR "
            "(conta_pagar_id IS NULL AND conta_receber_id IS NOT NULL)",
            name="ck_parcelas_uma_conta",
        ),
        CheckConstraint(_status_in("status", STATUS_PARCELA), name="ck_parcelas_status"),
        UniqueConstraint("conta_pagar_id", "numero", name="uq_parcela_conta_pagar_numero"),
        UniqueConstraint("conta_receber_id", "numero", name="uq_parcela_conta_receber_numero"),
        Index("ix_parcelas_data_vencimento", "data_vencimento"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    conta_pagar_id: Mapped[int | None] = mapped_column(ForeignKey("contas_pagar.id"))
    conta_receber_id: Mapped[int | None] = mapped_column(ForeignKey("contas_receber.id"))
    numero: Mapped[int] = mapped_column(nullable=False)
    data_vencimento: Mapped[date | None] = mapped_column(Date)
    valor: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="ABERTA", server_default="ABERTA", nullable=False)
    data_pagamento: Mapped[date | None] = mapped_column(Date)

    conta_pagar: Mapped[ContaPagar | None] = relationship(back_populates="parcelas")
    conta_receber: Mapped[ContaReceber | None] = relationship(back_populates="parcelas")


class ContaPagarDespesa(Base, TimestampMixin):
    __tablename__ = "conta_pagar_despesas"
    __table_args__ = (
        UniqueConstraint("conta_pagar_id", "tipo_despesa_id", name="uq_conta_pagar_despesa"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    conta_pagar_id: Mapped[int] = mapped_column(ForeignKey("contas_pagar.id"), nullable=False)
    tipo_despesa_id: Mapped[int] = mapped_column(ForeignKey("tipos_despesa.id"), nullable=False, index=True)
    valor: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))

    conta_pagar: Mapped[ContaPagar] = relationship(back_populates="despesas")


class ContaReceberReceita(Base, TimestampMixin):
    __tablename__ = "conta_receber_receitas"
    __table_args__ = (
        UniqueConstraint("conta_receber_id", "tipo_receita_id", name="uq_conta_receber_receita"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    conta_receber_id: Mapped[int] = mapped_column(ForeignKey("contas_receber.id"), nullable=False)
    tipo_receita_id: Mapped[int] = mapped_column(ForeignKey("tipos_receita.id"), nullable=False, index=True)
    valor: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))

    conta_receber: Mapped[ContaReceber] = relationship(back_populates="receitas")
