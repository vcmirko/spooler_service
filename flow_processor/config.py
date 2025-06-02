import os
from pathlib import Path

import pytz

# --- Base Paths ---
BASE_PATH = Path(__file__).resolve().parent.parent  # Project root
DATA_PATH = Path(os.getenv("DATA_PATH", BASE_PATH / "data"))
DATA_PATH.mkdir(exist_ok=True)

# --- Directory Paths ---
LOG_PATH = Path(os.getenv("LOG_PATH", DATA_PATH / "logs"))
LOG_PATH.mkdir(exist_ok=True)
FLOWS_PATH = Path(os.getenv("FLOWS_PATH", DATA_PATH / "flows"))
FLOWS_PATH.mkdir(exist_ok=True)
TEMPLATES_PATH = Path(os.getenv("TEMPLATES_PATH", DATA_PATH / "templates"))
TEMPLATES_PATH.mkdir(exist_ok=True)

# --- File Paths ---
SECRETS_PATH = Path(os.getenv("SECRETS_PATH", DATA_PATH / "secrets.yml"))
JOBS_DB_PATH = Path(os.getenv("JOBS_DB_PATH", DATA_PATH / "jobs.sqlite"))
CONFIG_FILE = Path(os.getenv("CONFIG_FILE", DATA_PATH / "config.yml"))

# --- Logging ---
LOG_FILE_NAME = os.getenv("LOG_FILE_NAME", "spooler_service.log")
LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

# --- Database ---
DATABASE_URL = f"sqlite:///{JOBS_DB_PATH}"

# --- Timezone ---
TIMEZONE = os.getenv("TIMEZONE", "Europe/Brussels")
TZ = pytz.timezone(TIMEZONE)

# --- API ---
API_PORT = int(os.getenv("API_PORT", 5000))
API_TOKEN = os.getenv("API_TOKEN", "default_token")

# --- Swagger ---
SWAGGER_URL = "/api/docs"
SWAGGER_JSON_PATH = os.path.join(BASE_PATH, "static/swagger.json")

# --- Vault ---
HASHICORP_VAULT_TOKEN = os.getenv("HASHICORP_VAULT_TOKEN", None)
HASHICORP_VAULT_CACHE_TTL = int(
    os.getenv("HASHICORP_VAULT_CACHE_TTL", 60)
)  # Default: 1 minute

# --- Flow ---
FLOW_TIMEOUT_SECONDS = int(os.getenv("FLOW_TIMEOUT", 600))  # Default: 10 minutes
