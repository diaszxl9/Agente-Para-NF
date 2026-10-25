"""Segunda etapa: analisa os dados extraídos da nota, consulta o banco e lança a conta a pagar.

Fluxo: consultar fornecedor -> consultar faturado -> consultar classificações -> (exibir) -> criar o que não existe
-> criar movimento -> criar parcelas. O lançamento roda numa única transação: qualquer erro desfaz tudo.
"""

import sqlite3

from app.schemas.financeiro import (
    AnaliseResponse,
    ClassificacaoIn,
    ConsultaClassificacao,
    ConsultaPessoa,
    LancamentoResponse,
    MovimentoIn,
    ParcelaIn,
    PessoaIn,
)
from app.schemas.nota_fiscal import NotaFiscalExtraida
from app.services import cadastros_service as cadastros
from app.services import contas_service as contas
from app.services.erros import CODIGO_CADASTRO_INATIVO, NegocioError
from app.services.sanitize import format_documento, only_digits

MENSAGEM_SUCESSO = "Registro lançado com sucesso."


def _consultar_pessoa(conn: sqlite3.Connection, entidade: str, nome: str | None, documento: str | None) -> ConsultaPessoa:
    existente = cadastros.buscar_pessoa(conn, entidade, documento, nome)
    if existente:
        return ConsultaPessoa(
            entidade=entidade,
            nome=nome or existente.razao_social,
            documento=format_documento(documento) or existente.documento,
            existe=True,
            id=existente.id,
            status=existente.status,
            acao="UTILIZAR" if existente.status == "ATIVO" else "REATIVAR",
        )
    pode_criar = bool(nome and len(only_digits(documento or "")) in (11, 14))
    return ConsultaPessoa(
        entidade=entidade,
        nome=nome,
        documento=format_documento(documento),
        existe=False,
        acao="CRIAR" if pode_criar else "INDISPONIVEL",
    )


def _categorias(dados: NotaFiscalExtraida) -> list[str]:
    return list(dict.fromkeys(d.categoria for d in dados.despesas if d.categoria))


def _pendencias_da_nota(dados: NotaFiscalExtraida) -> list[str]:
    pendencias = []
    if not dados.parcelas:
        pendencias.append("Nenhuma parcela identificada na nota.")
    for p in dados.parcelas:
        if p.data_vencimento is None:
            pendencias.append(f"Parcela {p.numero} sem data de vencimento.")
        if p.valor is None or p.valor <= 0:
            pendencias.append(f"Parcela {p.numero} sem valor válido.")
    if dados.valor_total is None or dados.valor_total <= 0:
        pendencias.append("Valor total da nota ausente ou inválido.")
    elif dados.parcelas and all(p.valor for p in dados.parcelas):
        soma = round(sum(p.valor for p in dados.parcelas), 2)
        if abs(soma - dados.valor_total) > contas.TOLERANCIA_CENTAVOS:
            pendencias.append(
                f"A soma das parcelas (R$ {soma:.2f}) é diferente do valor total (R$ {dados.valor_total:.2f})."
            )
    return pendencias


def analisar(conn: sqlite3.Connection, dados: NotaFiscalExtraida) -> AnaliseResponse:
    pendencias: list[str] = []

    forn = dados.fornecedor
    fornecedor = _consultar_pessoa(conn, "FORNECEDOR", forn.razao_social or forn.fantasia, forn.cnpj)
    if fornecedor.acao == "INDISPONIVEL":
        pendencias.append("Fornecedor sem razão social ou CNPJ/CPF válido: não é possível cadastrá-lo.")

    fat = dados.faturado
    faturado = None
    if fat.nome_completo or fat.cpf:
        faturado = _consultar_pessoa(conn, "FATURADO", fat.nome_completo, fat.cpf)
        if faturado.acao == "INDISPONIVEL":
            pendencias.append("Faturado sem nome ou CPF/CNPJ válido: não é possível cadastrá-lo.")

    despesas = []
    for categoria in _categorias(dados):
        existente = cadastros.buscar_classificacao(conn, "DESPESA", categoria)
        despesas.append(
            ConsultaClassificacao(
                descricao=existente.descricao if existente else categoria,
                existe=bool(existente),
                id=existente.id if existente else None,
                status=existente.status if existente else None,
                acao=("UTILIZAR" if existente.status == "ATIVO" else "REATIVAR") if existente else "CRIAR",
            )
        )
    if not despesas:
        pendencias.append("Nenhuma classificação de despesa identificada na nota.")

    pendencias += _pendencias_da_nota(dados)

    numero = dados.nota_fiscal.numero
    if fornecedor.id and numero:
        lancado = contas.buscar_movimento_da_nota(conn, "PAGAR", fornecedor.id, numero)
        if lancado:
            pendencias.append(f"A nota fiscal nº {numero} deste fornecedor já foi lançada (movimento ID {lancado}).")

    return AnaliseResponse(fornecedor=fornecedor, faturado=faturado, despesas=despesas, pendencias=pendencias)


