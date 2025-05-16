import os
from flow_processor.config import LOCK_PATH
from flow_processor.utils import make_timestamp

def is_locked(flow_name):
    return os.path.exists(os.path.join(LOCK_PATH, f"{flow_name}.lock"))

def create_lock(flow_name):
    os.makedirs(LOCK_PATH, exist_ok=True)
    lock_path = os.path.join(LOCK_PATH, f"{flow_name}.lock")
    with open(lock_path, "w") as lock_file:
        lock_file.write(make_timestamp())
    return lock_path


def release_lock(flow_name):
    lock_path = os.path.join(LOCK_PATH, f"{flow_name}.lock")
    if os.path.exists(lock_path):
        os.remove(lock_path)
        return (f"Released lock {lock_path}")
    else:
        raise FileNotFoundError(f"Lock file {lock_path} does not exist.")

def release_all_locks():
    """Release all locks in the LOCK_PATH directory."""
    if os.path.exists(LOCK_PATH):
        for root, dirs, files in os.walk(LOCK_PATH):
            for file in files:
                if file.endswith(".lock"):
                    os.remove(os.path.join(root, file))
                    return (f"Released all locks in {LOCK_PATH}")


def get_all_locks():
    locks = []
    if os.path.exists(LOCK_PATH):
        for root, dirs, files in os.walk(LOCK_PATH):
            for file in files:
                if file.endswith(".lock"):
                    # make a dict with the filename and the timestamp (the file content=> read the file)
                    with open(os.path.join(root, file), "r") as lock_file:
                        timestamp = lock_file.read().strip()
                    lock_info = {
                        "filename": file,
                        "timestamp": timestamp,
                    }
                    locks.append(lock_info)
    return locks