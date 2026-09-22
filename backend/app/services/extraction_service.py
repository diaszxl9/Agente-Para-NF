import json
import logging
import re

from pydantic import ValidationError

from app.schemas.nota_fiscal import (
    ArquivoInfo,
    Despesa,
    ExtracaoResponse,
    Faturado,
    GeminiRawResponse,
    Item,
    NotaFiscalExtraida,
    NotaFiscalInfo,
    Parcela,
)
from app.schemas.nota_fiscal import Fornecedor as FornecedorSchema
from app.services import mongo_store
from app.services.gemini_service import GeminiError, GeminiService
from app.services.prompt import build_prompt
from app.services.sanitize import (
    clean_text,
    cnpj_is_valid,
    cpf_is_valid,
    format_cnpj,
    format_cpf,
    normalize_key,
    only_digits,
    parse_date,
    parse_number,
)

logger = logging.getLogger(__name__)

MAX_ITENS = 500
MAX_PARCELAS = 120
TOLERANCIA_VALOR = 0.01


def parse_ia_json(text: str) -> GeminiRawResponse:
    """Converte o texto da IA em JSON validado; tolera cercas de Markdown, nada além disso."""
    cleaned = text.strip()
    fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", cleaned, flags=re.DOTALL | re.IGNORECASE)
    if fence:
        cleaned = fence.group(1)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValueError("A IA não retornou um JSON válido.") from exc
    if not isinstance(data, dict):
        raise ValueError("A IA retornou um JSON em formato inesperado.")
    try:
        return GeminiRawResponse.model_validate(data)
    except ValidationError as exc:
        raise ValueError("O JSON da IA não segue a estrutura esperada.") from exc


def _classificar(
    raw_despesas: list[dict | None], categorias: dict[str, list[str]], avisos: list[str]
) -> list[Despesa]:
    grupos = {normalize_key(g): g for g in categorias}
    subs_por_grupo = {g: {normalize_key(s): s for s in subs} for g, subs in categorias.items()}
    resultado: list[Despesa] = []

    for entry in raw_despesas:
        if not entry:
            continue
        cat_txt = clean_text(entry.get("categoria"), 160)
        sub_txt = clean_text(entry.get("subcategoria"), 160)
        grupo = grupos.get(normalize_key(cat_txt)) if cat_txt else None
        sub_nome = None

        if sub_txt:
            chave = normalize_key(sub_txt)
            if grupo:
                sub_nome = subs_por_grupo[grupo].get(chave)
            else:
                candidatos = [g for g, subs in subs_por_grupo.items() if chave in subs]
                if len(candidatos) == 1:
                    grupo = candidatos[0]
                    sub_nome = subs_por_grupo[grupo][chave]

        if cat_txt and not grupo:
            avisos.append(f"Categoria '{cat_txt}' sugerida pela IA não está cadastrada e foi descartada.")
        if sub_txt and not sub_nome:
            avisos.append(f"Subcategoria '{sub_txt}' sugerida pela IA não está cadastrada e foi descartada.")
        if grupo:
            despesa = Despesa(categoria=grupo, subcategoria=sub_nome)
            if despesa not in resultado:
                resultado.append(despesa)

    if not resultado:
        avisos.append("Não foi possível classificar a despesa com as categorias cadastradas.")
    return resultado


