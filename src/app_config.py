# app_config.py
import os
from dotenv import load_dotenv
from pathlib import Path

# ===========================
# LOAD .ENV
# ===========================
env_path = Path(__file__).resolve().parent.parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)

# ===========================
# RUN MODE
# ===========================
SANDBOX_MODE = os.getenv("SANDBOX_MODE", "true").lower() == "true"

# ===========================
# BIDV API SETTINGS (base urls vary by sandbox/prod)
# ===========================
BIDV_API_VERSION = os.getenv("BIDV_API_VERSION", "v1")

if SANDBOX_MODE:
    # sandbox endpoints (example from your web snippet)
    BIDV_BASE_URL = os.getenv("BIDV_BASE_URL", "https://openapi.bidv.com.vn/bidv/sandbox/open-banking")
    BIDV_OAUTH_TOKEN_URL = os.getenv(
        "BIDV_OAUTH_TOKEN_URL", "https://openapi.bidv.com.vn/bidv/sandbox/ibank-sandbox-oauth/oauth2/token"
    )
    BIDV_OAUTH_AUTHORIZE_URL = os.getenv(
        "BIDV_OAUTH_AUTHORIZE_URL",
        "https://openapi.bidv.com.vn/bidv/sandbox/ibank-sandbox-oauth/oauth2/authorize",
    )
else:
    BIDV_BASE_URL = os.getenv("BIDV_BASE_URL", "https://openapi.bidv.com.vn/bidv/open-banking")
    BIDV_OAUTH_TOKEN_URL = os.getenv(
        "BIDV_OAUTH_TOKEN_URL", "https://openapi.bidv.com.vn/bidv/ibank-oauth/oauth2/token"
    )
    BIDV_OAUTH_AUTHORIZE_URL = os.getenv(
        "BIDV_OAUTH_AUTHORIZE_URL", "https://openapi.bidv.com.vn/bidv/ibank-oauth/oauth2/authorize"
    )

# API relative paths
BIDV_API_INQUIRE_PATH = os.getenv("BIDV_API_INQUIRE_PATH", "/inquire-account-transaction/v1")
BIDV_API_BALANCE_PATH = os.getenv(
    "BIDV_API_BALANCE_PATH", "/inquire-account-v2/v1"
)  # adjust if BIDV uses a different path

CHANNEL_ID = os.getenv("CHANNEL_ID", "ProdChannel")
OAUTH_GRANT_TYPE = os.getenv("OAUTH_GRANT_TYPE", "authorization_code")

# ===========================
# BIDV API CREDENTIALS
# ===========================
BIDV_CLIENT_ID = os.getenv("BIDV_CLIENT_ID")
BIDV_CLIENT_SECRET = os.getenv("BIDV_CLIENT_SECRET")
# optional: raw API key/secret (some examples use these)
BIDV_API_KEY = os.getenv("BIDV_API_KEY")
BIDV_API_SECRET = os.getenv("BIDV_API_SECRET")

# ===========================
# ACCOUNT INFO
# ===========================
BIDV_ACCOUNT_NUMBER = os.getenv("BIDV_ACCOUNT_NUMBER")
BIDV_CURRENCY = os.getenv("BIDV_CURRENCY", "VND")

# ===========================
# OAUTH2 SETTINGS
# ===========================
OAUTH_SCOPE = os.getenv("OAUTH_SCOPE", "read")
OAUTH_REDIRECT_URI = os.getenv("OAUTH_REDIRECT_URI", "http://localhost:5000/callback")
TOKEN_CACHE_PATH = os.getenv("TOKEN_CACHE_PATH", "data/token.json")
TOKEN_EXPIRY_BUFFER = int(os.getenv("TOKEN_EXPIRY_BUFFER", "60"))  # seconds before expiry to refresh

# Ensure token cache directory exists
Path(TOKEN_CACHE_PATH).parent.mkdir(parents=True, exist_ok=True)

# ===========================
# SECURITY SETTINGS
# ===========================
JWS_ALG = os.getenv("JWS_ALG", "RS256")
JWS_DETACHED = os.getenv("JWS_DETACHED", "true").lower() == "true"

# JWE defaults (production). Allow override from env.
JWE_ALG = os.getenv("JWE_ALG", "A256KW")
JWE_ENC = os.getenv("JWE_ENC", "A128GCM")

PRIVATE_KEY_PATH = os.getenv("PRIVATE_KEY_PATH", "certs/private_key.pem")
CLIENT_CERT_PATH = os.getenv("CLIENT_CERT_PATH", "certs/client_cert.pem")
SYMMETRIC_KEY_PATH = os.getenv("SYMMETRIC_KEY_PATH", "certs/symmetric.key")

TLS_VERIFY = os.getenv("TLS_VERIFY", "true").lower() == "true"

# Toggle whether to use JWE encryption for outgoing payloads.
# In sandbox you may want to set USE_JWE=false to send plaintext JSON if sandbox doesn't require JWE.
USE_JWE = os.getenv("USE_JWE", "true").lower() == "true"

# Some sandbox deployments require the X-Client-Certificate header in addition to mutual TLS:
INCLUDE_CLIENT_CERT_HEADER = os.getenv("INCLUDE_CLIENT_CERT_HEADER", "false").lower() == "true"

# ===========================
# APPLICATION HEADERS
# ===========================
USER_AGENT = os.getenv("USER_AGENT", "BIDVMonitor/1.0")
CUSTOMER_IP = os.getenv("CUSTOMER_IP", "127.0.0.1")

# ===========================
# TIMEOUTS & RETRIES
# ===========================
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "30"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
RETRY_BACKOFF = int(os.getenv("RETRY_BACKOFF", "5"))

# ===========================
# LOGGING CONFIG
# ===========================
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", "logs/bidv_monitor.log")
LOG_ROTATE = os.getenv("LOG_ROTATE", "true").lower() == "true"
LOG_MAX_SIZE = int(os.getenv("LOG_MAX_SIZE", "10485760"))
LOG_BACKUP_COUNT = int(os.getenv("LOG_BACKUP_COUNT", "5"))

# Ensure log directory exists
Path(LOG_FILE).parent.mkdir(parents=True, exist_ok=True)

# ===========================
# ALERTING (optional)
# ===========================
ENABLE_ZALO_NOTIFY = os.getenv("ENABLE_ZALO_NOTIFY", "false").lower() == "true"
