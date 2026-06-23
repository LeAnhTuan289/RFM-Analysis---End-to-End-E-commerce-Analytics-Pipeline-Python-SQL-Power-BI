import os
import sys

# Add project root to path to import utils
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(project_root)

from google.cloud import storage
from utils.config import load_env_variables, get_gcs_credentials_path

# Load environment variables
load_env_variables()
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = get_gcs_credentials_path()


def test_connect_gcs():
    "This function is used to creat connect to GCS and test connection is successfully"
    client = storage.Client()

    bucket_name = "minpy"
    bucket = client.bucket(bucket_name)

    blobs = list(client.list_blobs(bucket_name))
    for i in blobs:
        print("Name: ", i.name)
    return True


test_connect_gcs()
