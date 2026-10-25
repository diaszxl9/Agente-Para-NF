"""Banco SQLite (biblioteca padrão do Python) com cadastros, contas e parcelas.

Regras garantidas no próprio banco: chaves estrangeiras ligadas, unicidade de pessoa por (tipo, documento) e de
classificação por (tipo, descrição normalizada). Não existe DELETE de cadastro em nenhum lugar do sistema: registros
são INATIVADOS/REATIVADOS pela coluna status.
"""

import sqlite3
from collections.abc import Iterator
from pathlib import Path

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
"""

_inicializados: set[str] = set()


def conectar(caminho: str | None = None) -> sqlite3.Connection:
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


def get_db() -> Iterator[sqlite3.Connection]:
    """Uma conexão por requisição. Cada serviço controla a própria transação com `with conn:`."""
    conn = conectar()
    try:
        yield conn
    finally:
        conn.close()
