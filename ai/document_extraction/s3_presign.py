import boto3
from botocore.config import Config

def presign_get_url(bucket: str, key: str, region: str, expires_seconds: int = 300) -> str:
    s3 = boto3.client(
        "s3",
        region_name=region,
        config=Config(signature_version="s3v4"),
    )
    return s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": key},
        ExpiresIn=expires_seconds,
    )