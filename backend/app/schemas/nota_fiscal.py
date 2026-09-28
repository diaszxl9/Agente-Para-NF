from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class Fornecedor(BaseModel):
    razao_social: str | None = None
    fantasia: str | None = None
    cnpj: str | None = None


class Faturado(BaseModel):
    nome_completo: str | None = None
    cpf: str | None = None


class NotaFiscalInfo(BaseModel):
    numero: str | None = None
    data_emissao: date | None = None


class Item(BaseModel):
    descricao: str
    quantidade: float | None = None


class Parcela(BaseModel):
    numero: int = Field(ge=1)
    data_vencimento: date | None = None
    valor: float | None = None


class Despesa(BaseModel):
    categoria: str | None = None
    subcategoria: str | None = None


class NotaFiscalExtraida(BaseModel):
    """Estrutura final (já validada e sanitizada) devolvida ao frontend."""

    fornecedor: Fornecedor = Field(default_factory=Fornecedor)
    faturado: Faturado = Field(default_factory=Faturado)
    nota_fiscal: NotaFiscalInfo = Field(default_factory=NotaFiscalInfo)
    itens: list[Item] = Field(default_factory=list)
    parcelas: list[Parcela] = Field(default_factory=list)
    valor_total: float | None = None
    despesas: list[Despesa] = Field(default_factory=list)


class ArquivoInfo(BaseModel):
    nome: str
    tamanho_bytes: int


class ExtracaoResponse(BaseModel):
    dados: NotaFiscalExtraida
    arquivo: ArquivoInfo
    modelo: str


class GeminiRawResponse(BaseModel):
    """Contrato bruto aceito da IA. Tudo é opcional/permissivo; a sanitização vem depois."""

    model_config = ConfigDict(extra="ignore")

    fornecedor: dict | None = None
    faturado: dict | None = None
    nota_fiscal: dict | None = None
    itens: list[dict | None] | None = None
    parcelas: list[dict | None] | None = None
    valor_total: str | int | float | None = None
    despesas: list[dict | None] | None = None
