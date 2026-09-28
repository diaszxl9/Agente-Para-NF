import re
import unicodedata
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_NULL_WORDS = {"", "null", "none", "n/a", "na", "nao informado", "não informado", "-"}


def clean_text(value: Any, max_len: int = 255) -> str | None:
    if value is None or isinstance(value, (dict, list)):
        return None
    text = _CONTROL_CHARS.sub("", str(value))
    text = re.sub(r"\s+", " ", text).strip()
    if text.lower() in _NULL_WORDS:
        return None
    return text[:max_len]


def normalize_key(value: str) -> str:
    """Minúsculas, sem acentos e sem espaços duplicados — para comparar categorias."""
    decomposed = unicodedata.normalize("NFKD", value)
    ascii_only = "".join(c for c in decomposed if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", ascii_only).strip().lower()


def only_digits(value: str) -> str:
    return re.sub(r"\D", "", value)


def format_cnpj(value: Any) -> str | None:
    text = clean_text(value)
    if not text:
        return None
    d = only_digits(text)
    if len(d) != 14:
        return None
    return f"{d[:2]}.{d[2:5]}.{d[5:8]}/{d[8:12]}-{d[12:]}"


def format_cpf(value: Any) -> str | None:
    text = clean_text(value)
    if not text:
        return None
    d = only_digits(text)
    if len(d) != 11:
        return None
    return f"{d[:3]}.{d[3:6]}.{d[6:9]}-{d[9:]}"


def parse_date(value: Any) -> date | None:
    text = clean_text(value, 40)
    if not text:
        return None
    text = text[:10]
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y"):
        try:
            parsed = datetime.strptime(text, fmt).date()
        except ValueError:
            continue
        if 1990 <= parsed.year <= 2100:
            return parsed
        return None
    return None


def parse_number(value: Any, decimals: int | None = None) -> float | None:
    """Aceita número JSON ou texto em formato BR ('1.234,56') ou US ('1234.56')."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float, Decimal)):
        number = Decimal(str(value))
    else:
        text = clean_text(value, 40)
        if not text:
            return None
        text = re.sub(r"[^\d,.\-]", "", text)
        if "," in text:
            text = text.replace(".", "").replace(",", ".")
        elif text.count(".") > 1:
            text = text.replace(".", "")
        try:
            number = Decimal(text)
        except InvalidOperation:
            return None
    if not number.is_finite() or number < 0:
        return None
    if decimals is not None:
        number = round(number, decimals)
    return float(number)
