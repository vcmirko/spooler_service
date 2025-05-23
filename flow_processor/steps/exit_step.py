import logging
from ..step import Step
from ..exceptions import FlowExitException

class ExitStep(Step):
    """Subclass for exit operations."""
    def __init__(self, step, flow):
        super().__init__(step, flow)
        assert "exit" in step, "exit property is required"
        self._exit = step.get("exit", {})
        assert "message" in self._exit, "exit message is required"
        self._message = self._exit.get("message", "")

    def process(self, ignore_when=False):
        """Process the exit step."""

        # check if the step is enabled
        enabled = super().pre_process(ignore_when)
        if not enabled:
            return 

        logging.info("%s -> exiting with message: %s", self._representation, self._message)
        self._data = {
            "message": self._message
        }
        
        raise FlowExitException("Flow exited with message: {}".format(self._message))