import logging
import os
import re

import yaml

from flow_processor.config import FLOWS_PATH, SECRETS_PATH
from flow_processor.exceptions import (
    FlowExitException,
    FlowNotFoundException,
    FlowParsingException,
)
from flow_processor.utils import make_timestamp

from .step_factory import create_step


class Flow:
    """
    Flow class for processing workflows defined in YAML files.
    """

    @staticmethod
    def validate_path(flow_path):
        """
        Validate the flow path to prevent directory traversal and ensure it is a YAML file.
        """
        try:
            with open(os.path.join(FLOWS_PATH, flow_path), "r") as file:
                flow_config = yaml.safe_load(file)
        except FileNotFoundError:
            raise FlowNotFoundException(f"Flow file {flow_path} not found.")
        except yaml.YAMLError as e:
            raise FlowParsingException(f"Failed to parse flow file {flow_path}: {e}")
        except Exception as e:
            raise e

    def __init__(self, path, payload={}, loop_index=None, job_id=None):
        flow = {}

        try:
            with open(os.path.join(FLOWS_PATH, path), "r") as file:
                flow = yaml.safe_load(file)
        except FileNotFoundError:
            raise FlowNotFoundException(f"Flow file not found: {path}")
        except yaml.YAMLError as e:
            raise FlowParsingException(f"Failed to parse flow file: {path}: {e}")
        except Exception as e:
            raise e

        self._name = flow.get("name")
        self._path = path
        self._steps = flow.get("steps", [])
        self._data = {}
        self._data["__errors__"] = []  # a list of errors that occurred during the flow
        self._data["__input__"] = (
            payload  # a flow can have an input payload, from a parent, or from the api
        )
        self._secrets = (
            self._load_secrets()
        )  # each flow loads the secrets and temporarily stores them in the flow
        self._data["__loop_index__"] = (
            loop_index  # a flow can have an index, for example, when looping over a list
        )
        self._data["__job_id__"] = (
            job_id  # the main job id, if the flow is run as a job
        )
        self._data["__timestamp__"] = (
            make_timestamp()
        )  # a flow can have a timestamp, for example, when looping over a list
        self._data["__flow_path__"] = (
            path  # the path of the flow, for reference, in case it's required later in a step
        )
        self._representation = f"[{self._name}]"
        if loop_index:
            self._representation += f"[{loop_index}]"

        self._step_dict = {step["name"]: idx for idx, step in enumerate(self._steps)}

    def __repr__(self):
        repr = f"[{self._name}][{self._data.get('__loop_index__')}]"
        return repr

    def process(self,stop_event=None):
        """Process the flow."""

        failed = False
        failed_message = None
        result = None

        try:
            #####################################
            # START THE FLOW PROCESSING
            #####################################

            # initial step
            current_idx = 0

            # as long as we have steps to process
            while current_idx < len(self._steps) and (not stop_event or not stop_event.is_set()):

                # get the current step
                step = self._steps[current_idx]
                step_obj = create_step(step, self)

                try:

                    # process the step
                    result = step_obj.process()


                except FlowExitException as e:
                    # an explicit exit from the flow, we will return the data and the exit message
                    return self._data, {"type": "exit", "message": str(e)}

                # we want to catch all errors in the step, and continue the flow if required
                except Exception as e:
                    # Get a good representation of the error
                    if hasattr(e, "__dict__") and e.__dict__:
                        error_detail = dict(e.__dict__)
                    else:
                        error_detail = str(e)
                    error_obj = {"step": step["name"], "error": error_detail}
                    error_one_line = (
                        str(dict(e.__dict__)).replace("\n", " ").replace("\r", " ")
                    )
                    continue_step = False
                    logging.error(
                        "%s Error in step %s: %s",
                        self._representation,
                        step["name"],
                        str(e),
                    )
                    # check if the step has ignore_errors, if so, we will ignore the error if the regex matches
                    for err_regex in step.get("ignore_errors", []):
                        if re.match(err_regex, error_one_line):
                            logging.warning(
                                "%s Ignoring error in step %s: %s",
                                self._representation,
                                step["name"],
                                str(e),
                            )
                            error_obj["ignored"] = (
                                f"Error ignored based on regex: {err_regex}"
                            )
                            continue_step = True
                            break
                    # store the error in the flow data
                    self._data["__errors__"].append(error_obj)

                    # error occurred, end of the line, we break the loop
                    if not continue_step:

                        # Check if the step defines a 'on_error_goto' property
                        on_error_goto = step.get("on_error_goto")
                        if on_error_goto:
                            logging.info(
                                "%s on_error_goto triggered in step %s: going to %s",
                                self._representation,
                                step["name"],
                                on_error_goto,
                            )
                            result = {"goto": on_error_goto}
                        else:
                            # error, no ignore, no goto, end of the flow with error
                            raise e

                # Check for the next step based on the result of the current step
                if isinstance(result, dict) and "goto" in result:
                    goto_name = result["goto"]
                    match goto_name:
                        case "__exit":
                            logging.info("%s Exiting flow %s", self._representation, self._name)
                            # we return the data and the exit message
                            return self._data, {"type": "exit", "message": "Flow exited."}
                        case "__end__":
                            # special case to end the flow, we exit the loop
                            logging.info("%s Ending flow %s", self._representation, self._name)
                            current_idx = len(self._steps)
                        case "__start__":
                            # special case to end the flow, we exit the loop
                            logging.info("%s Goto start of flow %s", self._representation, self._name)
                            # goto_name = self._steps[0].name 
                            current_idx = 0  
                        case _: 
                            if goto_name not in self._step_dict:
                                # bad goto step, we raise an exception
                                raise Exception(f"Goto step '{goto_name}' not found in flow.")
                            
                            logging.info("%s Goto step %s", self._representation, goto_name)
                            current_idx = self._step_dict[goto_name]
                else:
                    # no goto, just take the next step
                    logging.debug("%s next step of flow %s", self._representation, self._name)
                    current_idx += 1

            # in case the flow was stopped but no error ever occurred.
            if stop_event and stop_event.is_set():
                logging.info("%s Flow %s stopping on request.", self._representation, self._name)
                return self._data, {"type": "failed", "message": "Flow stopped on request."}

        except Exception as e:
            # we silence the error here, the flow failed, the error will be logged
            logging.error("%s Error in flow: %s", self._representation, str(e))
            failed = True
        except BaseException as be:
            # we catch BaseException to ensure we log it and can handle it gracefully
            logging.error("%s BaseException in flow: %s", self._representation, str(be))
            failed = True

        finally:
            logging.debug("%s Flow %s finished.", self._representation, self._name)

        if failed:
            return self._data, {"type": "failed", "message": failed_message}
        else:
            return self._data, {
                "type": "success",
                "message": "Flow completed successfully.",
            }

    def _load_secrets(self):
        """Load secrets from a YAML file."""
        with open(SECRETS_PATH, "r") as file:
            return yaml.safe_load(file)
