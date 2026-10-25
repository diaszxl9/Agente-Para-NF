"""Contas a pagar/receber (MOVIMENTOCONTAS), suas classificações e parcelas (PARCELACONTAS).

Como em cadastros_service, nenhuma função faz commit: a transação é de quem chama.
"""

import sqlite3

from app.schemas.financeiro import (
    ClassificacaoResumo,
    MovimentoBase,
    MovimentoIn,
    MovimentoOut,
    MovimentoUpdate,
    ParcelaOut,
    PessoaResumo,
)
from app.services.cadastros_service import NOME_TIPO_PESSOA, obter_classificacao, obter_pessoa
from app.services.erros import NaoEncontradoError, NegocioError
from app.services.sanitize import corresponde_busca

# Quem pode ser a pessoa principal e qual tipo de classificação cada movimento aceita.
PESSOA_POR_MOVIMENTO = {"PAGAR": ("FORNECEDOR",), "RECEBER": ("CLIENTE", "FATURADO")}
CLASSIFICACAO_POR_MOVIMENTO = {"PAGAR": "DESPESA", "RECEBER": "RECEITA"}
TOLERANCIA_CENTAVOS = 0.01


def _pessoa_resumo(conn: sqlite3.Connection, pessoa_id: int | None) -> PessoaResumo | None:
    if pessoa_id is None:
        return None
    p = obter_pessoa(conn, pessoa_id)
    return PessoaResumo(id=p.id, tipo=p.tipo, razao_social=p.razao_social, documento=p.documento, status=p.status)


def _movimento(conn: sqlite3.Connection, row: sqlite3.Row) -> MovimentoOut:
    classificacoes = [
        ClassificacaoResumo(id=r["id"], descricao=r["descricao"], status=r["status"])
        for r in conn.execute(
            "SELECT c.id, c.descricao, c.status FROM movimento_classificacao mc "
            "JOIN classificacao c ON c.id = mc.classificacao_id WHERE mc.movimento_id = ? ORDER BY c.descricao",
            (row["id"],),
        )
    ]
    parcelas = [
        ParcelaOut(**dict(r))
        for r in conn.execute(
            "SELECT id, numero, identificacao, data_vencimento, valor, situacao FROM parcelacontas "
            "WHERE movimento_id = ? ORDER BY numero",
            (row["id"],),
        )
    ]
    return MovimentoOut(
        id=row["id"],
        tipo=row["tipo"],
        pessoa=_pessoa_resumo(conn, row["pessoa_id"]),
        faturado=_pessoa_resumo(conn, row["faturado_id"]),
        numero_nota=row["numero_nota"],
        data_emissao=row["data_emissao"],
        descricao=row["descricao"],
        valor_total=row["valor_total"],
        status=row["status"],
        data_cadastro=row["data_cadastro"],
        classificacoes=classificacoes,
        parcelas=parcelas,
    )


def obter_movimento(conn: sqlite3.Connection, movimento_id: int) -> MovimentoOut:
    row = conn.execute("SELECT * FROM movimentocontas WHERE id = ?", (movimento_id,)).fetchone()
    if not row:
        raise NaoEncontradoError(f"Movimento ID {movimento_id} não encontrado.")
    return _movimento(conn, row)


def listar_movimentos(
    conn: sqlite3.Connection, tipo: str | None = None, status: str | None = None, busca: str | None = None
) -> list[MovimentoOut]:
    sql, params = "SELECT * FROM movimentocontas WHERE 1 = 1", []
    if tipo:
        sql += " AND tipo = ?"
        params.append(tipo)
    if status:
        sql += " AND status = ?"
        params.append(status)
    movimentos = [_movimento(conn, r) for r in conn.execute(sql + " ORDER BY id DESC", params).fetchall()]
    return [
        m
        for m in movimentos
        if corresponde_busca(
            busca,
            str(m.id),
            m.pessoa.razao_social,
            m.pessoa.documento,
            m.faturado.razao_social if m.faturado else None,
            m.numero_nota,
            m.descricao,
            *(c.descricao for c in m.classificacoes),
        )
    ]


