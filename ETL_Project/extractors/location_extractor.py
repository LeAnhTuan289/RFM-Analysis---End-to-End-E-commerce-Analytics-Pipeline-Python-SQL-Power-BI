import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
import pandas as pd
from extractors.base_extractors import BaseExtractor


class Location_Extractor(BaseExtractor):
    def __init__(self, bucket_name):
        super().__init__(bucket_name)

    def extract_file(self):
        list_file_in_shared = self.list_files("shared/")
        target_file = [
            f for f in list_file_in_shared if "sapo_locations" in f and "json.gz" in f
        ]
        logging.info(f"Found files: {target_file}")

        data_extract_products = []
        for i in target_file:
            data = self.extract_json_file(i)
            if isinstance(data, list):
                data_extract_products.extend(data)
            elif isinstance(data, dict):
                data_extract_products.append(data)

        df = pd.DataFrame(data_extract_products)
        logging.info(f"Extracted {len(df)} rows")
        return df


# Location = Location_Extractor(bucket_name="minpy")

# df = Location.extract_file()

# print(df.info())
# print(df.head(5))
