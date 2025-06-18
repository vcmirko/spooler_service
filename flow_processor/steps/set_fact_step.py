from ..step import Step
import logging
from flow_processor.utils import apply_jinja2

class SetFactStep(Step):

    def __init__(self, step, flow):
        super().__init__(step, flow)
        self._set_fact = step.get("set_fact")
        assert self._set_fact, "SetFact configuration is required"
        assert isinstance(self._set_fact, dict), "SetFact must be a dictionary"
        assert "value" in self._set_fact, "SetFact configuration requires a 'value' property"
        self._value = self._set_fact.get("value")
        assert self._value, "SetFact value cannot be empty"

    def process(self):
        # No return, just set the fact (assume self.flow has a facts dict)
        self.flow.facts.update(self.value)

    def process(self, ignore_when=False):
        """Process the set_fact step."""

        # check if the step is enabled
        enabled = super().pre_process(ignore_when)
        if not enabled:
            return

        logging.info("%s -> %s", self._representation, self._value)
        self._data = apply_jinja2(self._value, self._flow._data)
        return super().process()
