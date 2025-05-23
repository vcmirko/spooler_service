import logging
from ..step import Step


class SleepStep(Step):
    """Subclass for sleep operations."""
    def __init__(self, step, flow):
        super().__init__(step, flow)
        assert "sleep" in step, "sleep property is required"
        self._sleep = step.get("sleep", {})
        assert "seconds" in self._sleep, "sleep seconds is required"
        self._seconds = self._sleep.get("seconds", 0)

    def process(self, ignore_when=False):
        """Process the sleep step."""

        # check if the step is enabled
        enabled = super().pre_process(ignore_when)
        if not enabled:
            return 

        logging.info("%s -> sleeping for %s seconds", self._representation, self._seconds)
        import time
        time.sleep(self._seconds)
        
        return super().process()    