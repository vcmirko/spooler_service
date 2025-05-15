import logging
import json
import yaml
from ..step import Step
from flow_processor.utils import apply_jinja2_from_file

class JinjaStep(Step):
    """Subclass for jinja operations."""
    def __init__(self, step, flow):
        super().__init__(step, flow)
        assert "jinja" in step, "Jinja configuration is required"
        self._jinja = step.get("jinja")
        assert "path" in self._jinja, "Jinja path is required"
        self._path = self._jinja.get("path")
        self._parse = self._jinja.get("parse", None)
        self._data_key = self._jinja.get("data_key",None)
        if self._data_key:
            self._data = self._flow._data.get(self._data_key)


    def process(self):
        """Process the jinja step."""

        # check if the step is enabled
        enabled = super().pre_process()
        if not enabled:
            return 

        logging.info(f"{self._representation} -> {self._path}")
        self._data = apply_jinja2_from_file(self._path, self._flow._data)
        match self._parse:
            case "json":
                self._data = json.loads(self._data)
            case "yaml":
                self._data = yaml.safe_load(self._data)
            case _:
                pass
        return super().process()    