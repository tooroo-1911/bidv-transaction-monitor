import sqlite3
from pathlib import Path
import logging
from typing import List, Dict


logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent.parent / "data" / "transactions.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def get_connection():
    return sqlite3.connect(DB_PATH)


def create_table():
    """
    Tạo bảng processed_transactions nếu chưa tồn tại,
    khóa chính là (seq, tranDate) để tránh trùng giao dịch.
    """
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS processed_transactions (
                seq TEXT NOT NULL,
                tranDate TEXT NOT NULL,
                remark TEXT,
                debitAmount REAL DEFAULT 0,
                creditAmount REAL DEFAULT 0,
                ref TEXT,
                currCode TEXT DEFAULT 'VND',
                processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (seq, tranDate)
            )
            """
        )

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_tranDate
            ON processed_transactions(tranDate)
            """
        )
        conn.commit()
    logger.info("Bảng processed_transactions đã sẵn sàng.")


def has_transaction(seq: str, tranDate: str) -> bool:
    """
    Kiểm tra giao dịch đã tồn tại trong DB theo (seq, tranDate).
    """
    with get_connection() as conn:
        cur = conn.execute(
            "SELECT 1 FROM processed_transactions WHERE seq=? AND tranDate=?",
            (seq, tranDate),
        )
        found = cur.fetchone() is not None
    return found


def add_transaction(tx: dict) -> bool:
    """
    Thêm giao dịch mới vào DB.
    Trả về True nếu thêm thành công, False nếu đã tồn tại.
    """
    try:
        debit_amount = float(tx.get("debitAmount", 0)) if tx.get("debitAmount") else 0
        credit_amount = float(tx.get("creditAmount", 0)) if tx.get("creditAmount") else 0

        with get_connection() as conn:
            cur = conn.execute(
                """
                INSERT OR IGNORE INTO processed_transactions
                (seq, tranDate, remark, debitAmount, creditAmount, ref, currCode)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    tx.get("seq"),
                    tx.get("tranDate"),
                    tx.get("remark"),
                    debit_amount,
                    credit_amount,
                    tx.get("ref"),
                    tx.get("currCode", "VND"),
                ),
            )
            conn.commit()

            rows_affected = cur.rowcount

        if rows_affected > 0:
            logger.info(f"Thêm giao dịch mới: seq={tx.get('seq')}, ref={tx.get('ref')}")
            return True
        else:
            logger.debug(f"Giao dịch đã tồn tại: seq={tx.get('seq')}, tranDate={tx.get('tranDate')}")
            return False

    except Exception as e:
        logger.error(f"Lỗi khi thêm giao dịch: {e}")
        return False


def add_transactions_batch(transactions: List[dict]) -> int:
    """
    Thêm nhiều giao dịch cùng lúc. Trả về số giao dịch mới được thêm.
    """
    new_count = 0
    for tx in transactions:
        if add_transaction(tx):
            new_count += 1

    logger.info(f"Đã xử lý {len(transactions)} giao dịch, {new_count} giao dịch mới")
    return new_count


def get_transaction_count() -> int:
    """Đếm tổng số giao dịch trong DB"""
    with get_connection() as conn:
        cur = conn.execute("SELECT COUNT(*) FROM processed_transactions")
        return cur.fetchone()[0]


def get_latest_transactions(limit: int = 10) -> List[Dict]:
    """Lấy các giao dịch mới nhất"""
    with get_connection() as conn:
        cur = conn.execute(
            """
            SELECT * FROM processed_transactions
            ORDER BY processed_at DESC
            LIMIT ?
            """,
            (limit,),
        )
        columns = [desc[0] for desc in cur.description]
        return [dict(zip(columns, row)) for row in cur.fetchall()]


def process_api_response(response_data: dict) -> int:
    """
    Xử lý response từ API và lưu vào DB.
    Trả về số giao dịch mới được thêm.
    """
    if not response_data or "body" not in response_data:
        logger.warning("Response data không hợp lệ")
        return 0

    body = response_data["body"]
    transactions = body.get("trans", [])

    if not transactions:
        logger.info("Không có giao dịch mới")
        return 0

    logger.info(f"Bắt đầu xử lý {len(transactions)} giao dịch từ API")
    new_count = add_transactions_batch(transactions)

    try:
        total_records = int(body.get("totalRecords", 0))
        starting_bal = float(body.get("startingBal", 0))
        ending_bal = float(body.get("endingBal", 0))

        logger.info(f"Thống kê: {total_records} giao dịch, Số dư: {starting_bal:,.0f} → {ending_bal:,.0f} VND")
    except (ValueError, TypeError) as e:
        logger.info(
            (
                f"Thống kê: {body.get('totalRecords')} giao dịch, "
                f"Số dư: {body.get('startingBal')} → {body.get('endingBal')} VND"
            )
        )
        logger.debug(f"Format error: {e}")

    return new_count


if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    create_table()

    sample_response = {
        "body": {
            "result": "0",
            "totalRecords": 1,
            "totalPages": 1,
            "page": 1,
            "startingBal": 100000000,
            "endingBal": 1002075285,
            "trans": [
                {
                    "seq": "1221",
                    "tranDate": "01/01/2020 06:08:00",
                    "remark": "Test Remark",
                    "debitAmount": "10000",
                    "creditAmount": "0",
                    "ref": "ABC1234343",
                    "currCode": "VND",
                }
            ],
        }
    }

    print(f"Số giao dịch trong DB trước: {get_transaction_count()}")
    new_transactions = process_api_response(sample_response)
    print(f"Đã thêm {new_transactions} giao dịch mới")
    print(f"Tổng số giao dịch trong DB: {get_transaction_count()}")

    print("\nGiao dịch mới nhất:")
    for tx in get_latest_transactions(5):
        print(f"  {tx['seq']} - {tx['tranDate']} - {tx['remark']} - {tx['debitAmount']:,} VND")
