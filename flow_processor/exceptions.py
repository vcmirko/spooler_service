class FlowProcessorException(Exception):
    """Base exception for flow processor errors."""

    ...


class SecretException(Exception):
    """Base exception for secret errors."""

    ...


class NoScheduleException(FlowProcessorException):
    """Raised when no schedule is found."""

    ...


class FlowAlreadyAddedException(FlowProcessorException):
    """Raised when a flow is already added to the scheduler."""

    ...


class FlowNotFoundException(FlowProcessorException):
    """Raised when a flow is not found."""

    ...


class FlowAlreadyRunningException(FlowProcessorException):
    """Raised when a flow is already running."""

    ...


class FlowParsingException(FlowProcessorException):
    """Raised when a flow cannot be parsed."""

    ...


class BadSecretException(SecretException):
    """Raised when a secret is not valid."""

    ...


class SecretNotFoundException(SecretException):
    """Raised when a secret is not found."""

    ...


class FlowExitException(FlowProcessorException):
    """Raised when a flow exits."""

    def __init__(self, message, result=None):
        super().__init__(message)
        self.message = message
