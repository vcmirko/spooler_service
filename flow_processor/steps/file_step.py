import yaml
import json
import logging
import os
from ..step import Step
from flow_processor.utils import apply_jinja2
from flow_processor.config import DATA_PATH

class FileStep(Step):
    """Subclass for file operations."""
    def __init__(self, step, flow):
        super().__init__(step, flow)
        assert "file" in step, "File configuration is required"
        self._file = step.get("file")
        assert "path" in self._file, "File path is required"
        self._file_path = os.path.join(DATA_PATH, apply_jinja2(self._file.get("path"), self._flow._data))
        self._file_type = self._file.get("type", "yaml")
        self._file_mode = self._file.get("mode", "read")

    def process(self, ignore_when=False):
        """Process the file step."""

        # check if the step is enabled
        enabled = super().pre_process(ignore_when)
        if not enabled:
            return 

        logging.info("%s -> %s %s", self._representation, self._file_mode, self._file_path)

        match self._file_mode:
            case "read":
                with open(self._file_path, "r") as file:
                    data = file.read()
                    self._data = self._parse_data(data, self._file_type)
            case "write":
                os.makedirs(os.path.dirname(self._file_path), exist_ok=True)
                with open(self._file_path, "w") as file:
                    self._write_data(file, self._file_type)
            case "append":
                os.makedirs(os.path.dirname(self._file_path), exist_ok=True)
                with open(self._file_path, "a") as file:
                    self._write_data(file, self._file_type)
            case _:
                raise Exception(f"Unsupported file method: {self._file_mode}")

        return super().process()


    def _parse_data(self, data, file_type):
        """Parse data based on the file type."""
        match file_type:
            case "yaml":
                return yaml.safe_load(data)
            case "json":
                return json.loads(data)
            case _:
                raise Exception(f"Unsupported file type: {file_type}")

    def _write_data(self, file, file_type):
        """Write data to a file based on the file type."""
        match file_type:
            case "yaml":
                yaml.dump(self._get_data_by_key(self._file["data_key"]), file, default_flow_style=False)
            case "json":
                json.dump(self._get_data_by_key(self._file["data_key"]), file)
            case _:
                raise Exception(f"Unsupported file type: {file_type}")        
