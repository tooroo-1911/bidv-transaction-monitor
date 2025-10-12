import logging
from datetime import datetime, timedelta

from src.bidv_api import inquire_account_transactions
from utils.db_manager import process_api_response, get_transaction_count, get_latest_transactions
from src.token_manager import get_access_token


logger = logging.getLogger(__name__)


def sync_transactions(days_back: int = 30) -> int:
    """Đồng bộ giao dịch từ API về database, mặc định lấy 30 ngày gần nhất"""
    try:
        get_access_token()
        logger.debug("Access token hợp lệ.")

        end_date = datetime.today()
        start_date = end_date - timedelta(days=days_back)
        str_start = start_date.strftime("%Y-%m-%d")
        str_end = end_date.strftime("%Y-%m-%d")

        logger.debug(f"Đồng bộ giao dịch từ {str_start} đến {str_end}")

        transactions_data = inquire_account_transactions(str_start, str_end, page=1)
        if transactions_data is None:
            logger.warning("API trả về None!")
            return 0

        new_count = process_api_response(transactions_data)

        total_in_db = get_transaction_count()

        if new_count > 0:
            logger.info(f"Đồng bộ thành công! {new_count} giao dịch mới (Tổng: {total_in_db:,})")

            latest = get_latest_transactions(3)
            for tx in latest[:new_count]:
                amount = tx["debitAmount"] if tx["debitAmount"] > 0 else tx["creditAmount"]
                tx_type = "Rút" if tx["debitAmount"] > 0 else "Nạp"
                logger.info(f"   {tx_type}: {amount:,.0f} VND - {tx['remark']}")
        else:
            logger.info(f"Không có giao dịch mới (Tổng trong DB: {total_in_db:,})")

        return new_count

    except Exception as e:
        logger.error(f"Lỗi đồng bộ: {e}")
        return 0


def show_statistics():
    """Hiển thị thống kê database"""
    try:
        total = get_transaction_count()
        logger.info(f"Tổng số giao dịch: {total:,}")

        if total > 0:
            recent = get_latest_transactions(5)
            logger.info("5 giao dịch gần nhất:")
            for i, tx in enumerate(recent, 1):
                amount = tx["debitAmount"] if tx["debitAmount"] > 0 else tx["creditAmount"]
                tx_type = "Rút" if tx["debitAmount"] > 0 else "Nạp"
                logger.info(f"   {i}. {tx['tranDate']} - {tx_type}: {amount:,.0f} VND")
    except Exception as e:
        logger.error(f"Lỗi hiển thị thống kê: {e}")
