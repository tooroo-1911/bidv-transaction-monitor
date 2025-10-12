# utils/crypto_utils.py
import json
import base64
from typing import Dict, Optional
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend
from jwcrypto import jwk, jwe
import src.app_config as config
import os
from pathlib import Path


# ------------------------
# Helpers base64url
# ------------------------
def b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def b64url_decode(data: str) -> bytes:
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))


# ------------------------
# Detached JWS signer
# ------------------------
def sign_detached_jws(payload: str, private_key_path: Optional[str] = None, alg: Optional[str] = None) -> str:
    private_key_path = private_key_path or config.PRIVATE_KEY_PATH
    alg = alg or config.JWS_ALG

    if not os.path.exists(private_key_path):
        raise FileNotFoundError(f"Private key file not found: {private_key_path}")

    with open(private_key_path, "rb") as key_file:
        pem_data = key_file.read()

    private_key = serialization.load_pem_private_key(pem_data, password=None, backend=default_backend())

    header = {"alg": alg}
    encoded_header = b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))

    payload_bytes = payload.encode("utf-8")
    encoded_payload = b64url_encode(payload_bytes)

    signing_input = (encoded_header + "." + encoded_payload).encode("ascii")

    if alg.upper() == "RS256":
        signature = private_key.sign(signing_input, padding.PKCS1v15(), hashes.SHA256())
    else:
        raise ValueError(f"Unsupported JWS algorithm: {alg}")

    encoded_sig = b64url_encode(signature)
    return f"{encoded_header}..{encoded_sig}"


# ------------------------
# JWE Encrypt (JSON Serialization)
# ------------------------
def encrypt_jwe(
    payload: Dict,
    symmetric_key_path: Optional[str] = None,
    alg: Optional[str] = None,
    enc: Optional[str] = None,
) -> Dict:
    symmetric_key_path = symmetric_key_path or config.SYMMETRIC_KEY_PATH
    alg = alg or config.JWE_ALG
    enc = enc or config.JWE_ENC

    if not os.path.exists(symmetric_key_path):
        raise FileNotFoundError(f"Symmetric key file not found: {symmetric_key_path}")

    key_b64 = open(symmetric_key_path, "r").read().strip()
    raw_key = base64.b64decode(key_b64)
    if len(raw_key) not in (16, 24, 32):
        raise ValueError(f"Invalid key length: expected 16/24/32 bytes, got {len(raw_key)}")

    key = jwk.JWK(kty="oct", k=b64url_encode(raw_key))
    protected_header = {"alg": alg, "enc": enc}

    jwetoken = jwe.JWE(json.dumps(payload, separators=(",", ":")).encode("utf-8"), protected=protected_header)
    jwetoken.add_recipient(key)
    serialized = jwetoken.serialize(compact=False)
    return json.loads(serialized)


# ------------------------
# JWE Decrypt (JSON Serialization)
# ------------------------
def decrypt_jwe(jwe_json: Dict, symmetric_key_path: Optional[str] = None) -> Dict:
    symmetric_key_path = symmetric_key_path or config.SYMMETRIC_KEY_PATH

    if not os.path.exists(symmetric_key_path):
        raise FileNotFoundError(f"Symmetric key file not found: {symmetric_key_path}")

    key_b64 = open(symmetric_key_path, "r").read().strip()
    raw_key = base64.b64decode(key_b64)
    if len(raw_key) not in (16, 24, 32):
        raise ValueError(f"Invalid key length: expected 16/24/32 bytes, got {len(raw_key)}")

    key = jwk.JWK(kty="oct", k=b64url_encode(raw_key))
    serialized = json.dumps(jwe_json, separators=(",", ":"))
    jwetoken = jwe.JWE()
    jwetoken.deserialize(serialized)
    jwetoken.decrypt(key)
    plaintext = jwetoken.payload
    return json.loads(plaintext.decode("utf-8"))


# ------------------------
# Helper: produce base64 certificate string for X-Client-Certificate header
# ------------------------
def get_client_certificate_b64(cert_path: Optional[str] = None) -> str:
    """
    Read a PEM (or DER) certificate file and return base64 string suitable for X-Client-Certificate header.
    - If PEM: extract base64 block between BEGIN/END and join into single-line base64.
    - If DER (binary): base64-encode the binary.
    """
    cert_path = cert_path or config.CLIENT_CERT_PATH
    if not cert_path or not Path(cert_path).exists():
        raise FileNotFoundError(f"Client certificate not found: {cert_path}")

    data = Path(cert_path).read_bytes()
    try:
        text = data.decode("utf-8")
        if "-----BEGIN CERTIFICATE-----" in text:
            # extract base64 between headers
            b64_lines = []
            in_block = False
            for line in text.splitlines():
                if "-----BEGIN CERTIFICATE-----" in line:
                    in_block = True
                    continue
                if "-----END CERTIFICATE-----" in line:
                    break
                if in_block:
                    b64_lines.append(line.strip())
            return "".join(b64_lines)
    except UnicodeDecodeError:
        # binary DER
        pass

    # fallback: base64 encode the raw bytes
    return base64.b64encode(data).decode("utf-8")
