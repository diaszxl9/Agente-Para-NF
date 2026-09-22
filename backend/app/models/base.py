from datetime import datetime

from sqlalchemy import Boolean, DateTime, func, true
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    criado_em: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )


class AtivoMixin:
    """Cadastros nunca são excluídos fisicamente: apenas ativo=True/False."""

    ativo: Mapped[bool] = mapped_column(Boolean, server_default=true(), default=True, nullable=False, index=True)
