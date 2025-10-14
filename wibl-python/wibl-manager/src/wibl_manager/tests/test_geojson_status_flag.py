import os
import unittest
import logging
import uuid

import requests

from wibl_manager import GeoJSONStatus

logger = logging.getLogger(__name__)


class TestWiblManager(unittest.TestCase):

    def tearDown(self) -> None:
        pass

    def test_aaa_applying_upload_status(self):
        empty_test_status = GeoJSONStatus.VALIDATION_STARTED.value & GeoJSONStatus.EMPTY_VALIDATION.value
        upload_started_status = empty_test_status | GeoJSONStatus.UPLOAD_STARTED.value
        upload_successful_status = empty_test_status | GeoJSONStatus.UPLOAD_SUCCESSFUL.value
        upload_failed_status = empty_test_status | GeoJSONStatus.UPLOAD_FAILED.value

        self.assertEqual(GeoJSONStatus.UPLOAD_STARTED.value, upload_started_status)
        self.assertEqual(GeoJSONStatus.UPLOAD_SUCCESSFUL.value, upload_successful_status)
        self.assertEqual(GeoJSONStatus.UPLOAD_FAILED.value, upload_failed_status)

    def test_bbb_applying_validation_status(self):
        empty_test_status = GeoJSONStatus.VALIDATION_STARTED.value & GeoJSONStatus.EMPTY_VALIDATION.value
        validation_started_status = empty_test_status | GeoJSONStatus.VALIDATION_STARTED.value
        validation_successful_status = empty_test_status | GeoJSONStatus.VALIDATION_SUCCESSFUL.value
        validation_failed_status = empty_test_status | GeoJSONStatus.VALIDATION_FAILED.value

        self.assertEqual(GeoJSONStatus.VALIDATION_STARTED.value, validation_started_status)
        self.assertEqual(GeoJSONStatus.VALIDATION_SUCCESSFUL.value, validation_successful_status)
        self.assertEqual(GeoJSONStatus.VALIDATION_FAILED.value, validation_failed_status)

    def test_ccc_independent_status_changes(self):
        empty_test_status = GeoJSONStatus.UPLOAD_SUCCESSFUL.value

        validation_change_status = empty_test_status | GeoJSONStatus.VALIDATION_FAILED.value

        self.assertEqual(GeoJSONStatus.UPLOAD_SUCCESSFUL.value | GeoJSONStatus.VALIDATION_FAILED.value,
                         validation_change_status)

    def test_ddd_clear_status(self):
        upload_test_status = (GeoJSONStatus.UPLOAD_SUCCESSFUL.value | GeoJSONStatus.UPLOAD_STARTED.value |
                              GeoJSONStatus.UPLOAD_FAILED.value | GeoJSONStatus.VALIDATION_SUCCESSFUL.value)

        upload_cleared_status = upload_test_status & GeoJSONStatus.EMPTY_UPLOAD.value

        self.assertEqual(GeoJSONStatus.VALIDATION_SUCCESSFUL.value, upload_cleared_status)

        validation_test_status = (GeoJSONStatus.VALIDATION_SUCCESSFUL.value | GeoJSONStatus.VALIDATION_STARTED.value |
                                  GeoJSONStatus.VALIDATION_FAILED.value | GeoJSONStatus.UPLOAD_STARTED.value)

        validation_cleared_status = validation_test_status & GeoJSONStatus.EMPTY_VALIDATION.value

        self.assertEqual(GeoJSONStatus.UPLOAD_STARTED.value, validation_cleared_status)


if __name__ == '__main__':
    unittest.main(
        failfast=False, buffer=False, catchbreak=False
    )
