import logging
from logging.handlers import RotatingFileHandler
from src.app_config import LOG_FILE, LOG_LEVEL, LOG_MAX_SIZE, LOG_BACKUP_COUNT


def setup_logger():
    """
    Thiết lập logger chung cho toàn app.
    - Log ra file xoay vòng (RotatingFileHandler)
    - Log ra console
    - Mức log lấy từ app_config
    """
    logger = logging.getLogger()
    logger.setLevel(LOG_LEVEL)

    formatter = logging.Formatter("%(asctime)s [%(levelname)s] [%(module)s] %(message)s")

    file_handler = RotatingFileHandler(
        LOG_FILE, maxBytes=LOG_MAX_SIZE, backupCount=LOG_BACKUP_COUNT, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger
