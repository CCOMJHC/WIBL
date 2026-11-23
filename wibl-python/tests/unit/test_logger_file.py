import unittest

import xmlrunner

from wibl import config_logger_service
import wibl.core.logger_file.base as lf

logger = config_logger_service()


class TestLoggerFile(unittest.TestCase):
    def test_temp_to_celsius(self):
        self.assertAlmostEqual(-273.15, lf.temp_to_celsius(0))
        self.assertAlmostEqual(26.85, lf.temp_to_celsius(300))

    def test_pressure_to_mbar(self):
        self.assertAlmostEqual(0.01, lf.pressure_to_mbar(1))

    def test_angle_to_degs(self):
        self.assertAlmostEqual(57.295779513, lf.angle_to_degs(1))
        self.assertAlmostEqual(171.88733854, lf.angle_to_degs(3))
        self.assertAlmostEqual(401.07045659, lf.angle_to_degs(7))


if __name__ == '__main__':
    unittest.main(
        testRunner=xmlrunner.XMLTestRunner(output='test-reports'),
        failfast=False, buffer=False, catchbreak=False
    )
