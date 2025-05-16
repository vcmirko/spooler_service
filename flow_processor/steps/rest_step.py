import base64
import logging
import requests
from ..step import Step
from flow_processor.utils import apply_jinja2

import urllib3

class RestStepException(Exception):
    """Custom exception for REST step errors."""
    def __init__(self, message, status_code=None, response_content=None):
        super().__init__(message)
        self.status_code = status_code
        self.response_content = response_content
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    
class RestStep(Step):
    """Subclass for REST operations."""
    def __init__(self, step, flow):
        super().__init__(step, flow)

        # make sure the step is a REST step
        assert "rest" in step, "REST configuration is required"
        self._rest = step.get("rest")

        # make sure the step has an uri, this is minimum
        assert "uri" in self._rest, "URI is required"
        self._uri = apply_jinja2(self._rest.get("uri"), self._flow._data)
        self._method = self._rest.get("method", "GET").upper()
        self._headers = self._rest.get("headers", {})
        self._query = self._rest.get("query", {})
        self._data_key = self._rest.get("data_key", None)
        self._authentication = self._rest.get("authentication", None)

        # process the query parameters, add ? and & and uri encode the values, use python urllib.parse
        if self._query:
            from urllib.parse import urlencode
            self._uri += "?" + urlencode(self._query)

        # process body
        self._body = {}
        if self._data_key:
            self._body = self._flow._data.get(self._data_key, {})
        elif self._rest.get("body", False):
            self._body = self._rest.get("body")
        
        if self._authentication:
            self._headers.update(self._get_auth_headers())

    def __repr__(self):
        return f"RestStep(name={self._name}, uri={self._uri}, method={self._method}, headers={self._headers}, data_key={self._data_key})"

    def process(self, ignore_when=False):
        """Process the REST step."""

        # pre-process the step, check if the step is enabled
        enabled = super().pre_process(ignore_when)
        if not enabled:
            return

        logging.info("%s -> %s %s", self._representation, self._method, self._uri)

        # Make the REST request
        response = self._make_rest_request()
        if 200 <= response.status_code < 300:
            pass
        else:
            # if the response contained data, log it
            if response.content:
                logging.error("%s REST request failed with status code %s: %r", self._representation, response.status_code, response.content)
                try:
                    response_content = response.json()
                except ValueError:
                    response_content = response.content  # Fallback to raw content if not JSON
                raise RestStepException(
                    message="REST request failed",
                    status_code=response.status_code,
                    response_content=response_content
                )
            else:
                logging.error("%s REST request failed with status code %s", self._representation, response.status_code)
                raise RestStepException(
                    message="REST request failed",
                    status_code=response.status_code
                )
            
        self._data = response.json()
        return super().process()

    def _get_auth_headers(self):
        """Generate authentication headers."""
        auth_type = self._authentication.get("type")
        secret_name = self._authentication.get("secret")
        secret = super()._get_secret(secret_name)

        match auth_type:
            case "token":
                token = secret.get("token")
                if not token:
                    raise Exception(f"Token not found in secret {secret_name}")
                bearer = self._authentication.get("bearer", "Bearer")
                return {"Authorization": f"{bearer} {token}"}
            case "basic":
                username = secret.get("username")
                password = secret.get("password")
                if not username or not password:
                    raise Exception(f"Username or password missing in secret {secret_name}")
                basic_auth = base64.b64encode(f"{username}:{password}".encode()).decode()
                return {"Authorization": f"Basic {basic_auth}"}
            case _:
                raise Exception(f"Unsupported authentication type: {auth_type}")

    def _make_rest_request(self):
        """Make a REST request."""
        match self._method:
            case "GET":
                return requests.get(self._uri, headers=self._headers, verify=False)
            case "POST":
                return requests.post(self._uri, headers=self._headers, json=self._body, verify=False)
            case "PUT":
                return requests.put(self._uri, headers=self._headers, json=self._body, verify=False)
            case "DELETE":
                return requests.delete(self._uri, headers=self._headers, verify=False)
            case "PATCH":
                return requests.patch(self._uri, headers=self._headers, json=self._body, verify=False)
            case _:
                raise Exception(f"Unsupported HTTP method: {self._method}")        
