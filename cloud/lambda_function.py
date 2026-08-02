import json
import os
from urllib.parse import unquote_plus

import boto3
from botocore.exceptions import ClientError

from cloud.message_router import route_key


class S3ObjectStore:
    def __init__(self, bucket):
        self.bucket = bucket
        self.client = boto3.client("s3")

    def get_json(self, key, default=...):
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=key)
        except ClientError as error:
            if default is not ... and error.response.get("Error", {}).get("Code") in ("NoSuchKey", "404"):
                return default
            raise
        return json.loads(response["Body"].read().decode("utf-8"))

    def put_json(self, key, value):
        self.client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=json.dumps(value, indent=2, sort_keys=True).encode("utf-8"),
            ContentType="application/json",
            ServerSideEncryption="AES256",
        )


def lambda_handler(event, context):
    results = []
    expected_bucket = os.environ.get("MORSEPI_BUCKET", "")
    for record in event.get("Records", []):
        bucket = record["s3"]["bucket"]["name"]
        if expected_bucket and bucket != expected_bucket:
            raise ValueError("Unexpected S3 bucket.")
        key = unquote_plus(record["s3"]["object"]["key"])
        results.append(route_key(S3ObjectStore(bucket), key))
    return {"processed": len(results), "results": results}
