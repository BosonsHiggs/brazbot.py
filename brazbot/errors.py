"""
Hierarquia de exceções nativas da biblioteca brazbot.py.
"""

from typing import Optional, Dict, Any


class BrazbotError(Exception):
    """Exceção base para todos os erros da biblioteca brazbot."""
    pass


class HTTPException(BrazbotError):
    """Exceção lançada quando uma requisição HTTP para a API do Discord falha."""

    def __init__(
        self,
        status: int,
        message: str = "",
        code: Optional[int] = None,
        errors: Optional[Dict[str, Any]] = None,
        response_data: Optional[Any] = None,
    ):
        self.status = status
        self.code = code or 0
        self.errors = errors or {}
        self.response_data = response_data
        self.discord_message = message
        formatted = f"HTTP {status}"
        if self.code:
            formatted += f" (Discord Code {self.code})"
        if message:
            formatted += f": {message}"
        if self.errors:
            formatted += f" | Details: {self.errors}"
        super().__init__(formatted)


class BadRequest(HTTPException):
    """HTTP 400 - Requisição inválida."""
    pass


class Unauthorized(HTTPException):
    """HTTP 401 - Token inválido ou não autorizado."""
    pass


class Forbidden(HTTPException):
    """HTTP 403 - Permissão insuficiente na API do Discord."""
    pass


class NotFound(HTTPException):
    """HTTP 404 - Recurso não encontrado."""
    pass


class RateLimited(HTTPException):
    """HTTP 429 - Limite de requisições atingido."""

    def __init__(self, retry_after: float, is_global: bool = False, scope: str = "shared"):
        self.retry_after = float(retry_after)
        self.is_global = is_global
        self.scope = scope
        super().__init__(
            429,
            f"Rate limited ({scope}, global={is_global}). Retry after {self.retry_after:.2f}s",
        )


class DiscordServerError(HTTPException):
    """HTTP 5xx - Erro interno nos servidores do Discord."""
    pass


class GatewayError(BrazbotError):
    """Erro relacionado à conexão WebSocket do Gateway do Discord."""

    def __init__(self, message: str, close_code: Optional[int] = None):
        self.close_code = close_code
        super().__init__(f"{message} (close_code={close_code})" if close_code else message)


class VoiceConnectionError(BrazbotError):
    """Erro ao conectar, autenticar ou transmitir áudio no Voice Gateway/UDP."""
    pass


class OpusError(VoiceConnectionError):
    """Erro na codificação ou decodificação de pacotes de áudio Opus."""
    pass


class CommandError(BrazbotError):
    """Erro base durante o registro ou execução de comandos."""
    pass


class CommandNotFound(CommandError):
    """Comando não encontrado."""
    pass


class MissingRequiredArgument(CommandError):
    """Argumento obrigatório ausente na chamada do comando."""

    def __init__(self, param_name: str):
        self.param_name = param_name
        super().__init__(f"O argumento obrigatório '{param_name}' não foi informado.")


class BadArgument(CommandError):
    """Erro de conversão de tipo de argumento."""
    pass


class CheckFailure(CommandError):
    """Falha em uma verificação de permissão ou restrição de comando."""
    pass


class MissingPermissions(CheckFailure):
    """O usuário não possui as permissões necessárias para executar o comando."""

    def __init__(self, missing_perms: list):
        self.missing_perms = missing_perms
        perms_str = ", ".join(missing_perms)
        super().__init__(f"Você não possui as permissões necessárias: {perms_str}")


class BotMissingPermissions(CheckFailure):
    """O bot não possui as permissões necessárias para executar a ação."""

    def __init__(self, missing_perms: list):
        self.missing_perms = missing_perms
        perms_str = ", ".join(missing_perms)
        super().__init__(f"O bot não possui as permissões necessárias: {perms_str}")


class NotOwner(CheckFailure):
    """O usuário não é o dono do servidor ou do bot."""
    pass


class CooldownError(CommandError):
    """O comando está em tempo de recarga (rate limit)."""

    def __init__(self, retry_after: float, scope: str = "user"):
        self.retry_after = float(retry_after)
        self.scope = scope
        super().__init__(
            f"Comando em recarga ({scope}). Tente novamente em {self.retry_after:.2f} segundos."
        )
