import logging
import yaml
import re
from .step_factory import create_step
from flow_processor.utils import make_timestamp
from flow_processor.config import FLOWS_PATH, SECRETS_PATH
from flow_processor.exceptions import FlowParsingException,FlowNotFoundException,FlowExitException
import os

class Flow:
    """
    Flow class for processing workflows defined in YAML files.
    """

    @staticmethod
    def validatePath(flow_path):
        """
        Validate the flow path to prevent directory traversal and ensure it is a YAML file.
        """
        try:
            with open(os.path.join(FLOWS_PATH,flow_path), "r") as file:
                flow_config = yaml.safe_load(file)
        except FileNotFoundError:
            raise FlowNotFoundException(f"Flow file {flow_path} not found.")
        except yaml.YAMLError as e:
            raise FlowParsingException(f"Failed to parse flow file {flow_path}: {e}")
        except Exception as e:
            raise e

    def __init__(self, path, payload={}, loop_index=None):
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
        self._finally_step = flow.get("finally_step", None)
        self._data = {}
        self._data["__errors__"] = []             # a list of errors that occurred during the flow
        self._data["__input__"] = payload         # a flow can have an input payload, from a parent, or from the api
        self._secrets = self._load_secrets()      # each flow loads the secrets and temporarily stores them in the flow
        self._data["__loop_index__"] = loop_index        # a flow can have an index, for example, when looping over a list
        self._data["__timestamp__"] = make_timestamp() # a flow can have a timestamp, for example, when looping over a list
        self._representation = f"[{self._name}]"
        if loop_index:
            self._representation += f"[{loop_index}]"


    def __repr__(self):
        repr =  f"[{self._name}][{self._data.get('__loop_index__')}]"
        return repr

   
    def process(self):
        """Process the flow."""

        try:

            # loop over the steps, create the step object, since the step can a subclass of step, we need to use the factory
            # create the step object, and call the process method

            for step in self._steps:

                try:
                    # call the step factory to create the step object
                    create_step(step, self).process()

                # we want to catch all errors in the step, and continue the flow if required
                except Exception as e:
                    error_obj = {
                        "step": step["name"],
                        "error": dict(e.__dict__)
                    }
                    error_one_line = str(dict(e.__dict__)).replace("\n", " ").replace("\r", " ")
                    continue_step = False
                    logging.error(f"{self._representation} Error in step {step['name']}: {str(e)}")
                    # check if the step has ignore_errors, if so, we will ignore the error if the regex matches
                    for err_regex in step.get("ignore_errors", []):
                        if re.match(err_regex, error_one_line):
                            logging.warning(f"{self._representation} Ignoring error in step {step['name']}: {str(e)}")
                            error_obj["ignored"] = f"Error ignored based on regex: {err_regex}"
                            continue_step = True
                            break
                    # store the error in the flow data
                    self._data["__errors__"].append(error_obj)
                    if continue_step:
                        continue
                    else:
                        raise e
        except FlowExitException as e:
            return self._data, {"exit": True, "exit_message": str(e)}
        except Exception as e:
            # we silent the error here, the flow failed, the error will be logged
            logging.error(f"{self._representation} Error in flow: {str(e)}")

            try:
                finally_step = next((s for s in self._steps if s["name"] == self._finally_step), None)
                # call the step factory to create the finally step object on failure
                if finally_step:
                    logging.info(f"{self._representation} Calling finally step {self._finally_step}")
                    create_step(finally_step, self).process(True) # run with ignore_when=True, finally always runs

            except Exception as e:
                logging.error(f"{self._representation} Error in finally step {self._finally_step}: {str(e)}")

        finally:
            logging.debug(f"{self._representation} Flow {self._name} finished.")

        return self._data
    
    
    def _load_secrets(self):
        """Load secrets from a YAML file."""
        with open(SECRETS_PATH, "r") as file:
            return yaml.safe_load(file)

