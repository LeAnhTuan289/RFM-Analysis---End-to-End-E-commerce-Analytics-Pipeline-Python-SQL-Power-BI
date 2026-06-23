from google.cloud import bigquery
from google.cloud.exceptions import NotFound
from google.oauth2 import service_account
import os
from dotenv import load_dotenv
import pandas as pd
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.logger import setup_logger


class BigQueryLoader:
    """
    BigQuery Loader

    Features
    --------
    - Create dataset if not exists
    - Load dataframe to BigQuery
    - Execute query
    - Table validation
    """

    def __init__(self):

        self.logger = setup_logger(__name__)
        env_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"
        )
        load_dotenv(env_path)

        # Read BigQuery configuration from environment variables
        # to avoid hard-coding sensitive information.
        self.project_id = os.getenv("GCP_PROJECT_ID")
        self.dataset_id = os.getenv("BIGQUERY_DATASET")
        key_path = os.getenv("BIGQUERY_KEY_PATH")

        if not all(
            [
                self.project_id,
                self.dataset_id,
                key_path,
            ]
        ):
            raise ValueError("Missing required environment variables.")

        # Authenticate using Service Account credentials
        credentials = service_account.Credentials.from_service_account_file(key_path)

        # Create BigQuery client for all subsequent operations
        self.client = bigquery.Client(
            project=self.project_id,
            credentials=credentials,
        )

        self.logger.info(f"Connected to BigQuery project={self.project_id}")

    # HELPERS
    def _get_table_id(
        self,
        table_name: str,
    ) -> str:

        # Build fully-qualified BigQuery table name:
        # project.dataset.table
        return f"{self.project_id}.{self.dataset_id}.{table_name}"

    def create_dataset_if_not_exists(
        self,
        location: str = "US",
    ) -> None:

        dataset_ref = f"{self.project_id}.{self.dataset_id}"

        try:
            # Check whether dataset already exists
            self.client.get_dataset(dataset_ref)

            self.logger.info(f"Dataset exists: {dataset_ref}")

        except NotFound:

            # Create dataset automatically for first deployment
            dataset = bigquery.Dataset(dataset_ref)
            dataset.location = location

            self.client.create_dataset(dataset)

            self.logger.info(f"Created dataset: {dataset_ref}")

    def drop_table_if_exists(self, table_name: str) -> None:
        """Xóa bảng nếu tồn tại. Dùng trước WRITE_TRUNCATE để tránh schema conflict."""
        table_id = self._get_table_id(table_name)
        try:
            self.client.delete_table(table_id, not_found_ok=True)
            self.logger.info(f"{table_name}: Đã xóa bảng cũ để tạo lại với schema mới")
            time.sleep(5)
        except NotFound:
            pass

    # LOAD DATAFRAME
    def load_dataframe(
        self,
        df: pd.DataFrame,
        table_name: str,
        write_disposition: str = "WRITE_TRUNCATE",
        partition_col: str = None,
        cluster_cols: list = None,
    ) -> None:
        """
        Load DataFrame lên BigQuery.

        Parameters
        ----------
        df : pd.DataFrame
            DataFrame cần upload.

        table_name : str
            Tên bảng đích.

        write_disposition : str

            WRITE_TRUNCATE
                Ghi đè dữ liệu cũ (tự xóa bảng cũ trước để tránh
                schema conflict với partition/cluster config).

            WRITE_APPEND
                Thêm dữ liệu mới.

        partition_col : str, optional
            Cột để phân vùng (time partitioning)

        cluster_cols : list, optional
            Danh sách các cột để gom cụm (clustering)
        """

        # Prevent unnecessary BigQuery jobs
        if df is None or df.empty:

            self.logger.warning(f"{table_name}: dataframe is empty")
            return

        df = df.copy()

        # Map user-friendly string values to BigQuery constants
        write_modes = {
            "WRITE_TRUNCATE": bigquery.WriteDisposition.WRITE_TRUNCATE,
            "WRITE_APPEND": bigquery.WriteDisposition.WRITE_APPEND,
        }

        if write_disposition not in write_modes:

            raise ValueError(f"Invalid write_disposition: {write_disposition}")

        try:

            table_id = self._get_table_id(table_name)

            # ── Xóa bảng cũ trước khi WRITE_TRUNCATE ─────────────────────
            # Tránh lỗi schema conflict khi bảng cũ được tạo không có
            # partition/cluster config, còn lần load mới lại có config đó.
            # BigQuery sẽ tạo lại bảng mới hoàn toàn đúng schema.
            if write_disposition == "WRITE_TRUNCATE":
                self.drop_table_if_exists(table_name)

            # Configure BigQuery load job
            # CREATE_IF_NEEDED:
            #   create table automatically if it does not exist.
            # AUTODETECT:
            #   infer schema directly from pandas dataframe.
            job_config = bigquery.LoadJobConfig(
                write_disposition=write_modes[write_disposition],
                create_disposition=bigquery.CreateDisposition.CREATE_IF_NEEDED,
                autodetect=True,
            )

            # Cấu hình Phân vùng nếu có và tồn tại trong DF
            if partition_col:

                if partition_col not in df.columns:

                    self.logger.warning(
                        f"{table_name}: Partition column '{partition_col}' not found"
                    )

                else:
                    # Chuyển cột phân vùng về datetime trước khi load
                    if not pd.api.types.is_datetime64_any_dtype(df[partition_col]):
                        self.logger.info(
                            f"{table_name}: Converting partition column '{partition_col}' to datetime"
                        )
                        df[partition_col] = pd.to_datetime(
                            df[partition_col], errors="coerce"
                        )

                    self.logger.info(
                        f"{partition_col} dtype = {df[partition_col].dtype}"
                    )

                    self.logger.info(df[partition_col].head())

                    # DATETIME / TIMESTAMP PARTITION
                    if pd.api.types.is_datetime64_any_dtype(df[partition_col]):
                        job_config.time_partitioning = bigquery.TimePartitioning(
                            type_=bigquery.TimePartitioningType.DAY,
                            field=partition_col,
                            expiration_ms=3153600000000,  # 100 years in ms to override dataset default (60 days)
                        )

                        self.logger.info(
                            f"{table_name}: Time partitioning on '{partition_col}' (DATETIME)"
                        )

            # Cấu hình Gom cụm nếu có và tồn tại trong DF
            if cluster_cols:
                valid_cluster_cols = [c for c in cluster_cols if c in df.columns]
                if valid_cluster_cols:
                    job_config.clustering_fields = valid_cluster_cols
                    self.logger.info(
                        f"{table_name}: Cấu hình Clustering theo các cột: {valid_cluster_cols}"
                    )
                if len(valid_cluster_cols) < len(cluster_cols):
                    missing_clusters = set(cluster_cols) - set(valid_cluster_cols)
                    self.logger.warning(
                        f"{table_name}: Các cột gom cụm không tồn tại trong DataFrame: {list(missing_clusters)}"
                    )

            self.logger.info(f"Loading {len(df)} rows into {table_id}")

            for col in df.columns:
                if pd.api.types.is_datetime64_any_dtype(df[col]):
                    if hasattr(df[col].dtype, "tz") and df[col].dtype.tz is not None:
                        df[col] = df[col].dt.tz_convert(None)
                    # Convert ns → us to avoid ArrowInvalid precision error
                    df[col] = df[col].astype("datetime64[us]")

            self.logger.info(df.dtypes)

            # Submit batch load job to BigQuery
            load_job = self.client.load_table_from_dataframe(
                dataframe=df,
                destination=table_id,
                job_config=job_config,
            )

            # Wait until load job finishes
            load_job.result()
            print("DESTINATION =", load_job.destination)

            print("=" * 50)
            print("OUTPUT_ROWS:", load_job.output_rows)
            print("STATE:", load_job.state)
            print("ERROR_RESULT:", load_job.error_result)
            print("ERRORS:", load_job.errors)
            print("=" * 50)

            self.logger.info(f"Load completed | job_id={load_job.job_id}")

            # load_job.output_rows  show  số rows vừa được ghi
            self.logger.info(
                f"{table_name}: job output_rows = {load_job.output_rows} "
                f"(ground truth từ load job)"
            )

            if load_job.errors:
                self.logger.error(f"{table_name}: load errors = {load_job.errors}")

            # Giải pháp: sleep thêm trước khi đọc metadata để tránh
            # log misleading "0 rows".
            is_partitioned = (
                partition_col is not None
                and partition_col in df.columns
                and pd.api.types.is_datetime64_any_dtype(df[partition_col])
            )
            if is_partitioned:
                self.logger.info(
                    f"{table_name}: partitioned table — waiting 15s "
                    f"for BigQuery metadata propagation..."
                )
                time.sleep(10)

            # đọc metadata và COUNT sau khi đã chờ đủ
            table = self.client.get_table(table_id)

            self.logger.info(f"TABLE_ID = {table_id}")
            self.logger.info(f"PROJECT = {self.project_id}")
            self.logger.info(f"DATASET = {self.dataset_id}")

            self.logger.info(f"{table_name}: metadata num_rows = {table.num_rows}")

            count_query = f"""
                    SELECT COUNT(*) AS cnt
                    FROM `{table_id}`
                """

            count_result = list(self.client.query(count_query).result())

            self.logger.info(f"{table_name}: actual count = {count_result[0].cnt}")

            # Simple validation after loading
            total_rows = self.get_table_row_count(table_name)

            self.logger.info(f"{table_name}: {total_rows} rows")

        except Exception as e:

            self.logger.exception(f"Failed loading table {table_name}: {e}")

            raise

    # QUERY
    def execute_query(
        self,
        query: str,
    ):
        """
        Execute SQL query on BigQuery.
        """

        try:

            query_job = self.client.query(query)

            # Wait for query execution to complete
            result = query_job.result()

            self.logger.info(f"Query executed | job_id={query_job.job_id}")

            return result

        except Exception as e:

            self.logger.exception(f"Query failed: {e}")

            raise

    # VALIDATION
    def get_table_row_count(
        self,
        table_name: str,
    ) -> int:
        """
        Lấy số dòng trong bảng BigQuery từ metadata API.
        """
        try:
            table_id = self._get_table_id(table_name)
            table = self.client.get_table(table_id)
            return table.num_rows
        except NotFound:
            return 0
