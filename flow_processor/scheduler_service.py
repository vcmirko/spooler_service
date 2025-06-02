import logging
import time
from threading import Event, Thread

import yaml

from flow_processor.config import CONFIG_FILE
from flow_processor.flow_scheduler import FlowScheduler
from flow_processor.job_store import abandon_all_running_jobs

# we make the scheduler a singleton
# so you can initialize it once and use it in the whole app
# any second call to get_instance will return the same instance


class SchedulerService:
    _instance = None
    _thread = None
    _ready = Event()

    @classmethod
    def get_instance(cls):
        if cls._instance is not None:
            return cls._instance

        def start_scheduler():
            logging.info("Starting scheduler service")
            abandon_all_running_jobs()
            cls._instance = FlowScheduler()
            with open(CONFIG_FILE, "r") as file:
                autostart_flows = yaml.safe_load(file).get("autostart_flows", [])
            for flow in autostart_flows:
                try:
                    cls._instance.add_flow(flow)
                except Exception as e:
                    logging.error("Failed to add flow: %s", e)
            cls._instance.start()
            cls._ready.set()
            while True:
                time.sleep(1)

        if cls._thread is None or not cls._thread.is_alive():
            cls._thread = Thread(target=start_scheduler, daemon=True)
            cls._thread.start()
            cls._ready.wait()
            logging.info("Scheduler initialized and ready.")

        return cls._instance
