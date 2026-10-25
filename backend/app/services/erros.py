class NegocioError(Exception):
    """Violação de regra de negócio (duplicidade, cadastro inativo, dado obrigatório...), apresentável ao usuário."""

    def __init__(self, message: str, status_code: int = 422, codigo: str | None = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.codigo = codigo


class NaoEncontradoError(NegocioError):
    def __init__(self, message: str):
        super().__init__(message, 404)


# Enviado ao frontend quando o lançamento depende de um cadastro INATIVO e a reativação não foi confirmada.
CODIGO_CADASTRO_INATIVO = "cadastro_inativo"
