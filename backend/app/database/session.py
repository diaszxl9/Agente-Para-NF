import logging
import threading
import time
from collections.abc import Iterator

from sqlalchemy import create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import get_settings
from app.database.categorias_padrao import CATEGORIAS_PADRAO
from app.models import Base, TipoDespesa

logger = logging.getLogger(__name__)

RETRY_INTERVAL_SECONDS = 15


def _build_engine(url: str) -> Engine:
    if url.startswith("sqlite"):
        kwargs: dict = {"connect_args": {"check_same_thread": False}}
        if ":memory:" in url or url in ("sqlite://", "sqlite:///"):
            kwargs["poolclass"] = StaticPool
        return create_engine(url, **kwargs)
    return create_engine(url, pool_pre_ping=True, pool_recycle=1800, connect_args={"connect_timeout": 3})


engine: Engine = _build_engine(get_settings().DATABASE_URL)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

_lock = threading.Lock()
_ready = False
_last_failure = 0.0


def configure_engine(url: str) -> None:
    """Troca o banco (usado nos testes) e força nova inicialização."""
    global engine, _ready, _last_failure
    engine = _build_engine(url)
    SessionLocal.configure(bind=engine)
    _ready = False
    _last_failure = 0.0


def seed_tipos_despesa(session: Session) -> None:
    existentes = {(t.grupo, t.nome) for t in session.scalars(select(TipoDespesa))}
    for grupo, nomes in CATEGORIAS_PADRAO.items():
        for nome in nomes:
            if (grupo, nome) not in existentes:
                session.add(TipoDespesa(grupo=grupo, nome=nome))
    session.commit()


def init_db() -> bool:
    """Cria as tabelas e o seed. Nunca lança: o sistema sobe mesmo sem MySQL."""
    global _ready, _last_failure
    with _lock:
        if _ready:
            return True
        if _last_failure and time.monotonic() - _last_failure < RETRY_INTERVAL_SECONDS:
            return False
        try:
            Base.metadata.create_all(engine)
            with SessionLocal() as session:
                seed_tipos_despesa(session)
            _ready = True
            logger.info("Banco de dados inicializado.")
        except SQLAlchemyError as exc:
            _last_failure = time.monotonic()
            logger.warning("Banco de dados indisponível: %s", exc.__class__.__name__)
        return _ready


def get_db() -> Iterator[Session]:
    init_db()
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def listar_categorias() -> dict[str, list[str]]:
    """Categorias ativas cadastradas no banco; se o banco estiver fora, usa o padrão."""
    if init_db():
        try:
            with SessionLocal() as session:
                categorias: dict[str, list[str]] = {}
                rows = session.scalars(
                    select(TipoDespesa).where(TipoDespesa.ativo.is_(True)).order_by(TipoDespesa.id)
                )
                for tipo in rows:
                    categorias.setdefault(tipo.grupo, []).append(tipo.nome)
                if categorias:
                    return categorias
        except SQLAlchemyError:
            logger.warning("Falha ao ler tipos de despesa; usando categorias padrão.")
    return {grupo: list(nomes) for grupo, nomes in CATEGORIAS_PADRAO.items()}
