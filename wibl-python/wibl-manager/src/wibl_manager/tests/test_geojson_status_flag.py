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
        test_status = 0
        upload_started_status = test_status | GeoJSONStatus.UPLOAD_STARTED.value
        upload_successful_status = test_status | GeoJSONStatus.UPLOAD_SUCCESSFUL.value
        upload_failed_status = test_status | GeoJSONStatus.UPLOAD_FAILED.value

        self.assertEqual(0b001000, upload_started_status)
        self.assertEqual(0b010000, upload_successful_status)
        self.assertEqual(0b100000, upload_failed_status)

    def test_bbb_applying_validation_status(self):
        test_status = 0
        validation_started_status = test_status | GeoJSONStatus.VALIDATION_STARTED.value
        validation_successful_status = test_status | GeoJSONStatus.VALIDATION_SUCCESSFUL.value
        validation_failed_status = test_status | GeoJSONStatus.VALIDATION_FAILED.value

        self.assertEqual(0b000001, validation_started_status)
        self.assertEqual(0b000010, validation_successful_status)
        self.assertEqual(0b000100, validation_failed_status)

    def test_ccc_independent_status_changes(self):
        test_status = 0b100000

        validation_change_status = test_status | GeoJSONStatus.VALIDATION_FAILED.value

        self.assertEqual(0b100100, validation_change_status)

    def test_ddd_clear_status(self):
        test_status = 0b111111

        validation_cleared_status = test_status & GeoJSONStatus.EMPTY_VALIDATION.value

        self.assertEqual(0b111000, validation_cleared_status)

        upload_cleared_status = test_status & GeoJSONStatus.EMPTY_UPLOAD.value

        self.assertEqual(0b000111, upload_cleared_status)

if __name__ == '__main__':
    unittest.main(
        failfast=False, buffer=False, catchbreak=False
    )
