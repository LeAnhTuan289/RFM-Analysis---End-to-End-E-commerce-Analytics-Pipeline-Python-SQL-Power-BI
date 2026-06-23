import os
import sys
import logging

import pandas as pd

_current_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.dirname(_current_dir)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from transformers.base_transformer import BaseTransformer


class DimTransformer(BaseTransformer):

    def __init__(self):
        super().__init__()

    def create_dim_customer(self, df: pd.DataFrame) -> pd.DataFrame:

        if df is None or df.empty:
            logging.warning("Input dataframe is empty")
            return df

        # 1 Standardize columns
        df = self.standardize_column_names(df)
        # Select + Rename columns :
        col_mapping = {
            "id": "customer_id",
            "full_name": "full_name",
            "phone": "phone",
            "city": "city",
            "country": "country",
            "created_at": "created_at",
            "total_spent_vnd": "lifetime_value_vnd",
            "total_orders": "total_orders",
        }
        selected_cols = [c for c in col_mapping.keys() if c in df.columns]

        dim_customer = df[selected_cols].copy()

        dim_customer.rename(columns=col_mapping, inplace=True)

        # Convert data types
        type_config = {"created_at": "datetime", "lifetime_value_vnd": "float"}

        dim_customer = self.convert_data_types(dim_customer, type_config)

        missing_config = {
            "full_name": {"strategy": "fill", "value": "Unknown"},
            "city": {"strategy": "fill", "value": "Unknown"},
        }

        dim_customer = self.handle_missing_values(dim_customer, missing_config)

        # handle_negative_values
        dim_customer = self.handle_negative_values(
            dim_customer,
            {
                "lifetime_value_vnd": "abs",
                "total_orders": "abs",
            },
        )

        #  Create new columns
        dim_customer["customer_segment"] = "Default"

        dim_customer["first_order_date"] = pd.NaT

        dim_customer["last_order_date"] = pd.NaT

        # Remove duplicates

        dim_customer = dim_customer.drop_duplicates(subset=["customer_id"], keep="last")

        # # Add audit columns
        dim_customer = self.add_audit_cols(dim_customer, source_system="shared")

        # Data quality check
        self.data_quality_check(
            dim_customer,
            table_name="dim_customers",
            key_columns=["customer_id"],
            date_columns=["created_at"],
            amount_columns=["lifetime_value_vnd", "total_orders"],
        )

        return dim_customer

    def create_dim_product(self, df: pd.DataFrame) -> pd.DataFrame:

        if df is None or df.empty:
            logging.warning("Input dataframe is empty")
            return df

        #  Standardize column names
        df = self.standardize_column_names(df)

        col_mapping = {
            "id": "product_id",
            "name": "product_name",
            "sku": "sku",
            "barcode": "barcode",
            "category": "category",
            "brand": "brand",
            "price_vnd": "price_vnd",
            "price_usd": "price_usd",
            "stock_quantity": "stock_quantity",
        }

        # create dim_product table
        selected_cols = [c for c in col_mapping.keys() if c in df.columns]
        dim_product = df[selected_cols].copy()

        dim_product.rename(columns=col_mapping, inplace=True)

        type_config = {"price_vnd": "float"}

        dim_product = self.convert_data_types(dim_product, type_config)

        missing_config = {
            "product_name": {"strategy": "fill", "value": "Unknown Product"},
            "category": {"strategy": "fill", "value": "Unknown"},
            "brand": {"strategy": "fill", "value": "Unknown"},
        }

        dim_product = self.handle_missing_values(dim_product, missing_config)

        # handle_negative_values
        dim_product = self.handle_negative_values(
            dim_product,
            {"price_vnd": "abs", "price_usd": "abs", "stock_quantity": "abs"},
        )

        # Remove duplicates
        dim_product = dim_product.drop_duplicates(subset=["product_id"], keep="last")

        # Add placeholders for aggregate columns to prevent EXCEPT errors in BigQuery

        # # Add audit columns
        dim_product = self.add_audit_cols(dim_product, source_system="shared")

        # Data quality check
        self.data_quality_check(
            dim_product,
            table_name="dim_product",
            key_columns=["product_id"],
            amount_columns=["price_vnd", "stock_quantity", "price_usd"],
        )

        return dim_product

    def create_dim_location(self, df: pd.DataFrame) -> pd.DataFrame:

        if df is None or df.empty:
            logging.warning("Input dataframe is empty")
            return df

        #  Standardize column names
        df = self.standardize_column_names(df)

        col_mapping = {
            "id": "location_id",
            "code": "location_code",
            "name": "location_name",
            "city": "city",
            "address": "address",
            "phone": "phone",
            "status": "is_active",
        }

        selected_cols = [c for c in col_mapping.keys() if c in df.columns]
        dim_location = df[selected_cols].copy()

        dim_location.rename(columns=col_mapping, inplace=True)

        missing_config = {
            "location_code": {"strategy": "fill", "value": "Unknown Code"},
            "location_name": {"strategy": "fill", "value": "Unknown Name"},
            "city": {"strategy": "fill", "value": "Unknown"},
            "address": {"strategy": "fill", "value": "Unknown"},
        }

        dim_location = self.handle_missing_values(dim_location, missing_config)

        dim_location = dim_location.drop_duplicates(subset=["location_id"], keep="last")

        dim_location = self.add_audit_cols(dim_location, source_system="shared")

        # Data quality check
        self.data_quality_check(
            dim_location,
            table_name="dim_location",
            key_columns=["location_id"],
        )

        return dim_location

    # DIM DATE

    def create_dim_date(
        self,
        *fact_dfs: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Create dim_date from fact tables
        """
        try:
            all_dates = []

            # EXTRACT ALL DATE COLUMNS FROM FACT TABLES
            for df in fact_dfs:

                if df is None or df.empty:
                    continue

                possible_date_cols = [
                    "order_date",
                    "payment_date",
                    "event_timestamp",
                    "transaction_date",
                ]

                for col in possible_date_cols:
                    if col not in df.columns:
                        continue
                    try:
                        dates = pd.to_datetime(df[col], errors="coerce", utc=False)

                        # Normalize timezone-aware → timezone-naive
                        if hasattr(dates.dtype, "tz") and dates.dtype.tz is not None:
                            dates = dates.dt.tz_localize(None)

                        dates = dates.dropna()

                        if dates.empty:
                            continue

                        # Filter out unreasonable dates (before 2000 or after 2030)
                        valid_mask = (dates >= pd.Timestamp("2000-01-01")) & (
                            dates <= pd.Timestamp("2030-12-31")
                        )
                        dates = dates[valid_mask]

                        if not dates.empty:
                            all_dates.extend(dates.dt.date.tolist())
                            logging.info(
                                f"create_dim_date: collected {len(dates):,} dates from column '{col}'"
                            )

                    except Exception as col_err:
                        logging.warning(
                            f"create_dim_date: skipping column '{col}' due to error: {col_err}"
                        )
                        continue

            # VALIDATION
            if not all_dates:
                logging.warning(
                    "create_dim_date: No valid dates found. "
                    "Using fallback range 2020-01-01 to 2026-12-31."
                )
                min_date = pd.Timestamp("2020-01-01").date()
                max_date = pd.Timestamp("2026-12-31").date()
            else:
                min_date = min(all_dates)
                max_date = max(all_dates)

            # CREATE DATE RANGE

            date_range = pd.date_range(
                start=min_date,
                end=max_date,
                freq="D",
            )

            dim_date = pd.DataFrame({"full_date": date_range})

            # DATE KEY
            dim_date["date_key"] = (
                dim_date["full_date"].dt.strftime("%Y%m%d").astype(int)
            )

            # YEAR / QUARTER / MONTH

            dim_date["year"] = dim_date["full_date"].dt.year

            dim_date["quarter"] = "Q" + dim_date["full_date"].dt.quarter.astype(str)

            dim_date["month"] = dim_date["full_date"].dt.month

            dim_date["month_name"] = dim_date["full_date"].dt.month_name()

            # WEEK

            dim_date["week"] = dim_date["full_date"].dt.isocalendar().week.astype(int)

            # DAY

            dim_date["day_of_month"] = dim_date["full_date"].dt.day

            # Sunday=1, Monday=2, ..., Saturday=7
            dim_date["day_of_week"] = ((dim_date["full_date"].dt.dayofweek + 1) % 7) + 1

            dim_date["day_name"] = dim_date["full_date"].dt.day_name()

            # WEEKEND
            dim_date["is_weekend"] = dim_date["day_of_week"].isin([1, 7])

            # HOLIDAY
            dim_date["is_holiday"] = False

            # FISCAL
            dim_date["fiscal_year"] = dim_date["year"]

            dim_date["fiscal_quarter"] = dim_date["quarter"]

            # FINAL SELECT
            dim_date = dim_date[
                [
                    "date_key",
                    "full_date",
                    "year",
                    "quarter",
                    "month",
                    "month_name",
                    "week",
                    "day_of_month",
                    "day_of_week",
                    "day_name",
                    "is_weekend",
                    "is_holiday",
                    "fiscal_year",
                    "fiscal_quarter",
                ]
            ].copy()

            # REMOVE DUPLICATES
            dim_date = dim_date.drop_duplicates(
                subset=["date_key"],
                keep="last",
            )

            # ADD AUDIT COLUMNS
            dim_date = self.add_audit_cols(
                dim_date,
                source_system="generated_calendar",
            )

            # DATA QUALITY CHECK
            self.data_quality_check(
                dim_date,
                table_name="dim_date",
                key_columns=["date_key"],
                date_columns=["full_date"],
            )

            logging.info(f"Created dim_date with {len(dim_date)} rows")
            return dim_date

        except Exception as e:
            logging.exception(f"Error creating dim_date: {e}")
            return pd.DataFrame()


if __name__ == "__main__":

    import os
    import sys

    current_dir = os.path.dirname(os.path.abspath(__file__))

    project_root = os.path.dirname(current_dir)

    sys.path.append(project_root)

    from extractors.shopify_extractor import Shopify_Extraction

    from extractors.online_extractor import OnlineorderExtractor

    from extractors.payment_extractor import Payment_Extractor

    from extractors.tracking_extractor import Tracking_Extraction

    from transformers.fact_transformer import FactTransformer

    bucket = "minpy"

    shopify = Shopify_Extraction(bucket)

    shopify_df = shopify.extract_all_shopify_data()

    print(shopify_df.columns.tolist())

    online = OnlineorderExtractor(bucket)

    online_df = online.extract_file()

    payment = Payment_Extractor(bucket)

    paypal_df = payment.payment_paypal_extract()

    tracking = Tracking_Extraction(bucket)

    tracking_df = tracking.extract_files_tracking()

    # # CREATE FACT TABLES
    # fact_transformer = FactTransformer()

    # fact_shopify_orders = fact_transformer.fact_shopify_orders(shopify_df)

    # fact_online_orders = fact_transformer.fact_online_orders(online_df)

    # fact_payments = fact_transformer.create_payment_paypal(paypal_df)

    # fact_cart_events = fact_transformer.create_fact_cart_events(tracking_df)

    # # CREATE DIM DATE
    # dim_transformer = DimTransformer()

    # dim_date = dim_transformer.create_dim_date(
    #     fact_shopify_orders,
    #     fact_online_orders,
    #     fact_payments,
    #     fact_cart_events,
    # )

    # print("\n========== DIM DATE INFO ==========")

    # print(dim_date.info())

    # print("\n========== DIM DATE SAMPLE ==========")

    # print(dim_date.head(10))

    # print("\n========== DIM DATE SHAPE ==========")

    # print(dim_date.shape)
