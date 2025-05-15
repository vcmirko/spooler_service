class FlowProcessorException(Exception):
    """Base exception for flow processor errors."""
    pass

class NoScheduleException(FlowProcessorException):
    """Raised when no schedule is found."""
    pass

class FlowAlreadyAddedException(FlowProcessorException):
    """Raised when a flow is already added to the scheduler."""
    pass
