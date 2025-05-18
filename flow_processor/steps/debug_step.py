import logging
from ..step import Step


class DebugStep(Step):
    """Subclass for debug operations."""
    def __init__(self, step, flow):
        super().__init__(step, flow)
        assert "debug" in step, "Debug configuration is required"
        self._debug = step.get("debug")
        self._type = self._debug.get("type", "yaml")
        self._data_key = self._debug.get("data_key","")
        if self._data_key == "":
            self._data = self._flow._data
        else:
            self._data = self._flow._data.get(self._data_key)

    def process(self, ignore_when=False):
        """Process the debug step."""

        # check if the step is enabled
        enabled = super().pre_process(ignore_when)
        if not enabled:
            return 

        logging.info("%s -> dumping debug data_key %s", self._representation, self._data_key)
        if(self._type == "yaml"):
            import yaml
            logging.info(yaml.dump(self._data, default_flow_style=False))
        elif(self._type == "json"):
            import json
            logging.info(json.dumps(self._data, indent=4))
        elif(self._type == "text"):
            import pprint
            logging.info(pprint.pformat(self._data))
        else:
            raise Exception(f"Unsupported debug type: {self._type}")
        
        return super().process()    