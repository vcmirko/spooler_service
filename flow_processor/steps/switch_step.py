import re
import logging
from ..step import Step


class SwitchStep(Step):
    def __init__(self, step, flow):
        super().__init__(step, flow)
        assert "switch" in step, "Switch configuration is required"
        self._switch = step.get("switch")
        self._data_key = self._switch.get("data_key")
        assert self._data_key, "Data key for switch is required"
        self._cases = self._switch.get("cases", [])

        # Validate switch configuration
        assert isinstance(self._switch, dict), "Switch must be a dictionary"
        assert isinstance(self._data_key, str), "Data key must be a string"
        assert "cases" in self._switch, "Switch cases are required"
        assert isinstance(self._switch["cases"], list), "Switch cases must be a list"


    def process(self, ignore_when=False):
        """Process the file step."""
        from ..step_factory import create_step
        # check if the step is enabled
        enabled = super().pre_process(ignore_when)
        if not enabled:
            return

        logging.info(
            "%s -> %s", self._representation, self._data_key
        )


        value = self._flow._data.get(self._data_key)
        for rule in self._cases:
            assert "when" in rule, "Each case must have a 'when' condition"
            assert "step" in rule, "Each case must have a 'step' to execute"
            logging.debug("Comparing '%s' -> '%s'",str(value),rule["when"]  )
            if re.match(rule["when"], str(value)):
                step_conf = rule["step"]
                step_obj = create_step(step_conf, self._flow)
                return step_obj.process() # return, could be a goto step