def montar_resultado(
    raw: GeminiRawResponse, categorias: dict[str, list[str]]
) -> tuple[NotaFiscalExtraida, list[str]]:
    avisos: list[str] = []

    forn = raw.fornecedor or {}
    cnpj = format_cnpj(forn.get("cnpj"))
    if forn.get("cnpj") and not cnpj:
        avisos.append("O CNPJ do fornecedor não tem 14 dígitos e foi descartado.")
    elif cnpj and not cnpj_is_valid(only_digits(cnpj)):
        avisos.append("O CNPJ do fornecedor tem dígitos verificadores inválidos. Confira no documento.")
    fornecedor = FornecedorSchema(
        razao_social=clean_text(forn.get("razao_social")),
        fantasia=clean_text(forn.get("fantasia") or forn.get("nome_fantasia")),
        cnpj=cnpj,
    )

    fat = raw.faturado or {}
    cpf = format_cpf(fat.get("cpf"))
    if fat.get("cpf") and not cpf:
        avisos.append("O CPF do faturado não tem 11 dígitos e foi descartado.")
    elif cpf and not cpf_is_valid(only_digits(cpf)):
        avisos.append("O CPF do faturado tem dígitos verificadores inválidos. Confira no documento.")
    faturado = Faturado(nome_completo=clean_text(fat.get("nome_completo")), cpf=cpf)

    nf = raw.nota_fiscal or {}
    numero = clean_text(nf.get("numero"), 60)
    data_emissao = parse_date(nf.get("data_emissao"))
    if nf.get("data_emissao") and not data_emissao:
        avisos.append("A data de emissão retornada pela IA é inválida e foi descartada.")
    nota = NotaFiscalInfo(numero=numero, data_emissao=data_emissao)

    itens: list[Item] = []
    for entry in (raw.itens or [])[:MAX_ITENS]:
        if not entry:
            continue
        descricao = clean_text(entry.get("descricao"), 500)
        if descricao:
            itens.append(Item(descricao=descricao, quantidade=parse_number(entry.get("quantidade"), 4)))

    valor_total = parse_number(raw.valor_total, 2)

    parcelas: list[Parcela] = []
    usados: set[int] = set()
    for idx, entry in enumerate((raw.parcelas or [])[:MAX_PARCELAS], start=1):
        if not entry:
            continue
        num_bruto = parse_number(entry.get("numero"))
        num = int(num_bruto) if num_bruto and num_bruto >= 1 else idx
        while num in usados:
            num += 1
        usados.add(num)
        parcelas.append(
            Parcela(
                numero=num,
                data_vencimento=parse_date(entry.get("data_vencimento")),
                valor=parse_number(entry.get("valor"), 2),
            )
        )
    parcelas.sort(key=lambda p: p.numero)

    if not parcelas and valor_total is not None:
        parcelas = [Parcela(numero=1, data_vencimento=None, valor=valor_total)]
        avisos.append(
            "A nota não informa parcelas: foi considerada 1 parcela com o valor total e vencimento não informado."
        )

    soma = sum(p.valor for p in parcelas if p.valor is not None)
    if valor_total is not None and parcelas and all(p.valor is not None for p in parcelas):
        if abs(soma - valor_total) > TOLERANCIA_VALOR:
            avisos.append(
                f"A soma das parcelas ({soma:.2f}) difere do valor total da nota ({valor_total:.2f})."
            )

    if not itens:
        avisos.append("Nenhum item/produto foi identificado na nota.")

    despesas = _classificar(raw.despesas or [], categorias, avisos)

    resultado = NotaFiscalExtraida(
        fornecedor=fornecedor,
        faturado=faturado,
        nota_fiscal=nota,
        itens=itens,
        parcelas=parcelas,
        valor_total=valor_total,
        despesas=despesas,
    )
    return resultado, avisos


def extrair_nota_fiscal(
    pdf_bytes: bytes,
    nome_arquivo: str,
    gemini: GeminiService,
    categorias: dict[str, list[str]],
) -> ExtracaoResponse:
    prompt = build_prompt(categorias)

    raw: GeminiRawResponse | None = None
    texto_ia = ""
    for tentativa in (1, 2):
        texto_ia = gemini.gerar_json(pdf_bytes, prompt)
        try:
            raw = parse_ia_json(texto_ia)
            break
        except ValueError as exc:
            logger.warning("Resposta inválida do Gemini (tentativa %s): %s", tentativa, exc)
    if raw is None:
        mongo_store.salvar_documento(nome_arquivo, pdf_bytes, texto_ia, None, gemini.model, "ERRO_JSON_INVALIDO")
        raise GeminiError("A IA retornou uma resposta inválida. Tente extrair novamente.", 502)

    dados, avisos = montar_resultado(raw, categorias)
    documento_id = mongo_store.salvar_documento(
        nome_arquivo, pdf_bytes, texto_ia, dados.model_dump(mode="json"), gemini.model, "SUCESSO"
    )
    return ExtracaoResponse(
        dados=dados,
        avisos=avisos,
        arquivo=ArquivoInfo(nome=nome_arquivo, tamanho_bytes=len(pdf_bytes)),
        modelo=gemini.model,
        documento_id=documento_id,
    )
