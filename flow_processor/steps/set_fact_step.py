from ..step import Step
import logging
from flow_processor.utils import apply_jinja2

class SetFactStep(Step):

    def __init__(self, step, flow):
        super().__init__(step, flow)
        assert "value" in step, "SetFact configuration requires a 'value' property"
        self.value = step.get("value")

    def process(self):
        # No return, just set the fact (assume self.flow has a facts dict)
        self.flow.facts.update(self.value)

    def process(self, ignore_when=False):
        """Process the set_fact step."""

        # check if the step is enabled
        enabled = super().pre_process(ignore_when)
        if not enabled:
            return

        logging.info("%s -> %s", self._representation, self._expression)
        self._data = apply_jinja2(self.value, self._flow._data)
        return super().process()
