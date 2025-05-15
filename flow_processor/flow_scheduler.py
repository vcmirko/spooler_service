import schedule
import logging
import time
import os
import yaml
import uuid
from croniter import croniter
from datetime import datetime
from threading import Thread
from flow_processor.config import FLOWS_PATH
from flow_processor.locks import create_lock, release_lock, is_locked
from flow_processor.flow import Flow
from flow_processor.exceptions import NoScheduleException,FlowAlreadyAddedException

class FlowScheduler:
    def __init__(self):
        self.flows = {}  # Dictionary to store added flows and their scheduling details

    def add_flow(self, flow_path):
        # Load the flow YAML
        logging.info(f"Adding flow: {flow_path}")
        try:
            with open(os.path.join(FLOWS_PATH,flow_path), "r") as file:
                flow_config = yaml.safe_load(file)
        except Exception as e:
            logging.error(f"Failed to load flow configuration: {e}")
            return None
        
        # Check if the flow is not already added
        if any(flow["path"] == flow_path for flow in self.flows.values()):
            raise FlowAlreadyAddedException(f"Flow {flow_path} is already added to the scheduler.")

        cron = flow_config.get("cron", None)
        every_seconds = flow_config.get("every_seconds", None)
        if cron:
            # Schedule the flow based on the cron property
            self.schedule_cron(cron, flow_path)
            logging.info(f"Scheduled flow {flow_path} with cron: {cron}")
        elif every_seconds:
            # Schedule the flow based on the every_seconds property
            schedule.every(every_seconds).seconds.do(self.run_flow, flow_path)
            logging.info(f"Scheduled flow {flow_path} to run every {every_seconds} seconds")
        else:
            raise NoScheduleException(f"Flow {flow_path} does not have a valid schedule (cron or every_seconds).")

        # Generate a unique ID for the flow
        flow_id = str(uuid.uuid4())
        self.flows[flow_id] = {"path": flow_path, "cron": cron, "every_seconds": every_seconds}
        logging.info(f"Flow added with ID: {flow_id}")
        return flow_id

    def remove_flow(self, flow_id):
        """Remove a flow from the scheduler by ID."""
        if flow_id in self.flows:
            del self.flows[flow_id]
            logging.info(f"Removed flow with ID: {flow_id}")
            return True
        else:
            logging.warning(f"Flow with ID {flow_id} not found.")
            return False

    def list_flows(self):
        """List all added flows."""
        return self.flows

    def schedule_cron(self, cron_expression, flow_path):
        """Schedule a flow using a cron expression."""
        def job():
            self.run_flow(flow_path)

        # Use croniter to calculate the next run time
        def cron_job():
            while True:
                now = datetime.now()
                cron = croniter(cron_expression, now)
                next_run = cron.get_next(datetime)
                logging.info(f"Next run for {flow_path} is at {next_run}")
                delay = (next_run - now).total_seconds()
                logging.info(f"Scheduling job for {flow_path} in {delay} seconds")
                time.sleep(delay)
                job()

        # Start a thread for the cron job
        Thread(target=cron_job, daemon=True).start()

    def run_flow(self, flow_path):
        flow_name = os.path.basename(flow_path)
        if is_locked(flow_name):
            logging.warning(f"Flow {flow_name} is already running. Skipping.")
            return

        # get flow id
        flow_id = None
        for id, flow in self.flows.items():
            if flow["path"] == flow_path:
                flow_id = id
                break

        # Mark the flow as running
        if flow_id:
            self.flows[flow_id]["running"] = True



        try:
            create_lock(flow_name)
            Flow(path=flow_path).process()
        finally:
            release_lock(flow_name)
            # Remove the flow from the running set
            if flow_id and "running" in self.flows[flow_id]:
                del self.flows[flow_id]["running"]

    def start(self):
        def run_scheduler():
            while True:
                schedule.run_pending()
                time.sleep(1)

        Thread(target=run_scheduler, daemon=True).start()