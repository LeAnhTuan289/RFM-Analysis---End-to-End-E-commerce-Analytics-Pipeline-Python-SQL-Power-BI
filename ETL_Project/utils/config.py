"""
Quản lý toàn bộ biến môi trường của dự án ETL.

Nhiệm vụ:
1. Load file .env
2. Kiểm tra biến môi trường tồn tại
3. Kiểm tra file credential tồn tại
4. Cung cấp các hàm lấy config
"""

import os
from dotenv import load_dotenv


def load_env_variables():
    """
    Load file .env từ thư mục gốc project.

    Hàm này chỉ cần gọi 1 lần khi ứng dụng khởi động.
    """

    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    env_path = os.path.join(project_root, ".env")

    load_dotenv(env_path)


def get_gcs_credentials_path():
    """
    Trả về đường dẫn file key dùng cho GCS.
    """

    creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

    if not creds_path:
        raise ValueError("Thiếu biến GOOGLE_APPLICATION_CREDENTIALS")

    if not os.path.exists(creds_path):
        raise FileNotFoundError(f"Không tìm thấy file: {creds_path}")

    return creds_path


def get_bigquery_credentials_path():
    """
    Trả về đường dẫn file key dùng cho BigQuery.
    """

    creds_path = os.getenv("BIGQUERY_KEY_PATH")

    if not creds_path:
        raise ValueError("Thiếu biến BIGQUERY_KEY_PATH")

    if not os.path.exists(creds_path):
        raise FileNotFoundError(f"Không tìm thấy file: {creds_path}")

    return creds_path


def get_project_id():
    """
    Lấy GCP Project ID.
    """

    project_id = os.getenv("GCP_PROJECT_ID")

    if not project_id:
        raise ValueError("Thiếu biến GCP_PROJECT_ID")

    return project_id


def get_dataset_id():
    """
    Lấy Dataset BigQuery.
    """

    dataset_id = os.getenv("BIGQUERY_DATASET")

    if not dataset_id:
        raise ValueError("Thiếu biến BIGQUERY_DATASET")

    return dataset_id
