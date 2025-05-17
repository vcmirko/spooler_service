from .secrets.credential_secret import CredentialSecret
from .secrets.token_secret import TokenSecret
from .secrets.hashicorp_vault_secret import HashicorpVaultSecret
from .secrets.api_key_secret import ApiKeySecret
import logging

class SecretFactory:
    @staticmethod
    def load(secret_def):
        secret = {}
        secret_type = secret_def.get("type", "credential")
        if secret_type == "credential":
            secret = CredentialSecret(secret_def).load()
        elif secret_type == "token":
            secret = TokenSecret(secret_def).load()
        elif secret_type == "api-key":
            secret = ApiKeySecret(secret_def).load()
        elif secret_type == "hashicorp-vault":
            secret = HashicorpVaultSecret(secret_def).load()
        else:
            raise Exception(f"Unknown secret type: {secret_type}")
        return secret