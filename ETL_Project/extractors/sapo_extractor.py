import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
import pandas as pd
from extractors.base_extractors import BaseExtractor


class Sapo_Extraction(BaseExtractor):
    def __init__(self, bucket_name):
        super().__init__(bucket_name)

    def extract_file_sapo(self):
        data_extract_sapo = []
        files_sapo = self.list_files("sapo/transactions")
        logging.info(f"Found files: {files_sapo}")

        for file in files_sapo:
            data = self.extract_json_file(file)

            if not data:
                continue

            if isinstance(data, list):
                data_extract_sapo.extend(data)
            elif isinstance(data, dict):
                data_extract_sapo.append(data)

        df = pd.DataFrame(data_extract_sapo)
        logging.info(f"Extracted {len(df)} rows")
        return df


# Sappo = Sapo_Extraction(bucket_name="minpy")

# df = Sappo.extract_file_sapo()

# print(df.info())

# for col in df.columns:
#     print(f"Cột: {col}")
#     print(df[col].head(10).tolist())
