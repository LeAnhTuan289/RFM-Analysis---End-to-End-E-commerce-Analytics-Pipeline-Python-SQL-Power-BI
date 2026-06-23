import os
import sys

# Tự động tìm đường dẫn gốc project và thêm vào hệ thống
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(project_root)

import pandas as pd
from extractors.shopify_extractor import Shopify_Extraction
from extractors.payment_extractor import Payment_Extractor
from extractors.product_extractor import productExtractor
from extractors.customer_extractor import customer_Extractor
from extractors.online_extractor import OnlineorderExtractor
from extractors.tracking_extractor import Tracking_Extraction
from extractors.location_extractor import Location_Extractor

pd.set_option("display.max_columns", None)
pd.set_option("display.width", 1000)


bucket = "minpy"

# product = productExtractor(bucket)
# product_data = product.extract_file()


# print(product_data.head(50))
# print(product_data.info())

# location = Location_Extractor(bucket)
# location_data = location.extract_file()

# print(location_data.info())
# print(location_data["modified_on"].unique)


# online = OnlineorderExtractor(bucket)
# online_data = online.extract_file()

# print(online_data.info())

# shopify_order = Shopify_Extraction(bucket)
# shopify_order_df = shopify_order.extract_all_shopify_data()
# print(shopify_order_df.info())
# print(shopify_order_df["line_items"][0])

bank = Payment_Extractor(bucket)
bank_data = bank.payment_mercury_extract()

print(bank_data.info())
print(bank_data["details"][5])
