import pandas as pd
import hashlib
import logging


class BaseTransformer:
    def __init__(self):
        # Cấu hình logging để theo dõi chất lượng dữ liệu
        logging.basicConfig(
            level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
        )
        self.logger = logging.getLogger(__name__)

    def standardize_column_names(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Quy tắc: Viết thường, bỏ khoảng trắng đầu cuối, thay khoảng trắng giữa bằng '_'
        , thay thế các ký tự đặc biệt

        Ví dụ: ' Customer ID ' -> 'customer_id'
        """
        try:

            if df is None or df.empty:
                self.logger.warning("DataFrame rỗng")
                return df

            old_columns = df.columns.tolist()

            df.columns = (
                df.columns.str.strip()
                .str.lower()
                .str.replace(r"\s+", "_", regex=True)
                .str.replace(r"[^a-zA-Z0-9_]", "", regex=True)
            )

            new_columns = df.columns.tolist()

            self.logger.info("Đã chuẩn hóa tên cột")

            for old, new in zip(old_columns, new_columns):
                self.logger.info(f"{old} -> {new}")

            return df

        except Exception as e:

            self.logger.error(f"Lỗi khi chuẩn hóa tên cột: {e}")
            return df

    #
    def handle_missing_values(
        self, df: pd.DataFrame, missing_config: dict = None
    ) -> pd.DataFrame:
        """
        Xử lý dữ liệu bị thiếu theo nhiều chiến lược.

        Strategies:
        - fill: điền giá trị cố định
        - drop: xóa dòng
        - mean: trung bình (numeric)
        - median: trung vị
        - mode: giá trị xuất hiện nhiều nhất
        """
        try:
            if df is None or df.empty:
                self.logger.warning("DataFrame rỗng")
                return df

            if missing_config is None:
                missing_config = {}

            for col, config in missing_config.items():

                if col not in df.columns:
                    self.logger.warning(f"Column '{col}' không tồn tại")
                    continue

                strategy = config.get("strategy", "fill")

                missing_count = df[col].isnull().sum()

                if missing_count == 0:
                    self.logger.info(f"{col} : no missing value")
                    continue

                if strategy == "fill":
                    value = config.get("value", None)
                    df[col] = df[col].fillna(value)
                    self.logger.info(
                        f" Column '{col}' đã thay thế {missing_count} giá trị thiếu = '{value}'"
                    )

                elif strategy == "drop":
                    before = len(df)
                    df = df.dropna(subset=[col])
                    after = len(df)

                    self.logger.info(
                        f"Cột '{col}' đã xóa {before - after} dòng có giá trị thiếu"
                    )

                elif strategy == "mean":
                    value = df[col].mean()
                    df[col] = df[col].fillna(value)

                    self.logger.info(f"Column {col} đã được thay thế mean = {value}")

                elif strategy == "median":
                    value = df[col].median()
                    df[col] = df[col].fillna(value)

                    self.logger.info(f"Column {col} đã được thay thế median = {value}")

                elif strategy == "mode":

                    mode_values = df[col].mode()

                    if mode_values.empty:
                        self.logger.warning(f"Column {col} không tính được mode")
                        continue

                    value = mode_values[0]

                    df[col] = df[col].fillna(value)

                    self.logger.info(f"Column {col} đã được thay thế mode = {value}")

                else:
                    self.logger.warning(f"{col}: unknow strategy '{strategy}'")

            return df

        except Exception as e:
            self.logger.error(f"Lỗi khi xử lý missing values : {e}")
            return df

    #
    def convert_data_types(
        self, df: pd.DataFrame, type_cf: dict = None
    ) -> pd.DataFrame:
        """
        Chuyển đổi kiểu dữ liệu cho DataFrame.
        Parameters: type_config : dict
        data_type = int , float , datetime or datetime64 , string
        """

        try:
            self.logger.info("Đang convert dữ liệu...")

            if df is None or df.empty:
                self.logger.warning("DataFrame rỗng")
                return df

            if type_cf is None:
                type_cf = {}

            for col, dtype in type_cf.items():

                if col not in df.columns:
                    self.logger.warning(f"Column {col} không tồn tại trong DataFrame")
                    continue

                if dtype == "int":
                    df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")
                    self.logger.info(f"Column '{col}' đã convert sang int ")

                elif dtype == "float":
                    df[col] = pd.to_numeric(df[col], errors="coerce")
                    self.logger.info(f"Cột '{col}' đã convert sang float")

                elif dtype == "string":
                    df[col] = df[col].astype("string")
                    self.logger.info(f"Column '{col}' đã convert sang string")

                elif dtype in ["datetime", "datetime64"]:
                    df[col] = pd.to_datetime(df[col], errors="coerce").astype(
                        "datetime64[us]"
                    )
                    self.logger.info(f"Cột '{col}' đã convert sang datetime")

                else:
                    self.logger.warning(f"Kiểu dữ liệu '{dtype}' chưa được hỗ trợ")

            self.logger.info("Hoàn thành chuyển đổi kiểu dữ liệu")
            return df

        except Exception as e:

            self.logger.error(f"Lỗi khi convert data types: {e}")
            return df

    def handle_negative_values(
        self,
        df: pd.DataFrame,
        column_rules: dict,
    ) -> pd.DataFrame:
        """
        Xử lý giá trị âm theo business rule.

        Rules:
        - abs   : chuyển âm thành dương
        - drop  : xóa record có giá trị âm
        - null  : chuyển giá trị âm thành NULL
        - allow : giữ nguyên

        Example:
        ----------
        rules = {
            "quantity": "abs",
            "unit_price": "abs",
            "sales_amount": "abs",
            "refund_amount": "allow",
            "profit": "allow"
        }

        df = self.handle_negative_values(df, rules)
        """

        try:

            if df is None or df.empty:
                self.logger.warning("DataFrame rỗng")
                return df

            for col, rule in column_rules.items():

                if col not in df.columns:
                    self.logger.warning(f"Cột '{col}' không tồn tại trong DataFrame")
                    continue

                df[col] = pd.to_numeric(df[col], errors="coerce")

                negative_mask = df[col] < 0

                negative_count = int(negative_mask.sum())

                if negative_count == 0:
                    continue

                if rule == "abs":

                    df.loc[negative_mask, col] = df.loc[negative_mask, col].abs()

                    self.logger.warning(
                        f"Cột '{col}': "
                        f"đã chuyển {negative_count} giá trị âm thành dương"
                    )

                elif rule == "drop":

                    before = len(df)

                    df = df[~negative_mask]

                    after = len(df)

                    self.logger.warning(
                        f"Cột '{col}': "
                        f"đã xóa {before - after} records có giá trị âm"
                    )

                elif rule == "null":

                    df.loc[negative_mask, col] = pd.NA

                    self.logger.warning(
                        f"Cột '{col}': "
                        f"đã chuyển {negative_count} giá trị âm thành NULL"
                    )

                elif rule == "allow":

                    self.logger.info(
                        f"Cột '{col}': "
                        f"{negative_count} giá trị âm được phép giữ nguyên"
                    )

                else:

                    self.logger.warning(f"Cột '{col}': rule '{rule}' không hợp lệ")

            return df

        except Exception as e:

            self.logger.error(f"Lỗi xử lý negative values: {e}")

            return df

    def create_surrogate_key(
        self,
        df,
        selected_cols: list,
        new_key_name="new_key_name",
    ):
        """
        Create hashed surrogate key from multiple columns.

        Example:
        customer_id + email
        =>
        08809ca8eb94f292
        """

        try:

            if df is None or df.empty:
                self.logger.warning("DataFrame is empty")
                return df

            missing_cols = [c for c in selected_cols if c not in df.columns]

            if missing_cols:
                self.logger.error(f"Columns {missing_cols} not found in DataFrame")
                return df

            df = df.copy()

            # Combine business key columns
            combined_values = (
                df[selected_cols].fillna("NULL").astype(str).agg("_".join, axis=1)
            )

            # SHA256 -> lấy 16 ký tự đầu
            df[new_key_name] = combined_values.apply(
                lambda x: hashlib.sha256(x.encode("utf-8")).hexdigest()[:16]
            )

            self.logger.info(f"Successfully created surrogate key '{new_key_name}'")

            return df

        except Exception as e:
            self.logger.error(f"Error creating surrogate key: {e}")
        raise

    ##
    def explode_json_column(
        self,
        df: pd.DataFrame,
        explode_col: str,
        drop_original: bool = True,
    ) -> pd.DataFrame:
        """
        Explode nested JSON array column
        and normalize dict values into columns.

        Parameters
        ----------
        df : pd.DataFrame
            Input dataframe

        explode_col : str
            Column chứa nested list/json

        drop_original : bool
            Có xoá cột nested gốc hay không

        Returns
        -------
        pd.DataFrame
            Dataframe sau khi explode + normalize
        """

        try:
            # Check dataframe rỗng
            if df.empty:
                self.logger.warning("Input dataframe is empty")
                return df

            # Check column tồn tại
            if explode_col not in df.columns:
                self.logger.error(f"Column '{explode_col}' does not exist in dataframe")
                return df

            # Drop null để tránh explode lỗi
            df = df[df[explode_col].notna()].copy()

            # Explode list -> rows
            df = df.explode(explode_col)

            # Nếu sau explode bị empty
            if df.empty:
                self.logger.warning(
                    f"No data found after exploding column: {explode_col}"
                )
                return df

            # Normalize json/dict -> columns
            normalized_df = pd.json_normalize(df[explode_col])

            duplicate_cols = [col for col in normalized_df.columns if col in df.columns]

            if duplicate_cols:
                self.logger.warning(f"Duplicate columns removed: {duplicate_cols}")

                normalized_df = normalized_df.drop(columns=duplicate_cols)

            # Merge lại
            df = pd.concat(
                [
                    df.reset_index(drop=True),
                    normalized_df.reset_index(drop=True),
                ],
                axis=1,
            )

            # Drop nested column cũ
            if drop_original:
                df.drop(columns=[explode_col], inplace=True)

            self.logger.info(f"Successfully exploded column: {explode_col}")

            return df

        except KeyError as e:
            self.logger.error(f"KeyError while exploding column '{explode_col}': {e}")
            return df

        except ValueError as e:
            self.logger.error(f"ValueError while exploding column '{explode_col}': {e}")
            return df

        except Exception as e:
            self.logger.exception(
                f"Unexpected error while exploding column '{explode_col}': {e}"
            )
            return df

    # Tạo Date key

    def create_date_key(self, df, date_column, key_date_name="xxx_key_date"):
        """
        Creates a new integer date key column in YYYYMMDD format
        from a specific datetime column.
        Ví dụ: 2024-01-15 09:30:00  →  20240115
        
        """

        try:
            if date_column in df.columns:
                # Ensure the source column is datetime
                parsed = pd.to_datetime(df[date_column], errors="coerce")

                if hasattr(parsed.dtype, "tz") and parsed.dtype.tz is not None:
                    parsed = parsed.dt.tz_convert(None)

                # Format sang YYYYMMDD integer — khớp với dim_date.date_key
                # NaT → NaN → Int64 (nullable) giữ nguyên NULL thay vì raise lỗi
                df[key_date_name] = (
                    parsed.dt.strftime("%Y%m%d")  # "20240115" hoặc NaN
                    .astype("Int64", errors="ignore")  # int nullable, giữ NaN thành pd.NA
                )

                self.logger.debug(
                    f"Created date key '{key_date_name}' from '{date_column}' "
                    f"(dtype={df[key_date_name].dtype}) — format YYYYMMDD integer."
                )
            else:
                self.logger.warning(
                    f"Source column '{date_column}' not found. Cannot create date key."
                )
            return df

        except Exception as e:
            self.logger.error(f"Error in create_date_key: {e}")
            raise e

    def add_audit_cols(
        self,
        df: pd.DataFrame,
        source_system: str = "unknown",
    ) -> pd.DataFrame:
        """
        Add audit columns for:

        - Data Lineage
        - Monitoring

        Parameters
        ----------
        df : pd.DataFrame
            Input dataframe

        source_system : str
            Source system name
            Example:
            - shopify
            - paypal
            - momo
            - mercury
            - tracking

        Returns
        -------
        pd.DataFrame
        """

        try:

            if df is None or df.empty:
                self.logger.warning("DataFrame is empty")
                return df

            current_time = pd.Timestamp.now()

            if "source_system" not in df.columns:
                df["source_system"] = source_system

            if "ingestion_time" not in df.columns:
                df["ingestion_time"] = current_time
                df["ingestion_time"] = pd.to_datetime(df["ingestion_time"]).astype(
                    "datetime64[us]"
                )

            self.logger.info(f"Added audit columns | source_system={source_system}")

            return df

        except Exception as e:

            self.logger.exception(f"Error adding audit columns: {e}")

            return df

    #
    def data_quality_check(
        self,
        df: pd.DataFrame,
        table_name: str,
        key_columns: list = None,
        date_columns: list = None,
        amount_columns: list = None,
        allow_negative_amounts: bool = False,
        min_valid_date: str = "2000-01-01",
    ) -> dict:
        """
        Thực hiện kiểm tra chất lượng dữ liệu.

        Bao gồm:
        - Kiểm tra NULL values
        - Kiểm tra duplicates
        - Validate date ranges
        - Validate amount columns
        - Generate statistical summary
        - Detect outliers

        Parameters:
        table_name : str
            Tên bảng dữ liệu

        key_columns : list
            Các cột dùng để check duplicates

        date_columns : list
            Các cột datetime cần validate

        amount_columns : list
            Các cột numeric cần validate

        allow_negative_amounts : bool
            Cho phép giá trị âm hay không
        """
        try:
            self.logger.info(f"DATA QUALITY CHECK: {table_name}")

            if df is None or df.empty:

                self.logger.warning("DataFrame rỗng")
                return {}

            # # INIT QUALITY REPORT
            quality_report = {
                "table_name": table_name,
                "total_rows": len(df),
                "total_columns": len(df.columns),
                "null_issues": {},
                "duplicate_count": 0,
                "date_issues": {},
                "amount_issues": {},
            }

            self.logger.info(f"Số dòng: {len(df)} | " f"Số cột: {len(df.columns)}")

            self.logger.info(f"Các columns: {df.columns.tolist()}")

            # Check null
            self.logger.info("Kiem tra NULL values")
            null_counts = df.isnull().sum()
            cols_null = null_counts[null_counts > 0]

            if not cols_null.empty:
                for col, count in cols_null.items():
                    self.logger.warning(f"Cột '{col}' có {count} giá trị Null ")

                    quality_report["null_issues"][col] = int(count)
            else:

                self.logger.info("Không phát hiện NULL values")

            # Check duplicates
            self.logger.info("Kiem tra duplicate")
            if key_columns:
                missing_keys = [col for col in key_columns if col not in df.columns]
                if missing_keys:
                    self.logger.warning(
                        f"Không tìm thấy key columns: " f"{missing_keys}"
                    )

                else:
                    duplicate_count = df.duplicated(subset=key_columns).sum()
                    quality_report["duplicate_count"] = int(duplicate_count)

                    if duplicate_count > 0:
                        self.logger.warning(
                            f"Phát hiện " f"{duplicate_count} duplicate records"
                        )
                    else:
                        self.logger.info("Không phát hiện duplicates")

            # Check Date validation
            if date_columns:
                self.logger.info("Check Date Validation : ")

                current_date = pd.Timestamp.now()

                for col in date_columns:
                    if col not in df.columns:
                        self.logger.warning(f"Cot '{col}' không tồn tại ")
                        continue

                    valid_dates = df[col].dropna()

                    if valid_dates.empty:
                        self.logger.warning(f"Cột '{col}' không có dữ liệu date hợp lệ")
                        continue

                    min_date = valid_dates.min()
                    max_date = valid_dates.max()

                    self.logger.info(f"Cột '{col}' " f"từ {min_date} đến {max_date}")

                    future_date = valid_dates[valid_dates > current_date]

                    unreasonable_old = valid_dates[
                        valid_dates < pd.Timestamp(min_valid_date)
                    ]

                    quality_report["date_issues"][col] = {
                        "future_date": int(len(future_date)),
                        "unreasonable_old_dates": int(len(unreasonable_old)),
                    }

                    if len(future_date) > 0:
                        self.logger.warning(
                            f"Cot '{col}' co " f"{len(future_date)} future dates"
                        )

                    if len(unreasonable_old) > 0:
                        self.logger.warning(
                            f"Cot '{col}' co "
                            f"{len(unreasonable_old)} dates trước năm 2000"
                        )

            # Check amount Validation
            if amount_columns:
                self.logger.info("Check Amount Validation")

                for col in amount_columns:
                    if col not in df.columns:
                        self.logger.warning(f"Cột amount '{col}' không tồn tại")
                        continue

                    valid_amounts = df[col].dropna()

                    if valid_amounts.empty:

                        self.logger.warning(
                            f"Cột '{col}' không có dữ liệu amount hợp lệ"
                        )

                        continue

                    # NEGATIVE VALUES
                    negative_count = (valid_amounts < 0).sum()

                    if negative_count > 0:

                        if allow_negative_amounts:

                            self.logger.info(
                                f"Cột '{col}' có "
                                f"{negative_count} giá trị âm "
                                f"(được cho phép)"
                            )

                        else:

                            self.logger.warning(
                                f"Cột '{col}' có " f"{negative_count} giá trị âm"
                            )

                    # Statistic Summary
                    mean_val = valid_amounts.mean()

                    median_val = valid_amounts.median()

                    std_val = valid_amounts.std()

                    min_val = valid_amounts.min()

                    max_val = valid_amounts.max()

                    self.logger.info(f"""
                        Statistical Summary - {col}
                        Mean   : {mean_val:.2f}
                        Median : {median_val:.2f}
                        Std Dev: {std_val:.2f}
                        Min    : {min_val:.2f}
                        Max    : {max_val:.2f}
                    """)

                    # Outlier Detection
                    Q1 = valid_amounts.quantile(0.25)

                    Q3 = valid_amounts.quantile(0.75)

                    IQR = Q3 - Q1

                    lower_bound = Q1 - 1.5 * IQR

                    upper_bound = Q3 + 1.5 * IQR

                    outliers = valid_amounts[
                        (valid_amounts < lower_bound) | (valid_amounts > upper_bound)
                    ]

                    outlier_count = len(outliers)

                    if outlier_count > 0:
                        self.logger.warning(
                            f"Cột '{col}' có " f"{outlier_count} outliers"
                        )

                    else:
                        self.logger.info(f"Cột '{col}' không có outliers đáng kể")

                    quality_report["amount_issues"][col] = {
                        "negative_count": int(negative_count),
                        "outlier_count": int(outlier_count),
                        "mean": float(mean_val),
                        "median": float(median_val),
                        "std_dev": float(std_val),
                        "min": float(min_val),
                        "max": float(max_val),
                    }
            self.logger.info(f"Hoàn thành data quality check: {table_name}")
            return quality_report
        except Exception as e:
            self.logger.error(f"Lỗi data quality check: {e}")
            return {}
