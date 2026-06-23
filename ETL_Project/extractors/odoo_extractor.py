import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
import pandas as pd
from extractors.base_extractors import BaseExtractor


class Odoo_Extractor(BaseExtractor):
    def __init__(self, bucket_name):
        super().__init__(bucket_name)

    def extract_file(self):
        list_file_extract = self.list_files("odoo/transactions")
        logging.info(f"Found files: {list_file_extract}")

        data_extract_odoo = []
        for i in list_file_extract:
            data = self.extract_json_file(i)
            if isinstance(data, list):
                data_extract_odoo.extend(data)
            elif isinstance(data, dict):
                data_extract_odoo.append(data)

        df = pd.DataFrame(data_extract_odoo)
        logging.info(f"Extracted {len(df)} rows")
        return df


# Odoo = Odoo_Extractor(bucket_name="minpy")

# df = Odoo.extract_file()

# print(df.info())

# for col in df.columns:
#     print(f"Cột: {col}")
#     print(df[col].head(10).tolist())
