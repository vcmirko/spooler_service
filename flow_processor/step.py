from flow_processor.utils import apply_jinja2
from flow_processor.secret_factory import SecretFactory
from flow_processor.exceptions import SecretNotFoundException
import logging

class Step():
    """Base class for all steps in the flow."""
    def __init__(self, step, flow):
        self._name = step.get("name")
        self._type = step.get("type")
        self._flow = flow
        self._data = {}
        self._result_key = step.get("result_key", self._name)
        self._step = step  # Store the original step dictionary for internal use
        self._jq_expression = step.get("jq_expression", None)
        self._when = step.get("when", [])  # List of Jinja2 expressions
        self._representation = f"{self._flow._representation}[{self._name} // {self._type}]"

    def __repr__(self):
        return f"{self._representation}"

    def _patch(self):
        """Patch the data with the given key."""
        self._flow._data[self._result_key] = self._data

    def _evaluate_when(self):
        """Evaluate the 'when' conditions."""
        if not self._when:  # If no 'when' property, always execute
            return True

        for condition in self._when:
            logging.debug("Evaluating condition: {{ %s }}", condition)
            result = apply_jinja2(f"{{{{ {condition} }}}}", self._flow._data)
            logging.debug("Condition result: %s", result)
            if not result.lower() in ["true", "1", "yes"]:  # Treat only "true", "1", or "yes" as True
                return False
        return True
    
    def pre_process(self, ignore_when=False):
        """Pre-process the step."""
        # Check 'when' conditions
        if(ignore_when):
            return True
        return self._evaluate_when()

    def process(self):
        """Process the step."""
        from flow_processor.utils import apply_jq_filter



        # THIS IS RAN AFTER THE SUBCLASS PROCESS METHOD
        # Here we just patch the data with the result key

        # An optional jq filter in the step itself, because it's often enough to filter the data
        if self._jq_expression:
            self._data = apply_jq_filter(self._data, self._jq_expression)

        self._patch()
        # Return the result if needed
        return self._data

    def _get_secret(self, name):
        secret_def = next((s for s in self._flow._secrets if s["name"] == name), None)
        if not secret_def:
            raise SecretNotFoundException(f"Secret {name} not found")
        secret = SecretFactory.load(secret_def)
        return secret

    def _get_data_by_key(self, key=None):
        """Retrieve data by key."""
        if not key:
            return None
        if key == ".":
            return self._flow._data
        if not key in self._flow._data:
            raise Exception(f"Data {key} not found")
        return self._flow._data.get(key)
