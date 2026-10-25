from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, field_validator
from pydantic_core import PydanticCustomError

from app.schemas.nota_fiscal import NotaFiscalExtraida
from app.services.sanitize import clean_text, only_digits

TipoPessoa = Literal["CLIENTE", "FORNECEDOR", "FATURADO"]
TipoClassificacao = Literal["RECEITA", "DESPESA"]
TipoMovimento = Literal["PAGAR", "RECEBER"]
Status = Literal["ATIVO", "INATIVO"]
SituacaoParcela = Literal["ABERTA", "QUITADA"]


def _texto_obrigatorio(valor: str, campo: str, max_len: int = 255) -> str:
    texto = clean_text(valor, max_len)
    if not texto:
        raise PydanticCustomError("obrigatorio", f"Informe {campo}.")
    return texto


# ---------- Pessoas ----------
class PessoaBase(BaseModel):
    razao_social: str = Field(max_length=255)
    fantasia: str | None = Field(default=None, max_length=255)
    documento: str = Field(max_length=30)

    @field_validator("razao_social")
    @classmethod
    def _razao(cls, v: str) -> str:
        return _texto_obrigatorio(v, "a razão social/nome")

    @field_validator("fantasia")
    @classmethod
    def _fantasia(cls, v: str | None) -> str | None:
        return clean_text(v)

    @field_validator("documento")
    @classmethod
    def _documento(cls, v: str) -> str:
        digitos = only_digits(v or "")
        if len(digitos) not in (11, 14):
            raise PydanticCustomError("documento", "Informe um CPF (11 dígitos) ou CNPJ (14 dígitos).")
        return digitos


class PessoaIn(PessoaBase):
    tipo: TipoPessoa


class PessoaUpdate(PessoaBase):
    pass


class PessoaOut(BaseModel):
    id: int
    tipo: TipoPessoa
    razao_social: str
    fantasia: str | None
    documento: str
    status: Status
    data_cadastro: str


# ---------- Classificações ----------
class ClassificacaoUpdate(BaseModel):
    descricao: str = Field(max_length=160)

    @field_validator("descricao")
    @classmethod
    def _descricao(cls, v: str) -> str:
        return _texto_obrigatorio(v, "a descrição", 160)


class ClassificacaoIn(ClassificacaoUpdate):
    tipo: TipoClassificacao


class ClassificacaoOut(BaseModel):
    id: int
    tipo: TipoClassificacao
    descricao: str
    status: Status
    data_cadastro: str


# ---------- Contas (movimentos) e parcelas ----------
class ParcelaIn(BaseModel):
    numero: int | None = Field(default=None, ge=1)
    identificacao: str | None = Field(default=None, max_length=60)
    data_vencimento: date
    valor: float = Field(gt=0, le=1_000_000_000)


class MovimentoBase(BaseModel):
    pessoa_id: int
    faturado_id: int | None = None
    numero_nota: str | None = Field(default=None, max_length=60)
    data_emissao: date | None = None
    descricao: str = Field(max_length=500)
    valor_total: float = Field(gt=0, le=1_000_000_000)
    classificacao_ids: list[int] = Field(min_length=1, max_length=50)
    parcelas: list[ParcelaIn] = Field(min_length=1, max_length=120)

    @field_validator("descricao")
    @classmethod
    def _descricao(cls, v: str) -> str:
        return _texto_obrigatorio(v, "a descrição do movimento", 500)

    @field_validator("numero_nota")
    @classmethod
    def _numero(cls, v: str | None) -> str | None:
        return clean_text(v, 60)


class MovimentoIn(MovimentoBase):
    tipo: TipoMovimento


class MovimentoUpdate(MovimentoBase):
    """O tipo (pagar/receber) não muda na edição: classificações e pessoas dependem dele."""


class PessoaResumo(BaseModel):
    id: int
    tipo: TipoPessoa
    razao_social: str
    documento: str
    status: Status


class ClassificacaoResumo(BaseModel):
    id: int
    descricao: str
    status: Status


class ParcelaOut(BaseModel):
    id: int
    numero: int
    identificacao: str
    data_vencimento: date
    valor: float
    situacao: SituacaoParcela


class MovimentoOut(BaseModel):
    id: int
    tipo: TipoMovimento
    pessoa: PessoaResumo
    faturado: PessoaResumo | None
    numero_nota: str | None
    data_emissao: date | None
    descricao: str
    valor_total: float
    status: Status
    data_cadastro: str
    classificacoes: list[ClassificacaoResumo]
    parcelas: list[ParcelaOut]


# ---------- Segunda etapa: análise e lançamento da nota extraída ----------
AcaoConsulta = Literal["UTILIZAR", "CRIAR", "REATIVAR", "INDISPONIVEL"]


class ConsultaPessoa(BaseModel):
    entidade: Literal["FORNECEDOR", "FATURADO"]
    nome: str | None
    documento: str | None
    existe: bool
    id: int | None = None
    status: Status | None = None
    acao: AcaoConsulta


class ConsultaClassificacao(BaseModel):
    entidade: Literal["DESPESA"] = "DESPESA"
    descricao: str
    existe: bool
    id: int | None = None
    status: Status | None = None
    acao: AcaoConsulta


class AnaliseResponse(BaseModel):
    fornecedor: ConsultaPessoa
    faturado: ConsultaPessoa | None
    despesas: list[ConsultaClassificacao]
    # Problemas que impedem o lançamento (ex.: parcela sem vencimento). Vazio = pode lançar.
    pendencias: list[str]


class LancamentoRequest(BaseModel):
    dados: NotaFiscalExtraida
    # Cadastros encontrados INATIVOS só são usados se o usuário confirmar a reativação.
    reativar_inativos: bool = False


class LancamentoResponse(BaseModel):
    mensagem: str
    acoes: list[str]
    movimento: MovimentoOut
