import os
import json
from .config import LOG_PATH, SCRIPT_PATH


def load_log_file_path() -> str:
    """Load the log file path from the logging configuration."""
    with open(f"{SCRIPT_PATH}/flow_processor/logging_config.json", "r") as f:
        logging_config = json.load(f)
        return str(os.path.join(LOG_PATH, logging_config["handlers"]["file"]["filename"]))


def get_logs(lines=100):
    try:
        lines = int(lines)
        if lines <= 0:
            raise ValueError("Lines must be positive")
        log_file_path = load_log_file_path()
        if not os.path.exists(log_file_path):
            raise FileNotFoundError(f"Log file {log_file_path} not found")
        with open(log_file_path, "r") as f:
            log_lines = f.readlines()[-lines:]
        return log_lines
    except Exception as e:
        raise e
