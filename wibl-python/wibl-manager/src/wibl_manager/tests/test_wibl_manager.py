import os
import unittest
import logging
import uuid

import requests

from wibl_manager import ReturnCodes, ProcessingStatus, UploadStatus

logger = logging.getLogger(__name__)


class TestWiblManager(unittest.TestCase):
    def setUp(self) -> None:
        self.filename = 'cddb-aefga-weqa'
        self.base_uri = os.environ.get('BASE_URI', 'http://127.0.0.1:8001/')

    def tearDown(self) -> None:
        pass

    def test_aaa_healthcheck(self):
        response = requests.get(self.base_uri + 'heartbeat')
        self.assertIsNotNone(response)
        self.assertEqual(ReturnCodes.OK.value, response.status_code)

    def test_bbb_random_entries(self):
        n_raw_added = 0
        n_geo_added = 0
        for _ in range(100):
            fileid = str(uuid.uuid4())
            response = requests.post(self.base_uri + 'wibl/' + fileid, json={'size': 10.4})
            self.assertIsNotNone(response)
            self.assertEqual(ReturnCodes.RECORD_CREATED.value, response.status_code)
            n_raw_added += 1

            response = requests.put(self.base_uri + 'wibl/' + fileid,
                                    json={'logger': 'UNHJHC-wibl-1', 'platform': 'USCGC Healy',
                                          'observations': 100232, 'soundings': 8023,
                                          'startTime': '2023-01-23T12:34:45.142',
                                          'endTime': '2023-01-24T01:45:23.012',
                                          'status': ProcessingStatus.PROCESSING_SUCCESSFUL.value})
            self.assertIsNotNone(response)
            self.assertEqual(ReturnCodes.RECORD_CREATED.value, response.status_code)

            geojson_fileid = fileid + '.json'
            response = requests.post(self.base_uri + 'geojson/' + geojson_fileid, json={'size': 5.4})
            self.assertIsNotNone(response)
            self.assertEqual(ReturnCodes.RECORD_CREATED.value, response.status_code)
            n_geo_added += 1
            response = requests.put(self.base_uri + 'geojson/' + geojson_fileid,
                                    json={'logger': 'UNHJHC-wibl-1',
                                          'soundings': 8023,
                                          'status': UploadStatus.UPLOAD_SUCCESSFUL.value})
            self.assertIsNotNone(response)
            self.assertEqual(ReturnCodes.RECORD_CREATED.value, response.status_code)

    def test_ccc_filename(self):
        response = requests.delete(self.base_uri + 'wibl/' + self.filename)
        self.assertIsNotNone(response)
        self.assertEqual(404, response.status_code)

        response = requests.post(self.base_uri + 'wibl/' + self.filename, json={'size': 10.4})
        self.assertIsNotNone(response)
        self.assertEqual(ReturnCodes.RECORD_CREATED.value, response.status_code)

        messages = ['foo', 'bar', 'baz']
        response = requests.put(self.base_uri + 'wibl/' + self.filename,
                                json={'size': 5.4, 'observations': 10232, 'logger': 'UNHJHC-wibl-1',
                                      'startTime': '2023-01-23T13:45:08.231', 'status': 1,
                                      'messages': '\n'.join(messages)})
        self.assertIsNotNone(response)
        self.assertEqual(ReturnCodes.RECORD_CREATED.value, response.status_code)
        self.assertEqual('foo\nbar\nbaz', response.json()['messages'])

        response = requests.delete(self.base_uri + 'wibl/' + self.filename)
        self.assertIsNotNone(response)
        self.assertEqual(ReturnCodes.OK.value, response.status_code)

        response = requests.delete(self.base_uri + 'geojson/' + self.filename)
        self.assertIsNotNone(response)
        self.assertEqual(404, response.status_code)

        response = requests.post(self.base_uri + 'geojson/' + self.filename, json={'size': 5.4})
        self.assertIsNotNone(response)
        self.assertEqual(ReturnCodes.RECORD_CREATED.value, response.status_code)

        response = requests.put(self.base_uri + 'geojson/' + self.filename,
                                json={'logger': 'UNHJHC-wibl-1', 'soundings': 8020, 'size': 5.3, 'status': 1})
        self.assertIsNotNone(response)
        self.assertEqual(ReturnCodes.RECORD_CREATED.value, response.status_code)

        response = requests.delete(self.base_uri + 'geojson/' + self.filename)
        self.assertIsNotNone(response)
        self.assertEqual(ReturnCodes.OK.value, response.status_code)


if __name__ == '__main__':
    unittest.main(
        failfast=False, buffer=False, catchbreak=False
    )
