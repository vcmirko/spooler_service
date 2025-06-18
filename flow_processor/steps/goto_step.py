
from ..step import Step
import logging
from flow_processor.utils import apply_jinja2

class GotoStep(Step):

    def __init__(self, step, flow):
        super().__init__(step, flow)
        assert "goto" in step, "Goto configuration is required"
        self._goto = step.get("goto")
        self._step_name = self._goto.get("step_name")
        assert isinstance(self._step_name, str), "Goto step name must be a string"
        assert self._step_name, "Goto step name cannot be empty"
        self._step_name = apply_jinja2(self._step_name, self._flow._data)

    def process(self):
        # Just return the step name to jump to
        return {"goto": self._step_name}

    def process(self, ignore_when=False):
        """Process the goto step."""

        # check if the step is enabled
        enabled = super().pre_process(ignore_when)
        if not enabled:
            return

        logging.info("%s -> %s", self._representation, self._step_name)
        return {"goto": self._step_name}
    
        # no post processing needed for goto step, it just returns the step name to jump to