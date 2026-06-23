import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)

if project_root not in sys.path:
    sys.path.append(project_root)


# EXTRACTORS
from extractors.shopify_extractor import Shopify_Extraction
from extractors.payment_extractor import Payment_Extractor
from extractors.product_extractor import productExtractor
from extractors.customer_extractor import customer_Extractor
from extractors.online_extractor import OnlineorderExtractor
from extractors.tracking_extractor import Tracking_Extraction

# TRANSFORMERS
from transformers.base_transformer import BaseTransformer
from transformers.dimension_transformer import DimTransformer
from transformers.fact_transformer import FactTransformer

BUCKET = "minpy"


# BASE TRANSFORMER
def test_base_transformer():

    print("\n" + "=" * 60)
    print("TEST BASE TRANSFORMER")
    print("=" * 60)

    payment = Payment_Extractor(BUCKET)

    momo_df = payment.payment_momo_extract()

    transformer = BaseTransformer()

    print("\nRaw Data")
    print(momo_df.head())

    transformed_df = transformer.convert_data_types(
        momo_df, {"responseTimeISO": "datetime"}
    )

    transformed_df = transformer.create_date_key(
        transformed_df, "responseTimeISO", "payment_date_key"
    )

    print("\nAfter Date Key")
    print(transformed_df[["responseTimeISO", "payment_date_key"]].head())


# DIMENSIONS


def test_dimension_transformer():

    print("\n" + "=" * 60)
    print("TEST DIMENSION TRANSFORMER")
    print("=" * 60)

    dim = DimTransformer()

    # PRODUCT
    product = productExtractor(BUCKET)

    product_df = product.extract_file()

    dim_product = dim.create_dim_product(product_df)

    print("\nDIM PRODUCT")

    print(dim_product.head())

    print(dim_product.info())

    # CUSTOMER
    customer = customer_Extractor(BUCKET)

    customer_df = customer.extract_file()

    dim_customer = dim.create_dim_customer(customer_df)

    print("\nDIM CUSTOMER")

    print(dim_customer.head())

    print(dim_customer.info())


# FACTS
def test_fact_transformer():

    print("\n" + "=" * 60)
    print("TEST FACT TRANSFORMER")
    print("=" * 60)

    fact = FactTransformer()

    # # FACT ORDERS
    # shopify = Shopify_Extraction(BUCKET)
    # online = OnlineorderExtractor(BUCKET)

    # shopify_df = shopify.extract_all_shopify_data()

    # online_df = online.extract_file()

    # fact_shopify_orders = fact.fact_shopify_orders(shopify_df)

    # fact_online_orders = fact.fact_online_orders(online_df)

    # fact_orders = fact.create_fact_orders(fact_shopify_orders, fact_online_orders)

    # print("\nFACT ORDERS")

    # print(fact_orders.head())

    # print(fact_orders.info())

    # print(fact_orders.shape)

    # # FACT ORDER ITEMS
    # fact_shopify_order_items = fact.fact_shopify_order_items(
    #     shopify_df,
    #     fact_shopify_orders,
    # )

    # fact_online_order_items = fact.fact_online_order_items(
    #     online_df,
    #     fact_online_orders,
    # )

    # fact_order_items = fact.create_fact_order_items(
    #     fact_shopify_order_items,
    #     fact_online_order_items,
    # )

    # print("\nFACT ORDER ITEMS")

    # print(fact_order_items.head())

    # print(fact_order_items.info())

    # print(fact_order_items[["order_key", "order_item_key"]])

    # FACT PAYMENTS
    payment = Payment_Extractor(BUCKET)

    momo_df = payment.payment_momo_extract()

    paypal_df = payment.payment_paypal_extract()

    zalopay_df = payment.payment_zalopay_extract()

    fact_momo = fact.create_momo_payment(momo_df)

    fact_paypal = fact.create_payment_paypal(paypal_df)

    fact_zalopay = fact.create_zalopay_payment(zalopay_df)

    fact_payments = fact.create_fact_payments(
        fact_momo,
        fact_paypal,
        fact_zalopay,
    )

    print("\nFACT PAYMENTS")

    # print(fact_payments.head())

    print(fact_payments.info())

    # # FACT CART EVENTS
    # tracking = Tracking_Extraction(BUCKET)

    # tracking_df = tracking.extract_files_tracking()

    # fact_cart_events = fact.create_fact_cart_events(tracking_df)

    # print("\nFACT CART EVENTS")

    # print(fact_cart_events.head())

    # print(fact_cart_events.info())


if __name__ == "__main__":

    test_base_transformer()
    test_dimension_transformer()
    test_fact_transformer()

    print("\nALL TRANSFORMER TESTS COMPLETED")
