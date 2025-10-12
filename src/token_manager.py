import json
import time
import logging
from pathlib import Path
import requests
import src.app_config as cfg


# ===========================
# LOGGING
# ===========================
logger = logging.getLogger(__name__)


# ===========================
# TOKEN MANAGER CLASS
# ===========================
class TokenManager:
    def __init__(self):
        self.token_path = Path(cfg.TOKEN_CACHE_PATH)

    def load_token(self):
        """Đọc token từ file cache."""
        if not self.token_path.exists():
            return None
        try:
            with open(self.token_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            logger.warning("Token cache corrupted, ignoring.")
            return None

    def save_token(self, token_data):
        """Lưu token vào file cache."""
        self.token_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.token_path, "w", encoding="utf-8") as f:
            json.dump(token_data, f, ensure_ascii=False, indent=2)

    def is_token_expired(self, token_data):
        """Kiểm tra token có sắp hết hạn không."""
        expires_at = token_data.get("expires_at", 0)
        return (time.time() + cfg.TOKEN_EXPIRY_BUFFER) >= expires_at

    def refresh_token(self, refresh_token):
        """Gọi API BIDV để refresh token."""
        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": cfg.BIDV_CLIENT_ID,
            "client_secret": cfg.BIDV_CLIENT_SECRET,
            "redirect_uri": cfg.OAUTH_REDIRECT_URI,
        }

        logger.info("Refreshing OAuth2 token using refresh_token...")
        resp = requests.post(
            cfg.BIDV_OAUTH_TOKEN_URL, data=data, timeout=cfg.REQUEST_TIMEOUT, verify=cfg.TLS_VERIFY
        )
        if resp.status_code != 200:
            logger.error("Refresh token failed: %s %s", resp.status_code, resp.text)
            raise Exception(f"Refresh token failed: {resp.status_code} {resp.text}")

        token_info = resp.json()
        token_info["expires_at"] = time.time() + token_info.get("expires_in", 3600)
        self.save_token(token_info)
        return token_info

    def get_access_token(self):
        """
        Trả về access_token hợp lệ.
        Nếu hết hạn → refresh.
        Nếu không có token → raise Exception.
        """
        token_data = self.load_token()
        if not token_data:
            raise Exception("No token found. Please run oauth_listener.py to get new token.")

        if self.is_token_expired(token_data):
            refresh_token = token_data.get("refresh_token")
            if not refresh_token:
                raise Exception("No refresh token available. Please re-authorize.")
            token_data = self.refresh_token(refresh_token)

        return token_data["access_token"]


# ===========================
# MODULE-LEVEL HELPERS
# ===========================
_manager = TokenManager()


def get_access_token():
    return _manager.get_access_token()


# ===========================
# QUICK TEST WHEN RUN DIRECTLY
# ===========================
if __name__ == "__main__":
    logging.basicConfig(level=cfg.LOG_LEVEL, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    try:
        token = get_access_token()
        print("Access Token:", token)
    except Exception as e:
        logger.error("Error getting access token: %s", e)
