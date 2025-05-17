from ..secret import Secret
from flow_processor.exceptions import BadSecretException

class CredentialSecret(Secret):
    def __init__(self, secret_def):
        super().__init__(secret_def)
        self._username = secret_def.get("username")
        self._password = secret_def.get("password")

    def load(self):
        if not self._username or not self._password:    
            raise BadSecretException(f"Credential secret '{self.name}' missing username or password")
        return {
            "username": self._username,
            "password": self._password
        }