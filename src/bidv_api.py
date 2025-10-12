import json
import uuid
import logging
from datetime import datetime
from typing import Dict, Any

import src.app_config as config
from src.token_manager import get_access_token
from utils.crypto_utils import (
    sign_detached_jws,
    encrypt_jwe,
    decrypt_jwe,
    get_client_certificate_b64,
)
from utils.network_utils import create_ssl_session


logger = logging.getLogger(__name__)


def build_headers(jws_signature: str, include_client_cert_header: bool = False) -> Dict[str, str]:
    """Tạo header chuẩn cho BIDV API"""
    headers = {
        "Authorization": f"Bearer {get_access_token()}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": config.USER_AGENT,
        "X-API-Interaction-ID": str(uuid.uuid4()),
        "X-Idempotency-Key": str(uuid.uuid4()),
        "X-Customer-IP-Address": config.CUSTOMER_IP,
        "Timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%fZ")[:-3] + "Z",
        "Channel": config.CHANNEL_ID,
        "X-JWS-Signature": jws_signature,
    }

    if include_client_cert_header:
        try:
            cert_b64 = get_client_certificate_b64(config.CLIENT_CERT_PATH)
            headers["X-Client-Certificate"] = cert_b64
        except Exception as e:
            logger.warning("Could not include X-Client-Certificate header: %s", e)

    return headers


def prepare_payload_and_signature(payload: Dict[str, Any]):
    payload_json = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
    # signature is always over the original JSON payload (compact form)
    jws_signature = sign_detached_jws(payload_json)
    if config.USE_JWE:
        encrypted_payload = encrypt_jwe(payload)
        return encrypted_payload, jws_signature
    else:
        # send plaintext JSON (some sandboxes expect raw JSON)
        return payload, jws_signature


def inquire_account_transactions(start_date: str, end_date: str, page: int = 1) -> Dict[str, Any]:
    """
    Tra cứu giao dịch tài khoản BIDV
    start_date, end_date: dạng 'YYYY-MM-DD'
    page: số trang
    """
    payload = {
        "actNumber": config.BIDV_ACCOUNT_NUMBER,
        "curr": config.BIDV_CURRENCY,
        "fromDate": start_date.replace("-", ""),
        "toDate": end_date.replace("-", ""),
        "page": str(page),
    }

    body_to_send, jws_signature = prepare_payload_and_signature(payload)
    headers = build_headers(jws_signature, include_client_cert_header=config.INCLUDE_CLIENT_CERT_HEADER)

    url = f"{config.BIDV_BASE_URL}{config.BIDV_API_INQUIRE_PATH}"
    session = create_ssl_session()

    logger.info("Calling BIDV API: %s", url)
    response = session.post(url, headers=headers, json=body_to_send, timeout=config.REQUEST_TIMEOUT)

    if response.status_code != 200:
        logger.error("API request failed: %s - %s", response.status_code, response.text)
        raise Exception(f"API request failed: {response.status_code} - {response.text}")

    try:
        # If server returns JWE JSON serialization, decrypt; if plaintext, response.json() is final
        resp_json = response.json()
        if config.USE_JWE:
            decrypted_data = decrypt_jwe(resp_json)
            logger.info("API request successful and response decrypted")
            return decrypted_data
        else:
            logger.info("API request successful (plaintext response)")
            return resp_json
    except Exception as e:
        logger.error("Failed to parse/decrypt response: %s", e)
        raise


if __name__ == "__main__":
    try:
        logger.info("Testing BIDV API client...")
        transactions = inquire_account_transactions("2025-07-01", "2025-07-31")
        print(json.dumps(transactions, indent=2, ensure_ascii=False))

    except Exception as e:
        logger.exception("Error during BIDV API test: %s", e)
