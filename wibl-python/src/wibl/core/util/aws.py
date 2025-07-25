from typing import Callable, IO, AnyStr, Optional
from functools import partial
import logging

from botocore.exceptions import ClientError
import xarray

from wibl import get_logger


logger = get_logger()


def generate_get_s3_object(boto_s3_client) -> Callable[[str, str], Optional[IO[AnyStr]]]:
    def open_s3_object(client, bucket: str, key: str) -> Optional[IO[AnyStr]]:
        try:
            return client.get_object(Bucket=bucket, Key=key)['Body']
        except ClientError as e:
            logger.warning(f"Unabled to open {key} in bucket {bucket}, reason: {e.response['Error']['Code']}.")
            return None

    return partial(open_s3_object, boto_s3_client)


def open_s3_hdf5_as_xarray(*, bucket: str, key: str, array_name: str) -> xarray.DataArray:
    # Import fsspec here so that environment variables controlling its behaviour
    #   (e.g. FSSPEC_S3_ENDPOINT_URL, which is used in automated tests to point to
    #   localstack) can be set before import.
    import fsspec
    ncfile = fsspec.open(f"s3://{bucket}/{key}")
    gebco_ds: xarray.Dataset = xarray.open_dataset(ncfile.open(), engine='h5netcdf')
    return gebco_ds[array_name]
