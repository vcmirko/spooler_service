from flask import jsonify, request
import os
from flow_processor.config import LOG_PATH, LOG_FILE_NAME

def get_logs(lines=100):
    try:
        lines = int(lines)
        if lines <= 0:
            raise ValueError('Lines must be positive')
        log_file_path = os.path.join(LOG_PATH, LOG_FILE_NAME)
        if not os.path.exists(log_file_path):
            raise FileNotFoundError(f"Log file {log_file_path} not found")
        with open(log_file_path, 'r') as f:
            log_lines = f.readlines()[-lines:]
        return log_lines
    except Exception as e:
        raise e
