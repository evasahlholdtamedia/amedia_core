## This script grabs the BigQuery client to make it easy to import data.

from functools import cache
from google.cloud import bigquery

BILLING_PROJECT = "amedia-analytics-eu"

@cache
def get_client(billing_project=BILLING_PROJECT):
    return bigquery.Client(project=billing_project)