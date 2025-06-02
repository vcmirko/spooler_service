import logging

from .secrets.api_key_secret import ApiKeySecret
from .secrets.credential_secret import CredentialSecret
from .secrets.hashicorp_vault_secret import HashicorpVaultSecret
from .secrets.token_secret import TokenSecret


class SecretFactory:
    @staticmethod
    def load(secret_def):
        secret_type = secret_def.get("type", "credential")
        match secret_type:
            case "credential":
                secret = CredentialSecret(secret_def).load()
            case "token":
                secret = TokenSecret(secret_def).load()
            case "api-key":
                secret = ApiKeySecret(secret_def).load()
            case "hashicorp-vault":
                secret = HashicorpVaultSecret(secret_def).load()
            case _:
                raise Exception(f"Unknown secret type: {secret_type}")
        return secret
