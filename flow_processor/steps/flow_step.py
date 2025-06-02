import logging
import os

from flow_processor.config import FLOWS_PATH

from ..step import Step


class FlowStep(Step):
    """
    FlowStep is a subclass of Step that represents a specific step in a flow operation.
    Attributes:
        _flow (dict): The flow configuration dictionary extracted from the step.
        _path (str): The relative path of the flow, derived from the flow configuration.
        _data_key (str): The key used to retrieve specific data from the flow configuration.
        _payload (Any): The payload data associated with the specified data key in the flow.
    Methods:
        __init__(step, flow_parent):
            Initializes the FlowStep instance with the given step configuration and parent flow.
            Validates the presence of required flow configuration keys.
        process():
            Processes the flow step by invoking the Flow processor with the specified path and payload.
            Logs the operation and invokes the parent class's process method.
    """

    def __init__(self, step, flow_parent):
        super().__init__(step, flow_parent)
        assert "flow" in step, "Flow configuration is required"
        self._flow = step.get("flow")
        assert "path" in self._flow, "Flow path is required"
        self._path = os.path.join(FLOWS_PATH, self._flow.get("path"))
        assert "data_key" in self._flow, "Data key is required"
        self._data_key = self._flow.get("data_key")
        self._payload = self._flow._data.get(self._data_key)

    def process(self, ignore_when=False):
        """Process the flow step."""

        # check if the step is enabled
        enabled = super().pre_process(ignore_when)
        if not enabled:
            return

        from flow_processor import Flow  # recursive import

        logging.info("%s -> %s", self._representation, self._path)
        self._data = Flow(self._path, self._payload).process()
        return super().process()
