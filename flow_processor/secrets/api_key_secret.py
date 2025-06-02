from flow_processor.exceptions import BadSecretException

from ..secret import Secret


class ApiKeySecret(Secret):
    def __init__(self, secret_def):
        super().__init__(secret_def)
        self._key = secret_def.get("key")
        self._value = secret_def.get("value")

    def load(self):
        if not self._key or not self._value:
            raise BadSecretException(
                f"API key secret '{self._name}' missing 'key' or 'value'"
            )
        return {"key": self._key, "value": self._value}
