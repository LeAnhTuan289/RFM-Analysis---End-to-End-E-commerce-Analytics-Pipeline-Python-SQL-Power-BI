import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
import pandas as pd
from extractors.base_extractors import BaseExtractor


class customer_Extractor(BaseExtractor):
    def __init__(self, bucket_name):
        super().__init__(bucket_name)

    def extract_file(self):
        list_file_extract = self.list_files("shared/customers")
        logging.info(f"Found files: {list_file_extract}")

        data_extract = []
        for i in list_file_extract:
            data = self.extract_json_file(i)
            if isinstance(data, list):
                data_extract.extend(data)
            elif isinstance(data, dict):
                data_extract.append(data)

        df = pd.DataFrame(data_extract)
        logging.info(f"Extracted {len(df)} rows")
        return df
