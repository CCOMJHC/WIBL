from django.conf import settings
from storages.backends.s3boto3 import S3Boto3Storage

class StaticStorage(S3Boto3Storage):
    location = 'static'
    default_acl = "private"
    custom_domain = settings.CLOUDFRONT_DOMAIN
    file_overwrite = True
