if __name__ == "__main__":
    import os
    import sys
    import pandas as pd

    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    sys.path.append(project_root)

    from extractors.customer_extractor import customer_Extractor
    from transformers.dimension_transformer import DimTransformer
    from transformers.fact_transformer import FactTransformer
    from loaders.bigquery_loader import BigQueryLoader
    from extractors.payment_extractor import Payment_Extractor

    bucket = "minpy"

    # data_extract = customer_Extractor(bucket)
    # dim_table = DimTransformer()
    loader = BigQueryLoader()

    # customer_data = data_extract.extract_file()
    # dim_customer = dim_table.create_dim_customer(customer_data)

    # # test data_source empty
    empty_df = pd.DataFrame()
    loader.load_dataframe(empty_df, "dim_empty")

    # # check upload - successfull scenario
    check_data = loader.create_dataset_if_not_exists()
    # loader.load_dataframe(dim_customer, "dim_customer")

    payment = Payment_Extractor(bucket)
    mercury_df = payment.payment_mercury_extract()
    fact_table = FactTransformer()

    fact_bank_transactions = fact_table.fact_bank_transactions(mercury_df)
    loader.load_dataframe(fact_bank_transactions, "fact_bank_transactions")
