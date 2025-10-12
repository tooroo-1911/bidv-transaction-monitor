import json
import time
import logging
from pathlib import Path
from urllib.parse import urlencode

import requests
from flask import Flask, request

import src.app_config as cfg


logger = logging.getLogger(__name__)


app = Flask(__name__)


def save_token(token_data):
    Path(cfg.TOKEN_CACHE_PATH).parent.mkdir(parents=True, exist_ok=True)
    with open(cfg.TOKEN_CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(token_data, f, ensure_ascii=False, indent=2)
    logger.info("Access token saved to %s", cfg.TOKEN_CACHE_PATH)


def exchange_code_for_token(auth_code):
    data = {
        "grant_type": cfg.OAUTH_GRANT_TYPE,
        "code": auth_code,
        "redirect_uri": cfg.OAUTH_REDIRECT_URI,
        "client_id": cfg.BIDV_CLIENT_ID,
        "client_secret": cfg.BIDV_CLIENT_SECRET,
    }
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": cfg.USER_AGENT,
        "Accept": "application/json",
    }

    logger.info("Exchanging code for token...")

    resp = requests.post(
        cfg.BIDV_OAUTH_TOKEN_URL,
        data=data,
        timeout=cfg.REQUEST_TIMEOUT,
        verify=cfg.TLS_VERIFY,
        headers=headers,
    )

    if resp.status_code != 200:
        logger.error("Failed to get token: %s", resp.text)
        return None

    token_info = resp.json()
    token_info["created_at"] = int(time.time())
    return token_info


@app.route("/callback")
def callback():
    code = request.args.get("code")
    if not code:
        return "Error: No 'code' parameter in callback.", 400

    logger.info("Authorization code received: %s", code)

    token_data = exchange_code_for_token(code)
    if not token_data:
        return "Error exchanging code for token", 500

    save_token(token_data)
    return "Access token saved successfully. You can close this window."


if __name__ == "__main__":
    logger.info("Starting OAuth listener on %s", cfg.OAUTH_REDIRECT_URI)
    logger.info("Go to the BIDV authorization URL to approve access:")
    auth_params = {
        "client_id": cfg.BIDV_CLIENT_ID,
        "scope": cfg.OAUTH_SCOPE,
        "redirect_uri": cfg.OAUTH_REDIRECT_URI,
        "response_type": "code",
    }
    auth_url = f"{cfg.BIDV_OAUTH_AUTHORIZE_URL}?{urlencode(auth_params)}"
    logger.info("AUTH URL: %s", auth_url)

    app.run(host="0.0.0.0", port=5000, debug=False)
