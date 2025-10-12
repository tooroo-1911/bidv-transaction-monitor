# main.py
import logging
import time
from utils.db_manager import create_table
from src.transaction_monitor import sync_transactions, show_statistics
from src import app_config as config

logging.basicConfig(
    level=config.LOG_LEVEL,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler(config.LOG_FILE, encoding="utf-8"), logging.StreamHandler()],
)

logger = logging.getLogger("main")


def main():
    logger.info("BIDV Transaction Monitor khởi động")
    logger.info("Vòng lặp đồng bộ mỗi 60 giây")

    create_table()
    show_statistics()

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
                logger.info("THỐNG KÊ SAU {} LẦN ĐỒNG BỘ".format(sync_count))
                show_statistics()
                logger.info("=" * 50)

            time.sleep(60)

        except KeyboardInterrupt:
            logger.info("Người dùng dừng chương trình")
            logger.info("THỐNG KÊ CUỐI:")
            show_statistics()
            break

        except Exception as e:
            consecutive_errors += 1
            logger.error(f"Lỗi chương trình (lần {consecutive_errors}): {e}")

            if consecutive_errors >= 5:
                wait_time = 300  # 5 phút
                logger.warning(f"Lỗi liên tục {consecutive_errors} lần, đợi {wait_time}s")
                time.sleep(wait_time)
            else:
                time.sleep(60)


if __name__ == "__main__":
    main()
