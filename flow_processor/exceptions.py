class FlowProcessorException(Exception):
    """Base exception for flow processor errors."""
    pass

class SecretException(Exception):
    """Base exception for secret errors."""
    pass

class NoScheduleException(FlowProcessorException):
    """Raised when no schedule is found."""
    pass

class FlowAlreadyAddedException(FlowProcessorException):
    """Raised when a flow is already added to the scheduler."""
    pass

class FlowNotFoundException(FlowProcessorException):
    """Raised when a flow is not found."""
    pass

class FlowAlreadyRunningException(FlowProcessorException):
    """Raised when a flow is already running."""
    pass

class FlowParsingException(FlowProcessorException):
    """Raised when a flow cannot be parsed."""
    pass

class BadSecretException(SecretException):
    """Raised when a secret is not valid."""
    pass

class SecretNotFoundException(SecretException):
    """Raised when a secret is not found."""
    pass

class FlowExitException(FlowProcessorException):
    """Raised when a flow exits."""
    def __init__(self, message, result=None):
        super().__init__(message)
        self.message = message
