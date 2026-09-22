from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.services.sanitize import clean_text, format_cnpj, format_cpf, only_digits


def _texto_obrigatorio(value: str) -> str:
    texto = clean_text(value)
    if not texto:
        raise ValueError("Campo obrigatório.")
    return texto


def _cnpj(value: str | None) -> str | None:
    texto = clean_text(value, 30)
    if not texto:
        return None
    formatado = format_cnpj(texto)
    if not formatado:
        raise ValueError("CNPJ deve ter 14 dígitos.")
    return formatado


class _Saida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ativo: bool
    criado_em: datetime
    atualizado_em: datetime


class FornecedorIn(BaseModel):
    razao_social: str = Field(max_length=255)
    nome_fantasia: str | None = Field(default=None, max_length=255)
    cnpj: str | None = None

    v_razao = field_validator("razao_social")(_texto_obrigatorio)

    @field_validator("nome_fantasia")
    @classmethod
    def _fantasia(cls, v: str | None) -> str | None:
        return clean_text(v)

    v_cnpj = field_validator("cnpj")(_cnpj)


class FornecedorOut(_Saida):
    razao_social: str
    nome_fantasia: str | None
    cnpj: str | None


class ClienteIn(BaseModel):
    nome: str = Field(max_length=255)
    cpf_cnpj: str | None = None

    v_nome = field_validator("nome")(_texto_obrigatorio)

    @field_validator("cpf_cnpj")
    @classmethod
    def _doc(cls, v: str | None) -> str | None:
        texto = clean_text(v, 30)
        if not texto:
            return None
        digitos = only_digits(texto)
        if len(digitos) == 11:
            return format_cpf(digitos)
        if len(digitos) == 14:
            return format_cnpj(digitos)
        raise ValueError("Informe um CPF (11 dígitos) ou CNPJ (14 dígitos).")


class ClienteOut(_Saida):
    nome: str
    cpf_cnpj: str | None


class FaturadoIn(BaseModel):
    nome_completo: str = Field(max_length=255)
    cpf: str | None = None

    v_nome = field_validator("nome_completo")(_texto_obrigatorio)

    @field_validator("cpf")
    @classmethod
    def _cpf(cls, v: str | None) -> str | None:
        texto = clean_text(v, 30)
        if not texto:
            return None
        formatado = format_cpf(texto)
        if not formatado:
            raise ValueError("CPF deve ter 11 dígitos.")
        return formatado


class FaturadoOut(_Saida):
    nome_completo: str
    cpf: str | None


class TipoDespesaIn(BaseModel):
    grupo: str = Field(max_length=120)
    nome: str = Field(max_length=160)

    @field_validator("grupo")
    @classmethod
    def _grupo(cls, v: str) -> str:
        return _texto_obrigatorio(v).upper()

    v_nome = field_validator("nome")(_texto_obrigatorio)


class TipoDespesaOut(_Saida):
    grupo: str
    nome: str


class TipoReceitaIn(BaseModel):
    nome: str = Field(max_length=160)

    v_nome = field_validator("nome")(_texto_obrigatorio)


class TipoReceitaOut(_Saida):
    nome: str
