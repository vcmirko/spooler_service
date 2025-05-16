import os
from pathlib import Path

######################################################################
# Configuration for the Flow Processor
# This module contains the configuration settings for the Flow Processor.
# ENVIRONMENT VARIABLES:
# - DATA_PATH: Path to the data directory.
# - LOCK_PATH: Path to the directory for lock files.
# - LOG_PATH: Path to the directory for log files.
# - LOG_FILE_NAME: Name of the log file.
# - LOG_LEVEL: Logging level (default is INFO).
# - FLOWS_PATH: Path to the directory for flow files.
# - TEMPLATES_PATH: Path to the directory for template files.
# - SECRETS_PATH: Path to the secrets file.
# - CONFIG_FILE: Path to the configuration file.

# - API_HOST: Hostname for the API server (swagger mainly)
# - API_PORT: Port for the API server.
# - API_PROTOCOL: Protocols for the API server (comma-separated).
# - API_TOKEN: Token for API authentication.


# Base directory
BASE_PATH = Path(__file__).resolve().parent.parent  # Path to the project root
DATA_PATH = Path(os.getenv("DATA_PATH", BASE_PATH / "data"))  # Path to the data directory
DATA_PATH.mkdir(exist_ok=True)

# Paths with environment variable override and fallback to DATA_PATH
LOCK_PATH = Path(os.getenv("LOCK_PATH", DATA_PATH / "locks"))
LOCK_PATH.mkdir(exist_ok=True)
LOG_PATH = Path(os.getenv("LOG_PATH", DATA_PATH / "logs"))
LOG_PATH.mkdir(exist_ok=True)
LOG_FILE_NAME = os.getenv("LOG_FILE_NAME", "spooler_service.log")
FLOWS_PATH = Path(os.getenv("FLOWS_PATH", DATA_PATH / "flows"))
FLOWS_PATH.mkdir(exist_ok=True)
TEMPLATES_PATH = Path(os.getenv("TEMPLATES_PATH", DATA_PATH / "templates"))
TEMPLATES_PATH.mkdir(exist_ok=True)
SECRETS_PATH = Path(os.getenv("SECRETS_PATH", DATA_PATH / "secrets.yml"))

LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

# Environment variables for API
API_PORT = int(os.getenv("API_PORT", 5000))
API_TOKEN = os.getenv("API_TOKEN", "default_token")

# Swagger configuration // fixed, but could be moved to environment variables
SWAGGER_URL = "/api/docs"
SWAGGER_JSON_PATH = os.path.join(BASE_PATH, "static/swagger.json")

# Configuration file for the flow processor
CONFIG_FILE = Path(os.getenv("CONFIG_FILE", DATA_PATH / "config.yml"))