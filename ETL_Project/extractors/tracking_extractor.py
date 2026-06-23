import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
import pandas as pd
from extractors.base_extractors import BaseExtractor


class Tracking_Extraction(BaseExtractor):
    def __init__(self, bucket_name):
        super().__init__(bucket_name)

    def extract_files_tracking(self):
        files_tracking = self.list_files("cart_tracking/")
        logging.info(f"Found files: {files_tracking}")

        data_extract_tracking = []
        for file in files_tracking:

            data = self.extract_json_file(file)

            if not data:
                continue

            if isinstance(data, list):
                data_extract_tracking.extend(data)
            elif isinstance(data, dict):
                data_extract_tracking.append(data)

        df = pd.DataFrame(data_extract_tracking)
        logging.info(f"Extracted {len(df)} rows")
        return df


# Tracking = Tracking_Extraction(bucket_name="minpy")

# df_Tracking = Tracking.extract_files_tracking()

# print(df_Tracking.info())
# print(df_Tracking["customer_id"].unique)
