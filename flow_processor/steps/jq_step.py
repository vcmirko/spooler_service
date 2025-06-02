import logging

from flow_processor.utils import apply_jq_filter

from ..step import Step


class JqStep(Step):
    """Subclass for jq operations."""

    def __init__(self, step, flow):
        super().__init__(step, flow)
        assert "jq" in step, "Jq configuration is required"
        self._jq = step.get("jq")
        assert "expression" in self._jq, "Jq expression is required"
        assert "data_key" in self._jq, "Data key is required"
        self._expression = self._jq.get("expression")
        self._data_key = self._jq.get("data_key")
        self._data = self._flow._data.get(self._data_key, {})

    def process(self, ignore_when=False):
        """Process the jq step."""

        # check if the step is enabled
        enabled = super().pre_process(ignore_when)
        if not enabled:
            return

        logging.info("%s -> %s", self._representation, self._expression)
        self._data = apply_jq_filter(self._data, self._expression)
        return super().process()
