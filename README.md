# BIDV Monitor

Python tool to monitor BIDV account transactions using BIDV OpenAPI, with support for OAuth2, JWS/JWE encryption, and optional Zalo notifications.

## Features
- Automatic token management (OAuth2)
- Fetch account transactions & balances
- Optional alert via Zalo
- Sandbox-ready with TLS/Mutual TLS
- Logs & database for transaction history

## Project Structure
```
bidv-monitor/
├── certs/ # TLS & JWS/JWE certificates and keys
├── data/ # Cached and stored transactions
├── logs/ # Application logs
├── src/ # Python modules
├── utils/ # Helper modules (crypto, network, db, logger)
├── .env # Environment variables (not pushed!)
├── requirements.txt # Python dependencies
├── sandbox_openssl.cnf # OpenSSL config for sandbox
```

## Setup
1. Copy `.env.example` → `.env` and fill in your credentials
2. Install dependencies: `pip install -r requirements.txt`
3. Run main script: `python src/main.py`
