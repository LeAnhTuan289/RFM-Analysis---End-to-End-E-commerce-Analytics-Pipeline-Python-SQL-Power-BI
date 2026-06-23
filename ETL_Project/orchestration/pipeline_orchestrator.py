"""
ETL Pipeline Orchestrator
1. Extract  →  2. Transform Dims  →  3. Transform Facts
            →  4. Load Dims       →  5. Load Facts
            →  6. Update Aggregates  →  7. Validate
"""

import sys
import os
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
import traceback

from loaders.bigquery_loader import BigQueryLoader
from transformers.dimension_transformer import DimTransformer
from transformers.fact_transformer import FactTransformer

from extractors.shopify_extractor import Shopify_Extraction
from extractors.product_extractor import productExtractor
from extractors.customer_extractor import customer_Extractor
from extractors.online_extractor import OnlineorderExtractor
from extractors.payment_extractor import Payment_Extractor
from extractors.tracking_extractor import Tracking_Extraction
from extractors.odoo_extractor import Odoo_Extractor
from extractors.sapo_extractor import Sapo_Extraction
from extractors.location_extractor import Location_Extractor

from utils.logger import setup_logger


class PipelineOrchestrator:
    """
    Central controller for the ETL pipeline.

    Note: Dimensions are loaded before facts to maintain star-schema dependencies.
    """

    def __init__(self):
        self.logger = setup_logger(__name__)
        self.bucket_name = "minpy"
        self.loader = BigQueryLoader()
        self.dim_transformer = DimTransformer()
        self.fact_transformer = FactTransformer()

    #  EXTRACT
    def extract(self) -> dict:
        self.logger.info("\n")
        self.logger.info("=" * 40)
        self.logger.info("\nEXTRACT")
        self.logger.info("=" * 40)

        try:
            shopify_df = Shopify_Extraction(self.bucket_name).extract_all_shopify_data()
            product_df = productExtractor(self.bucket_name).extract_file()
            customer_df = customer_Extractor(self.bucket_name).extract_file()
            online_df = OnlineorderExtractor(self.bucket_name).extract_file()
            tracking_df = Tracking_Extraction(self.bucket_name).extract_files_tracking()
            odoo_df = Odoo_Extractor(self.bucket_name).extract_file()
            sapo_df = Sapo_Extraction(self.bucket_name).extract_file_sapo()
            location_df = Location_Extractor(self.bucket_name).extract_file()

            payment = Payment_Extractor(self.bucket_name)
            momo_df = payment.payment_momo_extract()
            paypal_df = payment.payment_paypal_extract()
            zalopay_df = payment.payment_zalopay_extract()
            mercury_df = payment.payment_mercury_extract()

            raw_data = {
                "shopify": shopify_df,
                "product": product_df,
                "customer": customer_df,
                "online": online_df,
                "tracking": tracking_df,
                "momo": momo_df,
                "paypal": paypal_df,
                "zalopay": zalopay_df,
                "mercury": mercury_df,
                "odoo": odoo_df,
                "sapo": sapo_df,
                "location": location_df,
            }

            for name, df in raw_data.items():
                self.logger.info(f"  {name}: {len(df):,} rows extracted")

            self.logger.info("Extract completed")
            return raw_data

        except Exception as e:
            self.logger.exception(f"Extract failed: {e}")
            raise

    # TRANSFORM

    # Fact
    def transform_facts(self, raw_data: dict) -> dict:
        self.logger.info("\n")
        self.logger.info("=" * 40)
        self.logger.info("\nTRANSFORM FACTS")
        self.logger.info("=" * 40)

        try:
            # Orders
            fact_shopify_orders = self.fact_transformer.fact_shopify_orders(
                raw_data["shopify"]
            )
            fact_online_orders = self.fact_transformer.fact_online_orders(
                raw_data["online"]
            )
            fact_orders = self.fact_transformer.create_fact_orders(
                fact_shopify_orders, fact_online_orders
            )

            # Order Items
            fact_shopify_items = self.fact_transformer.fact_shopify_order_items(
                raw_data["shopify"], fact_shopify_orders
            )
            fact_online_items = self.fact_transformer.fact_online_order_items(
                raw_data["online"], fact_online_orders
            )
            fact_order_items = self.fact_transformer.create_fact_order_items(
                fact_shopify_items, fact_online_items
            )

            # Payments
            fact_momo = self.fact_transformer.create_momo_payment(raw_data["momo"])
            fact_paypal = self.fact_transformer.create_payment_paypal(
                raw_data["paypal"]
            )
            fact_zalopay = self.fact_transformer.create_zalopay_payment(
                raw_data["zalopay"]
            )
            fact_payments = self.fact_transformer.create_fact_payments(
                fact_momo, fact_paypal, fact_zalopay
            )

            # Cart Events
            fact_cart_events = self.fact_transformer.create_fact_cart_events(
                raw_data["tracking"]
            )

            # Transaction_bank
            fact_bank_transactions = self.fact_transformer.fact_bank_transactions(
                raw_data["mercury"]
            )

            facts = {
                "fact_orders": fact_orders,
                "fact_order_items": fact_order_items,
                "fact_payments": fact_payments,
                "fact_cart_events": fact_cart_events,
                "fact_bank_transactions": fact_bank_transactions,
            }

            for name, df in facts.items():
                self.logger.info(f"  {name}: {len(df):,} rows")

            self.logger.info("Fact transformation completed")
            return facts

        except Exception as e:
            self.logger.exception(f"Fact transformation failed: {e}")
            raise

    # Dimensions
    def transform_dimensions(
        self,
        raw_data: dict,
        facts: dict,
    ) -> dict:
        self.logger.info("\n")
        self.logger.info("=" * 40)
        self.logger.info("\nTRANSFORM DIMENSIONS")
        self.logger.info("=" * 40)

        try:
            # Dim_date
            dim_date = self.dim_transformer.create_dim_date(
                facts["fact_orders"],
                facts["fact_payments"],
                facts["fact_cart_events"],
                facts["fact_bank_transactions"],
            )

            dimensions = {
                "dim_product": self.dim_transformer.create_dim_product(
                    raw_data["product"]
                ),
                "dim_customer": self.dim_transformer.create_dim_customer(
                    raw_data["customer"]
                ),
                "dim_location": self.dim_transformer.create_dim_location(
                    raw_data["location"]
                ),
                "dim_date": dim_date,
            }

            for name, df in dimensions.items():
                self.logger.info(f"  {name}: {len(df):,} rows")

            self.logger.info("Dimension transformation completed")
            return dimensions

        except Exception as e:
            self.logger.exception(f"Dimension transformation failed: {e}")
            raise

    #  LOAD

    def _load_tables(self, tables: dict, label: str) -> None:
        """Generic loader with per-table error handling."""
        self.logger.info("\n")
        self.logger.info("=" * 40)
        self.logger.info(f"LOAD {label}")
        self.logger.info("=" * 40)

        # Mapping cấu hình Partition và Clustering cho từng bảng
        table_configs = {
            "dim_customer": {
                "partition_col": "created_at",
                "cluster_cols": ["customer_id"],
            },
            "fact_orders": {
                "partition_col": "order_date",
                "cluster_cols": ["customer_id", "channel"],
            },
            "fact_order_items": {
                "partition_col": "order_date",
                "cluster_cols": ["product_id"],
            },
            "fact_payments": {
                "partition_col": "payment_date",
                "cluster_cols": ["customer_id", "payment_gateway"],
            },
            "fact_cart_events": {
                "partition_col": "event_timestamp",
                "cluster_cols": ["customer_id", "session_id", "event_type"],
            },
            "fact_bank_transactions": {
                "partition_col": "transaction_date",
                "cluster_cols": None,
            },
        }

        print(table_configs)

        for table_name, df in tables.items():
            try:
                config = table_configs.get(table_name, {})
                partition_col = config.get("partition_col")
                cluster_cols = config.get("cluster_cols")

                self.loader.load_dataframe(
                    df=df,
                    table_name=table_name,
                    write_disposition="WRITE_TRUNCATE",
                    partition_col=partition_col,    
                    cluster_cols=cluster_cols,
                )
                self.logger.info(f"  ✓ {table_name}: {len(df):,} rows loaded")
            except Exception as e:
                self.logger.error(f"  ✗ Failed to load {table_name}: {e}")
                raise

    def load_dimensions(self, dimensions: dict) -> None:
        """Load dimension tables first (star-schema requirement)."""
        self._load_tables(dimensions, "DIMENSIONS")

    def load_facts(self, facts: dict) -> None:
        """Load fact tables after all dimensions are ready."""
        self._load_tables(facts, "FACTS")

    # AGGREGATES

    def update_aggregates(self, dimensions: dict, facts: dict) -> None:
        """
        Refresh aggregate metrics on dimension tables.
        """

        self.logger.info("\n")
        self.logger.info("=" * 40)
        self.logger.info("UPDATE AGGREGATES")
        self.logger.info("=" * 40)

        pid = self.loader.project_id
        did = self.loader.dataset_id

        # 1. Cập nhật dim_customer (RFM) bằng BigQuery MERGE với NTILE(5)
        try:
            self.logger.info("  Updating dim_customer with RFM segments via BigQuery MERGE ...")
            merge_query = f"""
                MERGE `{pid}.{did}.dim_customer` AS target
                USING (
                    WITH aggregate_value AS (
                        -- Tính các chỉ số tổng hợp từ fact_orders
                        SELECT
                            customer_id,
                            MIN(order_date)            AS first_order_date,
                            MAX(order_date)            AS last_order_date,
                            COUNT(DISTINCT order_key)  AS total_orders,
                            SUM(total_vnd)             AS life_time_value_vnd
                        FROM `{pid}.{did}.fact_orders`
                        WHERE payment_status IN ('paid', 'partially_paid')
                          AND status IN ('completed', 'shipping', 'delivered',
                                         'fulfilled', 'pending')
                        GROUP BY customer_id
                    ),

                    rfm_score AS (
                        -- Tính điểm RFM bằng NTILE(5) trên toàn bộ tập khách hàng
                        SELECT
                            customer_id,
                            last_order_date            AS recency,
                            total_orders               AS frequency,
                            life_time_value_vnd        AS monetary,
                            NTILE(5) OVER (ORDER BY last_order_date)        AS r_score,
                            NTILE(5) OVER (ORDER BY total_orders)           AS f_score,
                            NTILE(5) OVER (ORDER BY life_time_value_vnd)    AS m_score,
                            CONCAT(
                                CAST(NTILE(5) OVER (ORDER BY last_order_date)     AS STRING),
                                CAST(NTILE(5) OVER (ORDER BY total_orders)        AS STRING),
                                CAST(NTILE(5) OVER (ORDER BY life_time_value_vnd) AS STRING)
                            ) AS rfm_cell
                        FROM aggregate_value
                    ),

                    rfm_segment AS (
                        -- Phân loại khách hàng theo rfm_cell
                        SELECT
                            r.customer_id,
                            a.first_order_date,
                            a.last_order_date,
                            a.total_orders,
                            a.life_time_value_vnd,
                            CASE
                                -- VIP / Best Customers: Champions + Loyal + Cannot Lose Them
                                WHEN rfm_cell IN ('555','554','544','545','454','455','445',
                                                  '543','444','435','355','354','345','344','335',
                                                  '155','154','144','214','215','115','114','113')
                                    THEN 'VIP / Best Customers'

                                -- Growing / Potential: Potential Loyalist + New Customer + Promising
                                WHEN rfm_cell IN ('553','551','552','541','542','533','532','531',
                                                  '452','451','442','441','431','453','433','432',
                                                  '423','353','352','351','342','341','333','323',
                                                  '512','511','422','421','412','411','311',
                                                  '525','524','523','522','521','515','514','513',
                                                  '425','424','413','414','415','315','314','313')
                                    THEN 'Growing / Potential'

                                -- Needs Attention: Need Attention + About To Sleep
                                WHEN rfm_cell IN ('535','534','443','434','343','334','325','324',
                                                  '331','321','312','221','213','231','241','251')
                                    THEN 'Needs Attention'

                                -- At Risk
                                WHEN rfm_cell IN ('255','254','245','244','253','252','243','242',
                                                  '235','234','225','224','153','152','145','143',
                                                  '142','135','134','133','125','124')
                                    THEN 'At Risk'

                                -- Lost / Inactive: Hibernating + Lost
                                WHEN rfm_cell IN ('332','322','233','232','223','222','132','123',
                                                  '122','212','211',
                                                  '111','112','121','131','141','151')
                                    THEN 'Lost / Inactive'

                                ELSE 'Unknown'
                            END AS segment
                        FROM rfm_score r
                        LEFT JOIN aggregate_value a
                            ON r.customer_id = a.customer_id
                    )

                    SELECT *
                    FROM rfm_segment
                ) AS source

                ON target.customer_id = source.customer_id

                -- Khách có đơn hàng hợp lệ: cập nhật metrics + segment RFM
                WHEN MATCHED THEN
                    UPDATE SET
                        target.first_order_date    = source.first_order_date,
                        target.last_order_date     = source.last_order_date,
                        target.total_orders        = source.total_orders,
                        target.lifetime_value_vnd  = source.life_time_value_vnd,
                        target.customer_segment    = source.segment

                -- Khách trong dim_customer nhưng không có đơn hàng hợp lệ nào
                WHEN NOT MATCHED BY SOURCE THEN
                    UPDATE SET
                        target.customer_segment    = 'No Purchase'
            """
            self.loader.execute_query(merge_query)
            self.logger.info("  ✓ dim_customer updated with RFM segments (BigQuery MERGE)")

        except Exception as e:
            self.logger.error(f"Failed to update dim_customer aggregates: {e}")
            raise

        #  2. Cập nhật dim_product
        try:
            self.logger.info("  Fetching product aggregates from fact_order_items ...")
            prod_query = f"""
                SELECT
                    product_id,
                    COALESCE(SUM(line_total_vnd), 0.0) AS total_revenue_vnd,
                    COALESCE(SUM(quantity), 0)          AS total_quantity_sold
                FROM `{pid}.{did}.fact_order_items`
                GROUP BY product_id
            """
            prod_rows = list(self.loader.execute_query(prod_query))

            if prod_rows:
                prod_agg = pd.DataFrame(
                    [dict(row) for row in prod_rows],
                    columns=["product_id", "total_revenue_vnd", "total_quantity_sold"],
                )

                dim_prod = dimensions["dim_product"].copy()
                drop_cols = [
                    c
                    for c in ["total_revenue_vnd", "total_quantity_sold"]
                    if c in dim_prod.columns
                ]
                dim_prod = dim_prod.drop(columns=drop_cols)

                dim_prod = dim_prod.merge(prod_agg, on="product_id", how="left")
                dim_prod["total_revenue_vnd"] = dim_prod["total_revenue_vnd"].fillna(
                    0.0
                )
                dim_prod["total_quantity_sold"] = (
                    dim_prod["total_quantity_sold"].fillna(0).astype(int)
                )

                self.loader.load_dataframe(
                    df=dim_prod,
                    table_name="dim_product",
                    write_disposition="WRITE_TRUNCATE",
                    cluster_cols=["product_id"],
                )
                self.logger.info(f"  ✓ dim_product updated: {len(dim_prod):,} rows")
            else:
                self.logger.warning(
                    "  ⚠ fact_order_items returned no rows — dim_product not updated"
                )

        except Exception as e:
            self.logger.error(f"Failed to update dim_product aggregates: {e}")
            raise

        self.logger.info("Aggregates updated")

    # VALIDATE

    def validate_tables(self, tables: dict) -> None:
        """Validate loaded tables by checking row counts in BigQuery."""
        self.logger.info("\n")
        self.logger.info("=" * 40)
        self.logger.info("VALIDATION")
        self.logger.info("=" * 40)

        for table_name, df in tables.items():
            expected_rows = len(df)
            actual_rows = self.loader.get_table_row_count(table_name)

            if expected_rows == actual_rows:
                status = "✓"
            else:
                status = "⚠ MISMATCH"

            self.logger.info(
                f"  {status} {table_name}: {actual_rows:,} rows in BigQuery "
                f"(Expected: {expected_rows:,})"
            )

    #  RUN

    def run(self) -> None:
        """Execute the complete ETL pipeline."""
        start = time.time()

        try:
            self.logger.info("\n")
            self.logger.info("=" * 40)
            self.logger.info("START ETL PIPELINE")
            self.logger.info("=" * 40)

            self.loader.create_dataset_if_not_exists()

            # Extract time
            extract_start = time.time()
            raw_data = self.extract()
            self.logger.info(f"Extract finished in {time.time()-extract_start:.2f}s")

            # Fact time
            fact_start = time.time()
            facts = self.transform_facts(raw_data)
            self.logger.info(
                f"Fact transformation finished in {time.time()-fact_start:.2f}s"
            )

            # Dimension time
            dim_start = time.time()
            dimensions = self.transform_dimensions(
                raw_data=raw_data,
                facts=facts,
            )
            self.logger.info(
                f"Dimension transformation finished in {time.time()-dim_start:.2f}s"
            )

            self.load_dimensions(dimensions)

            self.load_facts(facts)

            self.update_aggregates(dimensions=dimensions, facts=facts)

            self.validate_tables(dimensions)
            self.validate_tables(facts)

            elapsed = time.time() - start
            self.logger.info("\n")
            self.logger.info("=" * 40)
            self.logger.info(f"PIPELINE COMPLETED SUCCESSFULLY ({elapsed:.1f}s)")
            self.logger.info("=" * 40)

        except Exception:
            elapsed = time.time() - start
            self.logger.error(f"PIPELINE FAILED after {elapsed:.1f}s")
            self.logger.error(traceback.format_exc())
            raise


if __name__ == "__main__":
    PipelineOrchestrator().run()
