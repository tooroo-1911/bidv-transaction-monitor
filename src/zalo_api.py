# src/zalo_api.py - Zalo API Client

import requests
import json
import time
from typing import Dict, List, Optional
import logging
from pathlib import Path

# Import cấu hình
import sys

from app_config import (
    ZALO_API_URL,
    REQUEST_TIMEOUT,
    MAX_RETRIES,
    RETRY_DELAY,
    ZALO_MESSAGE_TEMPLATE,
    ERROR_MESSAGE_TEMPLATE,
    STARTUP_MESSAGE_TEMPLATE,
    get_current_time,
    format_currency,
    load_secrets,
)

sys.path.append(str(Path(__file__).parent.parent))

logger = logging.getLogger(__name__)


class ZaloAPIError(Exception):
    """Custom exception cho Zalo API errors"""

    def __init__(self, message: str, error_code: int = None, response: Dict = None):
        self.message = message
        self.error_code = error_code
        self.response = response
        super().__init__(self.message)


class ZaloAPIClient:
    """Client để gửi thông báo qua Zalo Official Account"""

    def __init__(self):
        """Khởi tạo Zalo API client"""
        # Load secrets
        self.secrets = load_secrets()

        # Setup session
        self.session = requests.Session()
        self.session.timeout = REQUEST_TIMEOUT

        # Zalo API headers
        self.headers = {
            "Content-Type": "application/json",
            "access_token": self.secrets["zalo_access_token"],
        }

        logger.info("Zalo API Client initialized")

    def _make_request(self, data: Dict) -> Dict:
        """Thực hiện HTTP request với retry logic"""

        for attempt in range(MAX_RETRIES):
            try:
                logger.debug(f"Making Zalo API request, attempt {attempt + 1}")

                response = self.session.post(
                    ZALO_API_URL, json=data, headers=self.headers, timeout=REQUEST_TIMEOUT
                )

                # Log response cho debugging
                logger.debug(f"Response status: {response.status_code}")
                logger.debug(f"Response: {response.text[:200]}...")

                response.raise_for_status()

                # Parse JSON response
                try:
                    response_data = response.json()

                    # Kiểm tra Zalo error code
                    error_code = response_data.get("error", 0)
                    if error_code != 0:
                        error_message = response_data.get("message", "Unknown Zalo error")
                        raise ZaloAPIError(f"Zalo API error: {error_message}", error_code, response_data)

                    return response_data

                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON response: {response.text}")
                    raise ZaloAPIError(f"Invalid JSON response: {e}")

            except requests.exceptions.Timeout:
                logger.warning(f"Request timeout, attempt {attempt + 1}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY)
                    continue
                raise ZaloAPIError("Request timeout after retries")

            except requests.exceptions.RequestException as e:
                logger.error(f"Request error: {e}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY)
                    continue
                raise ZaloAPIError(f"Request failed: {e}")

        raise ZaloAPIError("Request failed after all retries")

    def send_text_message(self, message: str, user_id: str = None) -> bool:
        """
        Gửi tin nhắn text qua Zalo OA

        Args:
            message: Nội dung tin nhắn
            user_id: ID người nhận (None = dùng từ config)

        Returns:
            bool: True nếu gửi thành công
        """
        try:
            if user_id is None:
                user_id = self.secrets["zalo_user_id"]

            logger.info(f"Sending Zalo message to user {user_id}")

            # Request data
            data = {"recipient": {"user_id": user_id}, "message": {"text": message}}

            # Gửi request
            response = self._make_request(data)

            # Kiểm tra response
            if response.get("error") == 0:
                logger.info("Zalo message sent successfully")
                return True
            else:
                logger.error(f"Zalo message failed: {response}")
                return False

        except ZaloAPIError as e:
            logger.error(f"Zalo API error: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending Zalo message: {e}")
            return False

    def send_transaction_notification(self, transaction: Dict) -> bool:
        """
        Gửi thông báo giao dịch mới

        Args:
            transaction: Dict chứa thông tin giao dịch

        Returns:
            bool: True nếu gửi thành công
        """
        try:
            # Chỉ gửi thông báo cho giao dịch có tiền vào (credit > 0)
            credit_amount = transaction.get("credit_amount", 0)
            if credit_amount <= 0:
                logger.debug("Skipping notification for non-credit transaction")
                return False

            # Format message
            message = ZALO_MESSAGE_TEMPLATE.format(
                amount=format_currency(credit_amount),
                currency=transaction.get("curr_code", "VND"),
                date=transaction.get("tran_date", ""),
                remark=transaction.get("remark", "Không có mô tả"),
                ref=transaction.get("ref", ""),
                balance=format_currency(transaction.get("ending_balance", 0)),
                current_time=get_current_time(),
            )

            return self.send_text_message(message)

        except Exception as e:
            logger.error(f"Error sending transaction notification: {e}")
            return False

    def send_error_notification(self, error_message: str) -> bool:
        """
        Gửi thông báo lỗi

        Args:
            error_message: Mô tả lỗi

        Returns:
            bool: True nếu gửi thành công
        """
        try:
            message = ERROR_MESSAGE_TEMPLATE.format(
                error=error_message, time=get_current_time(), retry_delay=RETRY_DELAY
            )

            return self.send_text_message(message)

        except Exception as e:
            logger.error(f"Error sending error notification: {e}")
            return False

    def send_startup_notification(self, account_number: str, check_interval: int) -> bool:
        """
        Gửi thông báo khi hệ thống khởi động

        Args:
            account_number: Số tài khoản đang theo dõi
            check_interval: Khoảng thời gian kiểm tra (giây)

        Returns:
            bool: True nếu gửi thành công
        """
        try:
            # Ẩn một phần số tài khoản cho bảo mật
            masked_account = (
                account_number[:4] + "****" + account_number[-4:]
                if len(account_number) > 8
                else account_number
            )

            message = STARTUP_MESSAGE_TEMPLATE.format(account=masked_account, interval=check_interval)

            return self.send_text_message(message)

        except Exception as e:
            logger.error(f"Error sending startup notification: {e}")
            return False

    def send_batch_notifications(self, transactions: List[Dict]) -> int:
        """
        Gửi thông báo cho nhiều giao dịch

        Args:
            transactions: Danh sách giao dịch

        Returns:
            int: Số thông báo gửi thành công
        """
        successful_count = 0

        for transaction in transactions:
            try:
                if self.send_transaction_notification(transaction):
                    successful_count += 1

                # Delay giữa các message để tránh spam
                time.sleep(1)

            except Exception as e:
                logger.error(f"Error in batch notification: {e}")
                continue

        logger.info(f"Sent {successful_count}/{len(transactions)} notifications successfully")
        return successful_count

    def send_custom_message(self, message: str, user_id: str = None) -> bool:
        """
        Gửi tin nhắn tùy chỉnh

        Args:
            message: Nội dung tin nhắn
            user_id: ID người nhận

        Returns:
            bool: True nếu gửi thành công
        """
        return self.send_text_message(message, user_id)

    def send_rich_message(self, title: str, subtitle: str, buttons: List[Dict] = None) -> bool:
        """
        Gửi tin nhắn rich format (nếu Zalo OA hỗ trợ)

        Args:
            title: Tiêu đề
            subtitle: Phụ đề
            buttons: Danh sách buttons

        Returns:
            bool: True nếu gửi thành công
        """
        try:
            # Rich message format cho Zalo OA
            data = {
                "recipient": {"user_id": self.secrets["zalo_user_id"]},
                "message": {
                    "attachment": {
                        "type": "template",
                        "payload": {
                            "template_type": "generic",
                            "elements": [{"title": title, "subtitle": subtitle, "buttons": buttons or []}],
                        },
                    }
                },
            }

            response = self._make_request(data)
            return response.get("error") == 0

        except Exception as e:
            logger.error(f"Error sending rich message: {e}")
            # Fallback to text message
            fallback_message = f"{title}\n{subtitle}"
            return self.send_text_message(fallback_message)

    def health_check(self) -> bool:
        """
        Kiểm tra kết nối với Zalo API

        Returns:
            bool: True nếu kết nối OK
        """
        try:
            logger.info("Performing Zalo API health check")

            # Gửi tin nhắn test đơn giản
            test_message = f"🔍 Zalo API Health Check - {get_current_time()}"

            return self.send_text_message(test_message)

        except Exception as e:
            logger.error(f"Zalo API health check failed: {e}")
            return False

    def get_user_info(self, user_id: str = None) -> Optional[Dict]:
        """
        Lấy thông tin user (nếu API hỗ trợ)

        Args:
            user_id: ID người dùng

        Returns:
            Dict: Thông tin user hoặc None
        """
        try:
            if user_id is None:
                user_id = self.secrets["zalo_user_id"]

            # API để lấy user info (URL có thể khác)
            user_info_url = "https://openapi.zalo.me/v2.0/oa/getuser"

            params = {"data": json.dumps({"user_id": user_id})}

            response = self.session.get(
                user_info_url, params=params, headers=self.headers, timeout=REQUEST_TIMEOUT
            )

            if response.status_code == 200:
                return response.json()

            return None

        except Exception as e:
            logger.error(f"Error getting user info: {e}")
            return None


# Factory function để tạo client
def create_zalo_client() -> ZaloAPIClient:
    """Factory function để tạo Zalo API client"""
    return ZaloAPIClient()


# Helper functions
def format_transaction_summary(transactions: List[Dict]) -> str:
    """Format tóm tắt nhiều giao dịch"""
    if not transactions:
        return "Không có giao dịch mới"

    total_amount = sum(t.get("credit_amount", 0) for t in transactions)
    count = len(transactions)

    summary = "TÓM TẮT GIAO DỊCH\n\n"
    summary += f"Số giao dịch: {count}\n"
    summary += f"Tổng tiền vào: {format_currency(total_amount)} VND\n"
    summary += f"Thời gian: {get_current_time()}\n\n"

    # Liệt kê từng giao dịch (tối đa 5)
    for i, trans in enumerate(transactions[:5]):
        summary += f"• {format_currency(trans.get('credit_amount', 0))} VND - {trans.get('remark', 'N/A')}\n"

    if len(transactions) > 5:
        summary += f"... và {len(transactions) - 5} giao dịch khác"

    return summary


# Test khi chạy trực tiếp
if __name__ == "__main__":
    print("Testing Zalo API Client")

    try:
        # Tạo client
        client = create_zalo_client()
        print("Client created successfully")

        # Health check
        if client.health_check():
            print("Health check passed")

            # Test transaction notification
            sample_transaction = {
                "credit_amount": 1000000,
                "curr_code": "VND",
                "tran_date": "01/01/2024 10:30:00",
                "remark": "Test transaction notification",
                "ref": "TEST123456",
                "ending_balance": 5000000,
            }

            if client.send_transaction_notification(sample_transaction):
                print("Test transaction notification sent")
            else:
                print("Failed to send transaction notification")
        else:
            print("Health check failed")

    except Exception as e:
        print(f"Error: {e}")
