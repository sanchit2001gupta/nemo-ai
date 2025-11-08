import os
import json
from urllib.parse import urlparse

import requests
import boto3
import logging

logger = logging.getLogger(__name__)

secrets_manager_client = boto3.client('secretsmanager', region_name='us-east-1')

def get_github_pat_from_secrets_manager(secret_arn: str) -> str:
    """Fetch the GitHub personal access token from AWS Secrets Manager using the given ARN."""
    try:
        response = secrets_manager_client.get_secret_value(SecretId=secret_arn)
        secret_str = response.get('SecretString')

        if not secret_str:
            raise ValueError("SecretString not found in secret.")

        secret_dict = json.loads(secret_str)

        token = secret_dict.get('token')
        if not token:
            raise ValueError("'token' key not found in secret.")

        return token
    except Exception as e:
        print(f"[ERROR] Could not retrieve GitHub PAT: {e}")
        raise
