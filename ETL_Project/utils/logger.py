import logging
import os


def setup_logger(name: str = __name__):
    """
    Khởi tạo logger cho toàn bộ ETL project.

    Logger sẽ ghi log ra:
    1. Terminal
    2. File logs/etl.log

    Parameters
    ----------
    name : str
        Tên logger.
        Thường truyền __name__.

    Returns
    -------
    logging.Logger
        Logger đã được cấu hình.
    """

    # Tạo logger
    logger = logging.getLogger(name)

    # Tránh add handler nhiều lần
    if logger.handlers:
        return logger

    # Mức log tối thiểu
    logger.setLevel(logging.INFO)

    # Tạo thư mục logs nếu chưa tồn tại
    os.makedirs("logs", exist_ok=True)

    # File log
    log_file = os.path.join("logs", "etl.log")

    # Format log
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )

    # Log ra terminal
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    # Log ra file
    file_handler = logging.FileHandler(log_file, encoding="utf-8")

    file_handler.setFormatter(formatter)

    # Add handlers
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    # Không cho log bị lặp lên root logger
    logger.propagate = False

    return logger