def buscar_movimento_da_nota(conn: sqlite3.Connection, tipo: str, pessoa_id: int, numero_nota: str) -> int | None:
    row = conn.execute(
        "SELECT id FROM movimentocontas WHERE tipo = ? AND pessoa_id = ? AND numero_nota = ? AND status = 'ATIVO'",
        (tipo, pessoa_id, numero_nota),
    ).fetchone()
    return row["id"] if row else None


def _validar_pessoa(conn: sqlite3.Connection, pessoa_id: int, tipos: tuple[str, ...], papel: str) -> None:
    try:
        pessoa = obter_pessoa(conn, pessoa_id)
    except NaoEncontradoError:
        raise NegocioError(f"{papel} ID {pessoa_id} não encontrado.") from None
    if pessoa.tipo not in tipos:
        esperado = " ou ".join(NOME_TIPO_PESSOA[t].lower() for t in tipos)
        raise NegocioError(f"{papel}: a pessoa ID {pessoa_id} não é {esperado}.")
    if pessoa.status != "ATIVO":
        raise NegocioError(f"{papel} \"{pessoa.razao_social}\" (ID {pessoa_id}) está INATIVO. Reative-o antes de lançar.")


def _validar_movimento(
    conn: sqlite3.Connection, tipo: str, dados: MovimentoBase, atual: MovimentoOut | None = None
) -> tuple[list[int], list[int]]:
    """Valida pessoas, classificações e parcelas. Na edição, o que já estava vinculado pode continuar mesmo inativo."""
    if not atual or atual.pessoa.id != dados.pessoa_id:
        _validar_pessoa(conn, dados.pessoa_id, PESSOA_POR_MOVIMENTO[tipo], "Fornecedor" if tipo == "PAGAR" else "Cliente")
    if dados.faturado_id is not None and not (atual and atual.faturado and atual.faturado.id == dados.faturado_id):
        _validar_pessoa(conn, dados.faturado_id, ("FATURADO", "CLIENTE"), "Faturado")

    tipo_classificacao = CLASSIFICACAO_POR_MOVIMENTO[tipo]
    ja_vinculadas = {c.id for c in atual.classificacoes} if atual else set()
    classificacao_ids = list(dict.fromkeys(dados.classificacao_ids))
    for cid in classificacao_ids:
        try:
            c = obter_classificacao(conn, cid)
        except NaoEncontradoError:
            raise NegocioError(f"Classificação ID {cid} não encontrada.") from None
        if c.tipo != tipo_classificacao:
            raise NegocioError(f"A classificação \"{c.descricao}\" não é de {tipo_classificacao.lower()}.")
        if c.status != "ATIVO" and cid not in ja_vinculadas:
            raise NegocioError(f"A classificação \"{c.descricao}\" (ID {cid}) está INATIVA. Reative-a antes de lançar.")

    soma = round(sum(p.valor for p in dados.parcelas), 2)
    if abs(soma - dados.valor_total) > TOLERANCIA_CENTAVOS:
        raise NegocioError(
            f"A soma das parcelas (R$ {soma:.2f}) é diferente do valor total (R$ {dados.valor_total:.2f})."
        )
    numeros = [p.numero or i for i, p in enumerate(dados.parcelas, start=1)]
    if len(set(numeros)) != len(numeros):
        raise NegocioError("Há parcelas com o mesmo número.")

    if dados.numero_nota:
        existente = buscar_movimento_da_nota(conn, tipo, dados.pessoa_id, dados.numero_nota)
        if existente and (not atual or existente != atual.id):
            raise NegocioError(
                f"A nota fiscal nº {dados.numero_nota} desta pessoa já foi lançada (movimento ID {existente}).", 409
            )
    return classificacao_ids, numeros


def _gravar_vinculos(
    conn: sqlite3.Connection, movimento_id: int, dados: MovimentoBase, classificacao_ids: list[int], numeros: list[int]
) -> None:
    conn.executemany(
        "INSERT INTO movimento_classificacao (movimento_id, classificacao_id) VALUES (?, ?)",
        [(movimento_id, cid) for cid in classificacao_ids],
    )
    total = len(dados.parcelas)
    conn.executemany(
        "INSERT INTO parcelacontas (movimento_id, numero, identificacao, data_vencimento, valor) VALUES (?, ?, ?, ?, ?)",
        [
            (
                movimento_id,
                numero,
                p.identificacao or (f"NF {dados.numero_nota} - {numero}/{total}" if dados.numero_nota else f"{numero}/{total}"),
                p.data_vencimento.isoformat(),
                round(p.valor, 2),
            )
            for numero, p in zip(numeros, dados.parcelas)
        ],
    )


