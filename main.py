import logging
import time
import threading
import webbrowser
from urllib.parse import urlencode
from pathlib import Path
import json

from utils.db_manager import create_table
from src.transaction_monitor import sync_transactions, show_statistics
from src import app_config as config
from src.token_manager import get_access_token
from src.oauth_listener import app as oauth_app


logging.basicConfig(
    level=config.LOG_LEVEL,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler(config.LOG_FILE, encoding="utf-8"), logging.StreamHandler()],
)
logger = logging.getLogger("main")

TOKEN_PATH = Path(config.TOKEN_CACHE_PATH)


def run_oauth_listener_background():
    """Chạy Flask server trong background để lắng nghe callback từ BIDV."""

    def run():
        oauth_app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)

    t = threading.Thread(target=run, daemon=True)
    t.start()
    return t


def request_new_token():
    """Khởi động quy trình OAuth2 để xin token mới."""
    logger.info("Không tìm thấy token hợp lệ — khởi động quy trình lấy token mới.")
    run_oauth_listener_background()

    # Tạo URL xác thực BIDV
    params = {
        "client_id": config.BIDV_CLIENT_ID,
        "scope": config.OAUTH_SCOPE,
        "redirect_uri": config.OAUTH_REDIRECT_URI,
        "response_type": "code",
    }
    auth_url = f"{config.BIDV_OAUTH_AUTHORIZE_URL}?{urlencode(params)}"
    logger.info(f"Mở trình duyệt để xác thực: {auth_url}")
    webbrowser.open(auth_url)

    # Đợi token.json được lưu (do callback)
    logger.info("Đang chờ BIDV redirect và lưu token.json ...")
    start_time = time.time()
    while time.time() - start_time < 180:  # tối đa 3 phút
        if TOKEN_PATH.exists():
            try:
                with open(TOKEN_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if "access_token" in data and "refresh_token" in data:
                    logger.info("Token hợp lệ — tiếp tục chương trình")
                    return True
                else:
                    logger.warning("Token.json chưa hoàn chỉnh, chờ thêm...")
            except Exception:
                logger.warning("Token.json đang được ghi, thử lại...")

        for _ in range(5):
            try:
                with open(TOKEN_PATH, "r", encoding="utf-8") as f:
                    json.load(f)
                break
            except Exception:
                time.sleep(1)
    logger.error("Hết thời gian chờ token — vui lòng thử lại.")
    return False


def ensure_token_available():
    """Đảm bảo có access_token hợp lệ trước khi đồng bộ."""
    try:
        token = get_access_token()
        if token:
            logger.info("Access token hiện tại hợp lệ.")
            return True
    except Exception as e:
        logger.warning(f"Token chưa hợp lệ hoặc chưa tồn tại: {e}")
    return request_new_token()


def main():
    logger.info("BIDV Transaction Monitor khởi động")
    logger.info("Vòng lặp đồng bộ mỗi 60 giây")

    create_table()
    show_statistics()

    # Đảm bảo có token trước khi chạy
    if not ensure_token_available():
        logger.error("Không thể lấy token, chương trình dừng.")
        return

    sync_count = 0
    consecutive_errors = 0

    while True:
        try:
            sync_count += 1
            logger.info(f"Lần đồng bộ #{sync_count}")

            new_transactions = sync_transactions()

            if new_transactions >= 0:
                consecutive_errors = 0

            if sync_count % 10 == 0:
                logger.info("=" * 50)
                logger.info(f"THỐNG KÊ SAU {sync_count} LẦN ĐỒNG BỘ")
                show_statistics()
                logger.info("=" * 50)

            time.sleep(60)

        except KeyboardInterrupt:
            logger.info("Người dùng dừng chương trình.")
            logger.info("THỐNG KÊ CUỐI:")
            show_statistics()
            break

        except Exception as e:
            consecutive_errors += 1
            logger.error(f"Lỗi chương trình (lần {consecutive_errors}): {e}")

            if consecutive_errors >= 5:
                wait_time = 300  # 5 phút
                logger.warning(f"Lỗi liên tục {consecutive_errors} lần, đợi {wait_time}s.")
                time.sleep(wait_time)
            else:
                time.sleep(60)


if __name__ == "__main__":
    main()
