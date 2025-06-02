from flow_processor.exceptions import BadSecretException

from ..secret import Secret


class TokenSecret(Secret):
    def __init__(self, secret_def):
        super().__init__(secret_def)
        self._token = secret_def.get("token")

    def load(self):
        if not self._token:
            raise BadSecretException(f"Token secret '{self._name}' missing token")
        return {"token": self._token}
