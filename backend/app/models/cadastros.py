from sqlalchemy import String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import AtivoMixin, Base, TimestampMixin


class Fornecedor(Base, TimestampMixin, AtivoMixin):
    __tablename__ = "fornecedores"

    id: Mapped[int] = mapped_column(primary_key=True)
    razao_social: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    nome_fantasia: Mapped[str | None] = mapped_column(String(255))
    cnpj: Mapped[str | None] = mapped_column(String(18), unique=True)


class Cliente(Base, TimestampMixin, AtivoMixin):
    __tablename__ = "clientes"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    cpf_cnpj: Mapped[str | None] = mapped_column(String(18), unique=True)


class Faturado(Base, TimestampMixin, AtivoMixin):
    __tablename__ = "faturados"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome_completo: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    cpf: Mapped[str | None] = mapped_column(String(14), unique=True)


class TipoDespesa(Base, TimestampMixin, AtivoMixin):
    """`grupo` é a categoria (ex.: MANUTENÇÃO E OPERAÇÃO); `nome` é a subcategoria."""

    __tablename__ = "tipos_despesa"
    __table_args__ = (UniqueConstraint("grupo", "nome", name="uq_tipos_despesa_grupo_nome"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    grupo: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    nome: Mapped[str] = mapped_column(String(160), nullable=False)


class TipoReceita(Base, TimestampMixin, AtivoMixin):
    __tablename__ = "tipos_receita"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(160), nullable=False, unique=True)
