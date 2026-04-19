"""Domain-specific exceptions."""


class AIOpsError(Exception):
    """Base exception."""


class ConfigError(AIOpsError):
    pass


class RetrievalError(AIOpsError):
    pass


class LLMError(AIOpsError):
    pass


class CircuitOpenError(AIOpsError):
    pass


class ExternalServiceError(AIOpsError):
    pass
