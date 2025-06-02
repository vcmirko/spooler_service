import logging

from .secrets.api_key_secret import ApiKeySecret
from .secrets.credential_secret import CredentialSecret
from .secrets.hashicorp_vault_secret import HashicorpVaultSecret
from .secrets.token_secret import TokenSecret


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
