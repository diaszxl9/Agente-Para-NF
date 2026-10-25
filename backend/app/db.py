"""Acesso ao banco com cadastros, contas e parcelas.

- PostgreSQL (produção, ex.: Render) quando DATABASE_URL está definida. As tabelas são criadas pelas migrations do
  Prisma em database/prisma (o backend NÃO cria tabelas no PostgreSQL).
- SQLite local (biblioteca padrão) quando DATABASE_URL está vazia: desenvolvimento e testes. As tabelas são criadas
  pelo SCHEMA abaixo, que espelha database/prisma/schema.prisma — altere os dois juntos.

Os serviços escrevem SQL único, compatível com os dois bancos: parâmetros com "?" (convertidos para o PostgreSQL),
INSERT ... RETURNING id e linhas acessadas por nome (row["coluna"]). Regras garantidas no próprio banco: chaves
estrangeiras, unicidade de pessoa por (tipo, documento) e de classificação por (tipo, descrição normalizada). Não existe
DELETE de cadastro em nenhum lugar do sistema: registros são INATIVADOS/REATIVADOS pela coluna status.
"""

import sqlite3
from collections.abc import Iterable, Iterator, Mapping, Sequence
from pathlib import Path
from typing import Any, Protocol

import psycopg
from psycopg.rows import dict_row

from app.config import get_settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS pessoas (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo          TEXT NOT NULL CHECK (tipo IN ('CLIENTE', 'FORNECEDOR', 'FATURADO')),
    razao_social  TEXT NOT NULL,
    fantasia      TEXT,
    documento     TEXT NOT NULL,              -- CPF (11) ou CNPJ (14), somente dígitos
    status        TEXT NOT NULL DEFAULT 'ATIVO' CHECK (status IN ('ATIVO', 'INATIVO')),
    data_cadastro TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (tipo, documento)
);

CREATE TABLE IF NOT EXISTS classificacao (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo          TEXT NOT NULL CHECK (tipo IN ('RECEITA', 'DESPESA')),
    descricao     TEXT NOT NULL,
    chave         TEXT NOT NULL,              -- descrição normalizada (sem acento/caixa), evita duplicatas
    status        TEXT NOT NULL DEFAULT 'ATIVO' CHECK (status IN ('ATIVO', 'INATIVO')),
    data_cadastro TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (tipo, chave)
);

CREATE TABLE IF NOT EXISTS movimentocontas (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo          TEXT NOT NULL CHECK (tipo IN ('PAGAR', 'RECEBER')),
    pessoa_id     INTEGER NOT NULL REFERENCES pessoas (id),   -- fornecedor (PAGAR) ou cliente/faturado (RECEBER)
    faturado_id   INTEGER REFERENCES pessoas (id),            -- destinatário da nota, quando houver
    numero_nota   TEXT,
    data_emissao  TEXT,
    descricao     TEXT NOT NULL,
    valor_total   REAL NOT NULL CHECK (valor_total > 0),
    status        TEXT NOT NULL DEFAULT 'ATIVO' CHECK (status IN ('ATIVO', 'INATIVO')),
    data_cadastro TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS movimento_classificacao (
    movimento_id     INTEGER NOT NULL REFERENCES movimentocontas (id),
    classificacao_id INTEGER NOT NULL REFERENCES classificacao (id),
    PRIMARY KEY (movimento_id, classificacao_id)
);

CREATE TABLE IF NOT EXISTS parcelacontas (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    movimento_id    INTEGER NOT NULL REFERENCES movimentocontas (id),
    numero          INTEGER NOT NULL CHECK (numero >= 1),
    identificacao   TEXT NOT NULL,
    data_vencimento TEXT NOT NULL,
    valor           REAL NOT NULL CHECK (valor > 0),
    situacao        TEXT NOT NULL DEFAULT 'ABERTA' CHECK (situacao IN ('ABERTA', 'QUITADA')),
    UNIQUE (movimento_id, numero)
);

CREATE INDEX IF NOT EXISTS ix_parcelacontas_movimento ON parcelacontas (movimento_id);
CREATE INDEX IF NOT EXISTS ix_movimentocontas_tipo ON movimentocontas (tipo);
CREATE INDEX IF NOT EXISTS ix_movimentocontas_nota ON movimentocontas (pessoa_id, numero_nota);
"""

# Exceções dos dois bancos, para os handlers e serviços não dependerem de qual está em uso.
ERROS_INTEGRIDADE = (sqlite3.IntegrityError, psycopg.IntegrityError)
ERROS_BANCO = (sqlite3.Error, psycopg.Error)

# Linha de resultado: sqlite3.Row ou dict (psycopg). Nos dois, acesse por nome: row["coluna"] e dict(row).
Linha = Mapping[str, Any]


class Cursor(Protocol):
    def fetchone(self) -> Any: ...
    def fetchall(self) -> list[Any]: ...
    def __iter__(self) -> Iterator[Any]: ...


class Conexao(Protocol):
    """O que os serviços usam da conexão. `with conn:` = transação (commit no fim, rollback em exceção)."""

    def execute(self, sql: str, params: Sequence[Any] = ...) -> Cursor: ...
    def executemany(self, sql: str, seq: Iterable[Sequence[Any]]) -> Any: ...
    def __enter__(self) -> Any: ...
    def __exit__(self, *exc: Any) -> Any: ...
    def close(self) -> None: ...


class ConexaoPostgres:
    """Adapta o psycopg à interface do sqlite3 usada nos serviços (inclusive `with conn:` sem fechar a conexão)."""

    def __init__(self, url: str):
        # prepare_threshold=None desliga os prepared statements automáticos, incompatíveis com poolers (PgBouncer)
        # e com o PostgreSQL local do `prisma dev`. As consultas são simples: não há perda relevante.
        self._conn = psycopg.connect(url, row_factory=dict_row, connect_timeout=10, prepare_threshold=None)

    @staticmethod
    def _sql(sql: str) -> str:
        return sql.replace("?", "%s")

    def execute(self, sql: str, params: Sequence[Any] = ()) -> psycopg.Cursor:
        return self._conn.execute(self._sql(sql), params)

    def executemany(self, sql: str, seq: Iterable[Sequence[Any]]) -> None:
        # Um execute por linha (poucas linhas: parcelas/classificações de uma conta). O executemany do psycopg usa
        # o modo pipeline, que nem todo servidor compatível suporta (ex.: o PostgreSQL local do `prisma dev`).
        with self._conn.cursor() as cur:
            for params in seq:
                cur.execute(self._sql(sql), params)

    def __enter__(self) -> "ConexaoPostgres":
        return self

    def __exit__(self, tipo_exc: Any, *_: Any) -> bool:
        if tipo_exc is None:
            self._conn.commit()
        else:
            self._conn.rollback()
        return False

    def close(self) -> None:
        self._conn.close()


_inicializados: set[str] = set()


def conectar_sqlite(caminho: str | None = None) -> sqlite3.Connection:
    caminho = caminho or get_settings().database_path
    if caminho != ":memory:":
        Path(caminho).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(caminho, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    if caminho not in _inicializados or caminho == ":memory:":
        conn.executescript(SCHEMA)
        _inicializados.add(caminho)
    return conn


def conectar() -> Conexao:
    url = get_settings().database_url
    return ConexaoPostgres(url) if url else conectar_sqlite()


def get_db() -> Iterator[Conexao]:
    """Uma conexão por requisição. Cada serviço controla a própria transação com `with conn:`."""
    conn = conectar()
    try:
        yield conn
    finally:
        conn.close()