def _colunas_movimento(dados: MovimentoBase) -> tuple:
    return (
        dados.pessoa_id,
        dados.faturado_id,
        dados.numero_nota,
        dados.data_emissao.isoformat() if dados.data_emissao else None,
        dados.descricao,
        round(dados.valor_total, 2),
    )


def criar_movimento(conn: sqlite3.Connection, dados: MovimentoIn) -> MovimentoOut:
    classificacao_ids, numeros = _validar_movimento(conn, dados.tipo, dados)
    cur = conn.execute(
        "INSERT INTO movimentocontas (tipo, pessoa_id, faturado_id, numero_nota, data_emissao, descricao, valor_total) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (dados.tipo, *_colunas_movimento(dados)),
    )
    _gravar_vinculos(conn, cur.lastrowid, dados, classificacao_ids, numeros)
    return obter_movimento(conn, cur.lastrowid)


def atualizar_movimento(conn: sqlite3.Connection, movimento_id: int, dados: MovimentoUpdate) -> MovimentoOut:
    """Edita o movimento e substitui suas classificações e parcelas (o STATUS não é alterado aqui)."""
    atual = obter_movimento(conn, movimento_id)
    if atual.status != "ATIVO":
        raise NegocioError(f"Movimento ID {movimento_id} está INATIVO. Reative-o antes de editar.", 409)
    if any(p.situacao == "QUITADA" for p in atual.parcelas):
        raise NegocioError("Há parcelas quitadas neste movimento. Reabra-as antes de editar.", 409)
    classificacao_ids, numeros = _validar_movimento(conn, atual.tipo, dados, atual)
    conn.execute(
        "UPDATE movimentocontas SET pessoa_id = ?, faturado_id = ?, numero_nota = ?, data_emissao = ?, descricao = ?, "
        "valor_total = ? WHERE id = ?",
        (*_colunas_movimento(dados), movimento_id),
    )
    # Parcelas e vínculos são itens do próprio movimento (não são cadastros): na edição são regravados.
    conn.execute("DELETE FROM movimento_classificacao WHERE movimento_id = ?", (movimento_id,))
    conn.execute("DELETE FROM parcelacontas WHERE movimento_id = ?", (movimento_id,))
    _gravar_vinculos(conn, movimento_id, dados, classificacao_ids, numeros)
    return obter_movimento(conn, movimento_id)


def alterar_status_movimento(conn: sqlite3.Connection, movimento_id: int, status: str) -> MovimentoOut:
    atual = obter_movimento(conn, movimento_id)
    if atual.status == status:
        raise NegocioError(f"Movimento ID {movimento_id} já está {status}.", 409)
    if status == "ATIVO" and atual.numero_nota:
        existente = buscar_movimento_da_nota(conn, atual.tipo, atual.pessoa.id, atual.numero_nota)
        if existente:
            raise NegocioError(
                f"Já existe outro lançamento ativo da nota fiscal nº {atual.numero_nota} (movimento ID {existente}).", 409
            )
    conn.execute("UPDATE movimentocontas SET status = ? WHERE id = ?", (status, movimento_id))
    return obter_movimento(conn, movimento_id)


def alterar_situacao_parcela(conn: sqlite3.Connection, parcela_id: int, situacao: str) -> MovimentoOut:
    row = conn.execute(
        "SELECT p.situacao, p.movimento_id, m.status FROM parcelacontas p "
        "JOIN movimentocontas m ON m.id = p.movimento_id WHERE p.id = ?",
        (parcela_id,),
    ).fetchone()
    if not row:
        raise NaoEncontradoError(f"Parcela ID {parcela_id} não encontrada.")
    if row["status"] != "ATIVO":
        raise NegocioError("O movimento desta parcela está INATIVO. Reative-o para alterar a parcela.", 409)
    if row["situacao"] == situacao:
        raise NegocioError(f"A parcela já está {situacao}.", 409)
    conn.execute("UPDATE parcelacontas SET situacao = ? WHERE id = ?", (situacao, parcela_id))
    return obter_movimento(conn, row["movimento_id"])
