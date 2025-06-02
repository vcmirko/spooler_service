import logging
import threading
import time
import uuid
from datetime import datetime
from threading import Thread

import schedule
from croniter import croniter

from flow_processor.config import FLOW_TIMEOUT_SECONDS, TZ
from flow_processor.exceptions import (
    FlowAlreadyAddedException,
    FlowAlreadyRunningException,
    FlowNotFoundException,
    NoScheduleException,
)
from flow_processor.flow import Flow
from flow_processor.flow_runner import FlowRunner

# logging.basicConfig()
# schedule_logger = logging.getLogger('schedule')
# schedule_logger.setLevel(level=logging.DEBUG)


class FlowScheduler:
    def __init__(self):
        self.flows = {}  # Dictionary to store added flows and their scheduling details

    # Add a flow to the scheduler
    def add_flow(self, flow):
        #########################
        # validate the flow

        # Check if the flow is a dictionary
        if not isinstance(flow, dict):
            raise ValueError(
                "Flow must be a dictionary with 'path' and scheduling details."
            )

        flow_path = flow.get("path")
        cron = flow.get("cron")
        every_seconds = flow.get("every_seconds")
        timeout_seconds = flow.get("timeout_seconds", FLOW_TIMEOUT_SECONDS)

        # assert flow_path is not None, "Flow path must be provided."
        if not flow_path or not isinstance(flow_path, str):
            raise ValueError("Flow path must be provided.")

        # assert cron is not None or every_seconds is not None, "Flow must have either 'cron' or 'every_seconds' defined."
        if not cron and not every_seconds:
            raise ValueError("Flow must have either 'cron' or 'every_seconds' defined.")

        # assert every_seconds is integer, "every_seconds must be an integer."
        if every_seconds and not isinstance(every_seconds, int):
            raise ValueError("every_seconds must be an integer.")

        # Load the flow YAML
        logging.info("Loading flow configuration from %s", flow_path)

        # Check if the flow file exists and parses well
        Flow.validate_path(flow_path)

        # Check if the flow is not already added
        if any(f["path"] == flow_path for f in self.flows.values()):
            raise FlowAlreadyAddedException(
                f"Flow {flow_path} is already added to the scheduler."
            )

        ######################################
        # flow is valid, let's add it to the scheduler

        # generate a unique ID for the flow
        schedule_id = str(uuid.uuid4())

        # add the flow to the scheduler
        self.flows[schedule_id] = {
            "path": flow_path,
            "cron": cron,
            "every_seconds": every_seconds,
            "timeout_seconds": timeout_seconds,
        }

        if cron:
            # Schedule the flow based on the cron property
            self.schedule_cron(cron, flow_path, schedule_id, timeout_seconds)
        elif every_seconds:
            # Schedule the flow based on the every_seconds property
            self.schedule_every_seconds(
                every_seconds, flow_path, schedule_id, timeout_seconds
            )
        else:
            raise NoScheduleException(
                f"Flow {flow_path} was added without valid schedule (cron or every_seconds)."
            )

        logging.info("Added flow %s with ID: %s", flow_path, schedule_id)
        return schedule_id

    def remove_flow(self, schedule_id):
        if schedule_id in self.flows:
            # Cancel interval job if present
            job = self.flows[schedule_id].get("job")
            if job:
                schedule.cancel_job(job)
            # Stop cron thread if present
            stop_event = self.flows[schedule_id].get("cron_stop_event")
            thread = self.flows[schedule_id].get("cron_thread")
            if stop_event:
                stop_event.set()
            if thread:
                thread.join(timeout=5)  # Wait up to 5 seconds for the thread to finish
            del self.flows[schedule_id]
            return f"Removed flow with ID: {schedule_id}"
        else:
            raise FlowNotFoundException(f"Flow with ID {schedule_id} not found.")

    def list_flows(self):
        """List all added flows."""

        flows_list = []
        for schedule_id, flow in self.flows.items():
            flow_info = {
                "id": schedule_id,
                "path": flow.get("path"),
                "cron": flow.get("cron"),
                "every_seconds": flow.get("every_seconds"),
                "timeout_seconds": flow.get("timeout_seconds"),
                "last_job_id": flow.get("last_job_id"),
                "running": bool(flow.get("running", False)),
            }
            flows_list.append(flow_info)
        return flows_list

    def schedule_every_seconds(
        self, every_seconds, flow_path, schedule_id, timeout_seconds
    ):
        """Schedule a flow to run every X seconds."""

        def job_wrapper():
            try:
                # You can set a default timeout here if you want
                self.run_scheduled_flow(
                    flow_path,
                    timeout=timeout_seconds,
                    schedule_id=schedule_id,
                    every_seconds=every_seconds,
                )
            except FlowAlreadyRunningException as e:
                logging.warning(e)
            except Exception as e:
                logging.error("Error running flow %s: %s", flow_path, e)

        job = schedule.every(every_seconds).seconds.do(job_wrapper)
        self.flows[schedule_id]["job"] = job
        logging.info(
            "Scheduled flow %s to run every %d seconds", flow_path, every_seconds
        )

    def schedule_cron(self, cron_expression, flow_path, schedule_id, timeout_seconds):
        """Schedule a flow using a cron expression."""
        stop_event = threading.Event()

        def job_wrapper():
            try:
                self.run_scheduled_flow(
                    flow_path,
                    timeout=timeout_seconds,
                    schedule_id=schedule_id,
                    cron=cron_expression,
                )
            except FlowAlreadyRunningException as e:
                logging.warning(e)
            except Exception as e:
                logging.error("Error running flow %s: %s", flow_path, e)

        def cron_job():
            while not stop_event.is_set():
                now = datetime.now(TZ)
                cron = croniter(cron_expression, now)
                next_run = cron.get_next(datetime)
                delay = (next_run - now).total_seconds()
                if stop_event.wait(timeout=delay):
                    break
                job_wrapper()

        thread = Thread(target=cron_job, daemon=True)
        thread.start()
        self.flows[schedule_id]["cron_thread"] = thread
        self.flows[schedule_id]["cron_stop_event"] = stop_event
        logging.info("Scheduled flow %s with cron: %s", flow_path, cron_expression)

    def run_scheduled_flow(
        self, flow_path, schedule_id, cron=None, every_seconds=None, timeout=None
    ):
        self.flows[schedule_id]["running"] = True

        try:
            meta = {
                "flow_path": flow_path,
                "timeout": timeout,
                "schedule_id": schedule_id,
                "cron": cron,
                "every_seconds": every_seconds,
                "source": "scheduler",
            }

            # Use FlowRunner for job tracking and async execution
            try:
                job_id = FlowRunner.launch_async(flow_path, timeout=timeout, meta=meta)
            except FlowAlreadyRunningException as e:
                raise e
            except Exception as e:
                raise e

            # Store the last job_id for this scheduled flow
            self.flows[schedule_id]["last_job_id"] = job_id
        except Exception as e:
            logging.error("Error scheduling flow %s: %s", flow_path, e)
        finally:
            if schedule_id and "running" in self.flows[schedule_id]:
                del self.flows[schedule_id]["running"]

    def start(self):
        def run_scheduler():
            while True:
                try:
                    schedule.run_pending()
                except Exception as e:
                    logging.error("Exception in scheduler loop: %s", e)
                time.sleep(1)

        Thread(target=run_scheduler, daemon=True).start()
