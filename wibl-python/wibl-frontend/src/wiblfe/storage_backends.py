from django.conf import settings
from storages.backends.s3boto3 import S3Boto3Storage

class StaticStorage(S3Boto3Storage):
    location = 'static'
    default_acl = None
    custom_domain = settings.CLOUDFRONT_DOMAIN
    file_overwrite = True
