class FlowProcessorException(Exception):
    """Base exception for flow processor errors."""
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