def _descricao_movimento(dados: NotaFiscalExtraida) -> str:
    base = f"NF {dados.nota_fiscal.numero}" if dados.nota_fiscal.numero else "Nota fiscal"
    if not dados.itens:
        return base
    extra = f" (+{len(dados.itens) - 1} itens)" if len(dados.itens) > 1 else ""
    return f"{base} - {dados.itens[0].descricao}{extra}"[:500]


def lancar(conn: sqlite3.Connection, dados: NotaFiscalExtraida, reativar_inativos: bool) -> LancamentoResponse:
    analise = analisar(conn, dados)
    if analise.pendencias:
        raise NegocioError("Não é possível lançar: " + " ".join(analise.pendencias))

    inativos = [c for c in (analise.fornecedor, analise.faturado, *analise.despesas) if c and c.acao == "REATIVAR"]
    if inativos and not reativar_inativos:
        nomes = ", ".join(f"{c.entidade.lower()} ID {c.id}" for c in inativos)
        raise NegocioError(
            f"Há cadastros INATIVOS ({nomes}). Confirme a reativação para utilizá-los no lançamento.",
            409,
            codigo=CODIGO_CADASTRO_INATIVO,
        )

    acoes: list[str] = []
    try:
        with conn:  # transação única: commit no fim, rollback em qualquer exceção
            def resolver_pessoa(consulta: ConsultaPessoa) -> int:
                nome = cadastros.NOME_TIPO_PESSOA[consulta.entidade]
                if consulta.acao == "CRIAR":
                    criada = cadastros.criar_pessoa(
                        conn,
                        PessoaIn(
                            tipo=consulta.entidade,
                            razao_social=consulta.nome,
                            fantasia=dados.fornecedor.fantasia if consulta.entidade == "FORNECEDOR" else None,
                            documento=consulta.documento,
                        ),
                    )
                    acoes.append(f"{nome} criado (ID {criada.id}).")
                    return criada.id
                if consulta.acao == "REATIVAR":
                    cadastros.alterar_status_pessoa(conn, consulta.id, "ATIVO")
                    acoes.append(f"{nome} reativado (ID {consulta.id}).")
                else:
                    acoes.append(f"{nome} existente utilizado (ID {consulta.id}).")
                return consulta.id

            fornecedor_id = resolver_pessoa(analise.fornecedor)
            faturado_id = resolver_pessoa(analise.faturado) if analise.faturado else None

            classificacao_ids = []
            for consulta in analise.despesas:
                if consulta.acao == "CRIAR":
                    criada = cadastros.criar_classificacao(conn, ClassificacaoIn(tipo="DESPESA", descricao=consulta.descricao))
                    acoes.append(f"Despesa \"{criada.descricao}\" criada (ID {criada.id}).")
                    classificacao_ids.append(criada.id)
                    continue
                if consulta.acao == "REATIVAR":
                    cadastros.alterar_status_classificacao(conn, consulta.id, "ATIVO")
                    acoes.append(f"Despesa \"{consulta.descricao}\" reativada (ID {consulta.id}).")
                else:
                    acoes.append(f"Despesa \"{consulta.descricao}\" existente utilizada (ID {consulta.id}).")
                classificacao_ids.append(consulta.id)

            movimento = contas.criar_movimento(
                conn,
                MovimentoIn(
                    tipo="PAGAR",
                    pessoa_id=fornecedor_id,
                    faturado_id=faturado_id,
                    numero_nota=dados.nota_fiscal.numero,
                    data_emissao=dados.nota_fiscal.data_emissao,
                    descricao=_descricao_movimento(dados),
                    valor_total=dados.valor_total,
                    classificacao_ids=classificacao_ids,
                    parcelas=[
                        ParcelaIn(numero=p.numero, data_vencimento=p.data_vencimento, valor=p.valor)
                        for p in dados.parcelas
                    ],
                ),
            )
            acoes.append(f"Movimento (conta a pagar) criado (ID {movimento.id}).")
            acoes.append(f"{len(movimento.parcelas)} parcela(s) criada(s).")
    except sqlite3.IntegrityError as exc:
        # Outro lançamento concorrente criou o mesmo cadastro entre a análise e a gravação: nada foi gravado.
        raise NegocioError("Conflito ao gravar o lançamento (registro duplicado). Analise a nota novamente.", 409) from exc

    return LancamentoResponse(mensagem=MENSAGEM_SUCESSO, acoes=acoes, movimento=movimento)
