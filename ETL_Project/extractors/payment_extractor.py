import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
import pandas as pd
from extractors.base_extractors import BaseExtractor


class Payment_Extractor(BaseExtractor):
    def __init__(self, bucket_name):
        super().__init__(bucket_name)

    def _extract_standard_payment(self, folder_path):
        list_file_extract = self.list_files(folder_path)
        logging.info(f"Found files in {folder_path}: {list_file_extract}")

        data_extract = []
        for i in list_file_extract:
            data = self.extract_json_file(i)
            if data is None:
                continue

            if isinstance(data, list):
                data_extract.extend(data)
            elif isinstance(data, dict):
                data_extract.append(data)

        return pd.DataFrame(data_extract)

    def payment_momo_extract(self):
        return self._extract_standard_payment("momo/")

    def payment_paypal_extract(self):
        return self._extract_standard_payment("paypal/")

    def payment_zalopay_extract(self):
        return self._extract_standard_payment("zalopay/")

    def payment_mercury_extract(self):
        return self._extract_standard_payment("mercury/")


# Paypal = Payment_Extractor(bucket_name="minpy")

# df = Paypal.payment_paypal_extract()

# print(df.info())
# print(df["source"].unique)

# Momo = Payment_Extractor(bucket_name="minpy")

# df = Momo.payment_momo_extract()

# print(df.info())
# # print(df["source"].unique)

# ZaloPay = Payment_Extractor(bucket_name="minpy")

# df = ZaloPay.payment_zalopay_extract()

# print(df.info())
# print(df["description"].unique)

# mercury = Payment_Extractor(bucket_name="minpy")

# df = mercury.payment_mercury_extract()

# print(df.info())
