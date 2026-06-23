import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
from extractors.base_extractors import BaseExtractor


class Shopify_Extraction(BaseExtractor):
    def __init__(self, bucket_name):
        super().__init__(bucket_name)

    def extract_all_shopify_data(self):
        data_extract = []
        files_shopify = self.list_files("shopify/")
        logging.info(f"Found files: {files_shopify}")

        for file in files_shopify:
            data = self.extract_json_file(file)

            if not data:
                continue

            if isinstance(data, list):
                data_extract.extend(data)
            elif isinstance(data, dict):
                data_extract.append(data)

        df = pd.DataFrame(data_extract)

        logging.info(f"Extracted {len(df)} rows")

        return df
