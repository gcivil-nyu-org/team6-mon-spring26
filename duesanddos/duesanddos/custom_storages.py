from storages.backends.s3boto3 import S3Boto3Storage


class MediaStorage(S3Boto3Storage):
    """Store user-uploaded media under the 'media/' prefix in S3."""
    location = "media"
    file_overwrite = True   # Skip HeadObject check — IAM only has PutObject, not GetObject
