from ..secret import Secret
from flow_processor.exceptions import BadSecretException
from flow_processor.config import HASHICORP_VAULT_TOKEN, HASHICORP_VAULT_CACHE_TTL
import requests
import time

class HashicorpVaultSecret(Secret):
    _cache = {}
    _cache_expiry = {}

    def __init__(self, secret_def):
        super().__init__(secret_def)
        self._uri = secret_def.get("uri")
        self._jq_expression = secret_def.get("jq_expression", None)

    def load(self):
        cache_key = f"{self._uri}|{self._jq_expression}"
        now = time.time()
        # Check cache
        if (
            cache_key in self._cache
            and cache_key in self._cache_expiry
            and now < self._cache_expiry[cache_key]
        ):
            return self._cache[cache_key]

        if not self._uri:
            raise BadSecretException(f"Hashicorp Vault secret '{self._name}' missing uri")
        
        token = HASHICORP_VAULT_TOKEN
        if not token:
            raise BadSecretException(f"Hashicorp Vault secret '{self._name}' missing token, please set HASHICORP_VAULT_TOKEN in the environment")

        headers = {"X-Vault-Token": token}
        response = requests.get(self._uri, headers=headers, verify=False)
        if not response.ok:
            raise BadSecretException(f"Failed to fetch secret '{self._name}' from Hashicorp Vault: {response.text}")
        data = response.json()
        data = data.get("data", None)
        assert data is not None, f"Hashicorp Vault secret '{self._name}' has no data"
        data = data.get("data")
        assert data is not None, f"Hashicorp Vault secret '{self._name}' data has no data key"

        if self._jq_expression:
            from flow_processor.utils import apply_jq_filter
            data = apply_jq_filter(data, self._jq_expression)

        # Cache result 
        self._cache[cache_key] = data
        self._cache_expiry[cache_key] = now + HASHICORP_VAULT_CACHE_TTL

        return data