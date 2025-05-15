import logging
import os
from ..step import Step
from flow_processor.config import FLOWS_PATH
import asyncio

class FlowLoopStep(Step):
    """Subclass for flow loop operations."""
    def __init__(self, step, flow):
        super().__init__(step, flow)
        assert "flow_loop" in step, "Flow loop configuration is required"
        self._flow_loop = step.get("flow_loop")
        assert "path" in self._flow_loop, "Flow path is required"
        self._path = os.path.join(FLOWS_PATH, self._flow_loop.get("path"))
        assert "data_key" in self._flow_loop, "Data key is required"
        self._data_key = self._flow_loop.get("data_key")
        self._list = self._flow._data.get(self._data_key)
        assert isinstance(self._list, list), "Data key must produce a list"

    def process(self):
        """Process the flow loop step."""
        # check if the step is enabled
        enabled = super().pre_process()
        if not enabled:
            return 

        logging.info(f"{self._representation} -> {self._path}")
        from flow_processor import Flow # recursive import
        logging.info(f"{self._representation} -> {self._path}")
        # Load the flow and process it
        self._data = []
        async def process_item(index, item):
            return await asyncio.to_thread(Flow(self._path,item,index+1).process)

        async def process_all():
            tasks = [process_item(index, item) for index, item in enumerate(self._list)]
            self._data = await asyncio.gather(*tasks)

        asyncio.run(process_all())

        # loop self._data, extend __errors__ to the flow._data __errors__
        for item in self._data:
            if "__errors__" in item:
                self._flow._data["__errors__"].extend(item["__errors__"])

        return super().process()
