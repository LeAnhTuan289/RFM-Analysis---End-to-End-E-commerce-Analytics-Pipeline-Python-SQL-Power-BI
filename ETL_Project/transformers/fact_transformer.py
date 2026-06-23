import os
import sys
import logging
import pandas as pd

_current_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.dirname(_current_dir)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from transformers.base_transformer import BaseTransformer


class FactTransformer(BaseTransformer):
    """
    Transformer class for creating fact tables
    """

    USD_VND_RATE = 26000

    def __init__(self):
        super().__init__()

    # COMMON HELPERS
    def _reorder_columns(self, df: pd.DataFrame, first_column: str) -> pd.DataFrame:
        """
        Move a specific column to the first position
        """
        if first_column not in df.columns:
            return df

        new_cols = [first_column] + [c for c in df.columns if c != first_column]
        return df[new_cols]

    def _remove_duplicates(self, df: pd.DataFrame, subset_cols: list) -> pd.DataFrame:
        """
        Remove duplicate rows
        """

        return df.drop_duplicates(subset=subset_cols, keep="last")

    def _combine_fact_tables(self, *dfs: pd.DataFrame) -> pd.DataFrame:
        """
        Combine multiple fact tables
        """

        try:

            combined_df = pd.concat(dfs, ignore_index=True)
            logging.info(f"Combined dataframe with " f"{len(combined_df)} rows")
            return combined_df

        except Exception as e:
            logging.exception(f"Error combining fact tables: {e}")
            return pd.DataFrame()

    # FACT SHOPIFY ORDERS
    def fact_shopify_orders(self, df: pd.DataFrame) -> pd.DataFrame:

        if df is None or df.empty:
            logging.warning("Input dataframe is empty")
            return df

        try:

            col_mapping = {
                "id": "order_id",
                "transaction_id": "transaction_id",
                "customer_id": "customer_id",
                "order_date": "order_date",
                "channel": "channel",
                "source": "source",
                "fulfillment_status": "status",
                "payment_status": "payment_status",
                "total_vnd": "total_vnd",
                "total_usd": "total_usd",
            }

            selected_cols = [c for c in col_mapping.keys() if c in df.columns]

            fact_orders = df[selected_cols].copy()

            fact_orders.rename(columns=col_mapping, inplace=True)

            # Convert datatype
            fact_orders = self.convert_data_types(
                fact_orders, type_cf={"order_date": "datetime"}
            )

            # Create order_date_key
            fact_orders = self.create_date_key(
                fact_orders,
                "order_date",
                "order_date_key",
            )

            # Standardize source and channel
            fact_orders["source"] = fact_orders["source"].replace(
                to_replace="shopify", value="shopify_platform"
            )

            fact_orders["channel"] = fact_orders["channel"].replace(
                to_replace="online", value="shopify"
            )

            # Create surrogate key
            fact_orders = self.create_surrogate_key(
                fact_orders, ["channel", "order_id", "transaction_id"], "order_key"
            )

            # Reorder columns
            fact_orders = self._reorder_columns(fact_orders, "order_key")

            # handle_negative_values
            fact_orders = self.handle_negative_values(
                fact_orders, {"total_vnd": "abs", "total_usd": "abs"}
            )

            # Remove duplicates
            fact_orders = self._remove_duplicates(fact_orders, ["order_key"])

            # Ensure order_id is always string to avoid mixed-type issues when combining
            if "order_id" in fact_orders.columns:
                fact_orders["order_id"] = fact_orders["order_id"].astype(str)

            # # Add audit columns
            fact_orders = self.add_audit_cols(fact_orders, source_system="shopify")

            # Data quality check
            self.data_quality_check(
                fact_orders,
                table_name="fact_shopify_orders",
                key_columns=["order_key"],
                date_columns=["order_date"],
                amount_columns=["total_vnd", "total_usd"],
            )

            logging.info(
                f"Created fact_shopify_orders " f"with {len(fact_orders)} rows"
            )

            return fact_orders

        except Exception as e:
            logging.exception(f"Error creating fact_shopify_orders: {e}")
            return pd.DataFrame()

    # FACT ONLINE ORDERS
    def fact_online_orders(self, df: pd.DataFrame) -> pd.DataFrame:

        if df is None or df.empty:
            logging.warning("Input dataframe is empty")
            return df

        try:

            col_mapping = {
                "order_id": "order_id",
                "transaction_id": "transaction_id",
                "customer_id": "customer_id",
                "created_at": "order_date",
                "channel": "channel",
                "source": "source",
                "status": "status",
                "payment_status": "payment_status",
                "total": "total_vnd",
            }

            selected_cols = [c for c in col_mapping.keys() if c in df.columns]

            fact_orders = df[selected_cols].copy()

            fact_orders.rename(columns=col_mapping, inplace=True)

            # Convert datatype
            fact_orders = self.convert_data_types(
                fact_orders,
                type_cf={
                    "order_date": "datetime",
                    "total_vnd": "float",
                },
            )

            # Create order_date_key
            fact_orders = self.create_date_key(
                fact_orders,
                "order_date",
                "order_date_key",
            )

            # Create total_usd
            fact_orders["total_usd"] = round(
                (fact_orders["total_vnd"] / self.USD_VND_RATE), 2
            )

            # Create surrogate key
            fact_orders = self.create_surrogate_key(
                fact_orders, ["channel", "order_id", "transaction_id"], "order_key"
            )

            # Reorder columns
            fact_orders = self._reorder_columns(fact_orders, "order_key")

            # handle_negative_values
            fact_orders = self.handle_negative_values(
                fact_orders, {"total_vnd": "abs", "total_usd": "abs"}
            )

            # Remove duplicates
            fact_orders = self._remove_duplicates(fact_orders, ["order_key"])

            # Ensure order_id is always string to avoid mixed-type issues when combining
            if "order_id" in fact_orders.columns:
                fact_orders["order_id"] = fact_orders["order_id"].astype(str)

            # # Add audit columns
            fact_orders = self.add_audit_cols(
                fact_orders, source_system="online_orders"
            )

            # Data quality check
            self.data_quality_check(
                fact_orders,
                table_name="fact_online_orders",
                key_columns=["order_key"],
                date_columns=["order_date"],
                amount_columns=["total_vnd", "total_usd"],
            )

            logging.info(f"Created fact_online_orders " f"with {len(fact_orders)} rows")
            return fact_orders

        except Exception as e:
            logging.exception(f"Error creating fact_online_orders: {e}")
            return pd.DataFrame()

    # COMBINE FACT ORDERS
    def create_fact_orders(self, *dfs: pd.DataFrame) -> pd.DataFrame:
        return self._combine_fact_tables(*dfs)

    # COMMON ORDER ITEMS FACT
    def _create_order_items_fact(
        self,
        source_df: pd.DataFrame,
        fact_orders: pd.DataFrame,
        source_system: str,
        price_column: str,
    ) -> pd.DataFrame:

        try:

            # Select columns
            order_items = source_df[["transaction_id", "line_items"]].copy()

            # Explode nested JSON
            order_items = self.explode_json_column(
                order_items, explode_col="line_items"
            )

            if order_items.empty:
                logging.warning(f"No order items found " f"for {source_system}")
                return pd.DataFrame()

            # Merge order_key and order_date
            order_items = order_items.merge(
                fact_orders[
                    [
                        "order_key",
                        "transaction_id",
                        "order_date",
                        "order_date_key",
                    ]
                ],
                on="transaction_id",
                how="left",
            )

            # Rename columns
            order_items.rename(columns={price_column: "unit_price_vnd"}, inplace=True)

            # Calculate line_total
            order_items["line_total_vnd"] = (
                order_items["quantity"] * order_items["unit_price_vnd"]
            )

            # Final select
            fact_order_items = order_items[
                [
                    "order_key",
                    "transaction_id",
                    "order_date",
                    "order_date_key",
                    "product_id",
                    "product_name",
                    "quantity",
                    "unit_price_vnd",
                    "line_total_vnd",
                ]
            ].copy()

            # Create surrogate key
            fact_order_items = self.create_surrogate_key(
                fact_order_items,
                ["order_key", "transaction_id", "product_id", "order_date_key"],
                "order_item_key",
            )

            # handle mising value
            fact_order_items = self.handle_missing_values(
                fact_order_items,
                missing_config={
                    "product_id": {"strategy": "fill", "value": -1},
                },
            )

            # Reorder columns
            fact_order_items = self._reorder_columns(fact_order_items, "order_item_key")

            # handle_negative_values
            fact_order_items = self.handle_negative_values(
                fact_order_items,
                {"quantity": "abs", "unit_price_vnd": "abs", "line_total_vnd": "abs"},
            )

            # Remove duplicates
            fact_order_items = self._remove_duplicates(
                fact_order_items, ["order_item_key"]
            )

            # # Add audit columns
            fact_order_items = self.add_audit_cols(
                fact_order_items, source_system=source_system
            )

            # Data quality check
            self.data_quality_check(
                fact_order_items,
                table_name=f"fact_{source_system}_order_items",
                key_columns=["order_item_key"],
                date_columns=["order_date"],
                amount_columns=["quantity", "unit_price_vnd", "line_total_vnd"],
            )

            logging.info(
                f"Created fact_{source_system}_order_items "
                f"with {len(fact_order_items)} rows"
            )

            return fact_order_items

        except Exception as e:
            logging.exception(
                f"Error creating " f"fact_{source_system}_order_items: {e}"
            )
            return pd.DataFrame()

    # FACT SHOPIFY ORDER ITEMS
    def fact_shopify_order_items(
        self, shopify_df: pd.DataFrame, fact_orders: pd.DataFrame
    ) -> pd.DataFrame:
        if shopify_df is None or shopify_df.empty:
            logging.warning("Input dataframe is empty")
            return shopify_df

        return self._create_order_items_fact(
            source_df=shopify_df,
            fact_orders=fact_orders,
            source_system="shopify",
            price_column="price_vnd",
        )

    # FACT ONLINE ORDER ITEMS
    def fact_online_order_items(
        self, online_df: pd.DataFrame, fact_orders: pd.DataFrame
    ) -> pd.DataFrame:

        if online_df is None or online_df.empty:
            logging.warning("Input dataframe is empty")
            return online_df

        return self._create_order_items_fact(
            source_df=online_df,
            fact_orders=fact_orders,
            source_system="online_orders",
            price_column="unit_price",
        )

    # COMBINE FACT ORDER ITEMS
    def create_fact_order_items(self, *dfs: pd.DataFrame) -> pd.DataFrame:
        return self._combine_fact_tables(*dfs)

    # COMMON PAYMENT FACT
    def _create_payment_fact(
        self,
        df: pd.DataFrame,
        col_mapping: dict,
        source_system: str,
        payment_method: str = None,
    ) -> pd.DataFrame:

        if df is None or df.empty:
            logging.warning("Input dataframe is empty")
            return pd.DataFrame()

        try:

            selected_cols = [c for c in col_mapping.keys() if c in df.columns]

            fact_payment = df[selected_cols].copy()

            fact_payment.rename(columns=col_mapping, inplace=True)

            # Add payment method if needed
            if payment_method:
                fact_payment["payment_method"] = payment_method

            # Ensure amount_vnd is always float64 to avoid INT64 vs FLOAT64
            # type conflict in BigQuery when multiple payment sources are combined.
            if "amount_vnd" in fact_payment.columns:
                fact_payment["amount_vnd"] = fact_payment["amount_vnd"].astype(
                    "float64"
                )

            # Convert datatype
            fact_payment = self.convert_data_types(
                fact_payment, type_cf={"payment_date": "datetime"}
            )

            # Create payment_date_key
            fact_payment = self.create_date_key(
                fact_payment,
                "payment_date",
                "payment_date_key",
            )

            # Create surrogate key
            fact_payment = self.create_surrogate_key(
                fact_payment, ["payment_gateway", "transaction_id"], "payment_key"
            )

            # Reorder columns
            fact_payment = self._reorder_columns(fact_payment, "payment_key")

            # handle_negative_values
            fact_payment = self.handle_negative_values(
                fact_payment,
                {"amount_vnd": "allow"},
            )

            # Remove duplicates
            fact_payment = self._remove_duplicates(fact_payment, ["payment_key"])

            # # Add audit columns
            fact_payment = self.add_audit_cols(
                fact_payment, source_system=source_system
            )

            # Data quality check
            self.data_quality_check(
                fact_payment,
                table_name=f"fact_payment_{source_system}",
                key_columns=["payment_key"],
                date_columns=["payment_date"],
                allow_negative_amounts=["amount_vnd"],
            )

            logging.info(
                f"Created fact_payment_{source_system} "
                f"with {len(fact_payment)} rows"
            )

            return fact_payment

        except Exception as e:
            logging.exception(
                f"Error creating payment fact " f"for {source_system}: {e}"
            )
            return pd.DataFrame()

    # PAYPAL PAYMENT
    def create_payment_paypal(self, df: pd.DataFrame) -> pd.DataFrame:

        if df is None or df.empty:
            logging.warning("Input dataframe is empty")
            return df

        col_mapping = {
            "transaction_id": "transaction_id",
            "invoice_id": "order_id",
            "customer_id": "customer_id",
            "source": "payment_gateway",
            "transaction_amount_vnd": "amount_vnd",
            "transaction_status": "payment_status",
            "transaction_initiation_date": "payment_date",
        }

        return self._create_payment_fact(
            df=df,
            col_mapping=col_mapping,
            source_system="paypal",
            payment_method="e-wallet",
        )

    # MOMO PAYMENT
    def create_momo_payment(self, df: pd.DataFrame) -> pd.DataFrame:

        if df is None or df.empty:
            logging.warning("Input dataframe is empty")
            return df

        col_mapping = {
            "transaction_id": "transaction_id",
            "orderId": "order_id",
            "customer_id": "customer_id",
            "source": "payment_gateway",
            "amount": "amount_vnd",
            "message": "payment_status",
            "responseTimeISO": "payment_date",
            "payType": "payment_method",
        }

        return self._create_payment_fact(
            df=df, col_mapping=col_mapping, source_system="momo"
        )

    # ZALOPAY PAYMENT
    def create_zalopay_payment(self, df: pd.DataFrame) -> pd.DataFrame:

        if df is None or df.empty:
            logging.warning("Input dataframe is empty")
            return df

        try:

            col_mapping = {
                "transaction_id": "transaction_id",
                "description": "order_id",
                "customer_id": "customer_id",
                "source": "payment_gateway",
                "amount": "amount_vnd",
                "return_message": "payment_status",
                "app_time": "payment_date",
            }

            fact_payment = self._create_payment_fact(
                df=df,
                col_mapping=col_mapping,
                source_system="zalopay",
                payment_method="e-wallet",
            )

            # Extract order_id
            fact_payment["order_id"] = (
                fact_payment["order_id"].astype(str).str.extract(r"#(.*)", expand=False)
            )

            return fact_payment

        except Exception as e:
            logging.exception(f"Error creating zalopay payment: {e}")
            return pd.DataFrame()

    # COMBINE FACT PAYMENTS
    def create_fact_payments(self, *dfs: pd.DataFrame) -> pd.DataFrame:

        return self._combine_fact_tables(*dfs)

    # FACT CART EVENTS
    def create_fact_cart_events(self, df: pd.DataFrame) -> pd.DataFrame:

        if df is None or df.empty:
            logging.warning("Input dataframe is empty")
            return df

        try:

            col_mapping = {
                "event_id": "event_id",
                "session_id": "session_id",
                "customer_id": "customer_id",
                "event_type": "event_type",
                "timestamp": "event_timestamp",
                "product_id": "product_id",
                "source": "source",
                "device": "device",
                "utm_source": "utm_source",
                "utm_campaign": "utm_campaign",
            }

            selected_cols = [c for c in col_mapping.keys() if c in df.columns]

            fact_cart_events = df[selected_cols].copy()

            fact_cart_events.rename(columns=col_mapping, inplace=True)

            # Convert datatype
            fact_cart_events = self.convert_data_types(
                fact_cart_events,
                type_cf={
                    "event_timestamp": "datetime",
                    "customer_id": "int",
                    "product_id": "int",
                },
            )

            # Create event_date_key
            fact_cart_events = self.create_date_key(
                fact_cart_events,
                "event_timestamp",
                "event_date_key",
            )

            # Handle missing values
            missing_config = {
                "customer_id": {"strategy": "fill", "value": -1},
                "product_id": {"strategy": "fill", "value": -1},
                "utm_source": {"strategy": "fill", "value": "unidentified"},
                "utm_campaign": {"strategy": "fill", "value": "unidentified"},
            }

            fact_cart_events = self.handle_missing_values(
                fact_cart_events, missing_config=missing_config
            )

            # Create surrogate key
            fact_cart_events = self.create_surrogate_key(
                fact_cart_events, ["event_id", "session_id", "event_type"], "event_key"
            )

            # Reorder columns
            fact_cart_events = self._reorder_columns(fact_cart_events, "event_key")

            # Remove duplicates
            fact_cart_events = self._remove_duplicates(fact_cart_events, ["event_key"])

            # # Add audit columns
            fact_cart_events = self.add_audit_cols(
                fact_cart_events, source_system="cart_tracking"
            )

            # Data quality check
            self.data_quality_check(
                fact_cart_events,
                table_name="fact_cart_events",
                key_columns=["event_key"],
                date_columns=["event_timestamp"],
            )

            logging.info(
                f"Created fact_cart_events " f"with {len(fact_cart_events)} rows"
            )

            return fact_cart_events

        except Exception as e:
            logging.exception(f"Error creating fact_cart_events: {e}")
            return pd.DataFrame()

    # FACT BANK TRANSACTIONS
    def fact_bank_transactions(
        self,
        df: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Create  bank transaction fact table
        """

        try:

            if df is None or df.empty:
                logging.warning("Input dataframe is empty")
                return df

            col_mapping = {
                "transaction_id": "transaction_id",
                "accountId": "account_id",
                "kind": "transaction_type",
                "amount_vnd": "amount_vnd",
                "status": "status",
                "createdAt": "transaction_date",
                "source": "source",
            }

            selected_cols = [col for col in col_mapping.keys() if col in df.columns]

            fact_df = df[selected_cols].copy()

            fact_df.rename(
                columns=col_mapping,
                inplace=True,
            )

            # Ensure amount_vnd is always float64 to match fact_payments schema.
            if "amount_vnd" in fact_df.columns:
                fact_df["amount_vnd"] = fact_df["amount_vnd"].astype("float64")

            # Datatype conversion
            fact_df = self.convert_data_types(
                fact_df,
                type_cf={
                    "transaction_date": "datetime",
                },
            )

            # Date key
            fact_df = self.create_date_key(
                fact_df, "transaction_date", "transaction_date_key"
            )
            fact_df = self.create_surrogate_key(
                fact_df,
                [
                    "source",
                    "transaction_id",
                ],
                "transaction_key",
            )

            fact_df = self._reorder_columns(
                fact_df,
                "transaction_key",
            )

            fact_df = self._remove_duplicates(
                fact_df,
                ["transaction_key"],
            )

            # Audit columns
            fact_df = self.add_audit_cols(
                fact_df,
                source_system="mercury",
            )

            self.data_quality_check(
                fact_df,
                table_name="fact_bank_transactions",
                key_columns=["transaction_key"],
                date_columns=["transaction_date"],
                allow_negative_amounts=["amount_vnd"],
            )

            logging.info(f"Created fact_bank_transactions " f"with {len(fact_df)} rows")

            return fact_df

        except Exception as e:

            logging.exception(f"Error creating fact_bank_transactions: {e}")

            return pd.DataFrame()
