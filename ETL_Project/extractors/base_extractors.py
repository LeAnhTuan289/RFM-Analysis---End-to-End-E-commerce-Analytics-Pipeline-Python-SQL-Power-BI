from google.cloud import storage
import gzip
import json
import os
from dotenv import load_dotenv
import logging
import pandas as pd


class BaseExtractor:
    """ """

    def __init__(self, bucket_name: str):
        try:
            # Load .env từ thư mục gốc project
            env_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"
            )
            load_dotenv(env_path)
            self.client = storage.Client()
            self.bucket = self.client.bucket(bucket_name)
        except Exception as e:
            logging.critical(f"Failed to initialize GCS Client: {e}")
            raise ConnectionError(f"Could not connect to bucket {bucket_name}")

    def extract_json_file(self, blob_path: str):
        try:
            blob = self.bucket.blob(blob_path)

            # Download as type
            compressed_data = blob.download_as_bytes()
            decompressed_data = gzip.decompress(compressed_data)

            # Parse JSON
            data = json.loads(decompressed_data.decode("utf-8"))
            logging.info(f"Đã giải nén thành công file: {blob_path}")
            return data
        except Exception as e:
            logging.error(f"Error extracting file {blob_path}: {e}")
            return None

    def list_files(self, folder_name):
        """
        Lấy tất cả file có tên bắt đầu bằng folder_name và kết thúc bằng .json.gz
        """
        try:
            blobs = self.bucket.list_blobs(prefix=folder_name)
            file_paths = [blob.name for blob in blobs if blob.name.endswith(".json.gz")]
            return file_paths
        except Exception as e:
            logging.error(f"Error occurred while fetching file paths: {e}")
            return []
