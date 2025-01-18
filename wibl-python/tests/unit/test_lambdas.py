import unittest
from pathlib import Path
import os
import tempfile
import shutil
from datetime import datetime
import json

from wibl import config_logger_service
import wibl.core.config as conf
from wibl.core import Lineage
import wibl.core.timestamping as ts
from wibl.core.datasource import LocalSource, LocalController
from wibl.core.notification import LocalNotifier
from wibl.processing.cloud.aws.lambda_function import process_item
from wibl.core.geojson_convert import FMT_OBS_TIME


logger = config_logger_service()


def validate_depth(depth: float) -> bool:
    return depth != -1e9


def validate_lon_lat(lon: float, lat: float) -> bool:
    if lon < -180.0 or lon > 180.0:
        return False
    if lat < -90.0 or lat > 90.0:
        return False
    return True


def validate_obs_time_str(obs_time_str: str) -> bool:
    try:
        obs_time = datetime.strptime(obs_time_str, FMT_OBS_TIME)
    except ValueError:
        return False
    return obs_time.year < 2100


class TestAlgorithms(unittest.TestCase):
    def setUp(self) -> None:
        self.fixtures_dir = Path(Path(__file__).parent.parent, 'data')
        self.tmp_dir = tempfile.mkdtemp()

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp_dir)

    def test_processing_process_item(self):
        # Initialize
        config_file = Path(self.fixtures_dir, 'configure.local.json')
        infile = str(Path(self.fixtures_dir, 'test-algo-dedup-nodata.wibl'))
        config = conf.read_config(config_file)
        if 'notification' not in config:
            config['notification'] = {}
        if 'converted' not in config['notification']:
            config['notification']['converted'] = ''
        now = datetime.utcnow()
        outfile = os.path.join(self.tmp_dir, f"{now.timestamp()}.geojson")
        # The cloud-based code uses environment variables to provide some of the configuration,
        # so we need to add this to the local environment to compensate.
        os.environ['PROVIDER_ID'] = config['provider_id']
        if 'management_url' in config:
            os.environ['MANAGEMENT_URL'] = config['management_url']

        # First load data without processing algorithms to include data from all packets
        lineage: Lineage = Lineage()
        source_data = ts.time_interpolation(infile, lineage, config['elapsed_time_quantum'],
                                            verbose=config['verbose'], fault_limit=config['fault_limit'],
                                            process_algorithms=False)
        self.assertIsNotNone(source_data)
        self.assertEqual(287, len(source_data['depth']['z']))
        # Count no-data depth values
        self.assertEqual(28, len(source_data['depth']['z'][source_data['depth']['z'] == -1e9]))

        # Next, run process_item function of processing lambda to convert WIBL data to GeoJSON
        source = LocalSource(infile, outfile, config)
        data_item = source.nextSource()
        controller = LocalController(config)
        notifier = LocalNotifier(config['notification']['converted'])
        status = process_item(data_item, controller, notifier, config)
        self.assertTrue(status)

        # Now, open resulting GeoJSON file and compare to raw WIBL data
        with open(outfile, 'r') as f:
            out_data = json.load(f)
            self.assertIsNotNone(out_data)
            self.assertEqual(201, len(out_data['features']))
            # Ensure "no-data" values have not made it into GeoJSON output
            for feat in out_data['features']:
                self.assertTrue(validate_lon_lat(*feat['geometry']['coordinates']),
                                msg=feat['geometry']['coordinates'])
                self.assertTrue(validate_depth(feat['properties']['depth']),
                                msg=feat['properties']['depth'])
                self.assertTrue(validate_obs_time_str(feat['properties']['time']),
                                msg=feat['properties']['time'])
