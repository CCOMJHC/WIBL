import struct
import unittest
import math

import xmlrunner
import numpy as np

from wibl import config_logger_service
from wibl.core.logger_file import PacketTypes
from wibl.simulator.data import DataGenerator, State, FormattedAngle, format_angle, MAX_RAD
from wibl.simulator.data.writer import Writer, MemoryWriter


logger = config_logger_service()


class TestDataGeneratorVersion_1_3(unittest.TestCase):
    """
    TODO: Add tests for the following packet types in `wibl.core.logger_file.py`:
        - COG
        - Environment
        - Temperature
        - Humidity
        - Pressure
        - SerialiserVersion
        - Motion
        - Metadata
        - AlgorithmRequest
        - JSONMetadata
        - NMEA0183Filter
    """
    def test_compute_checksum(self):
        self.assertEqual(86, DataGenerator.compute_checksum("$GPZDA,000000.000,01,01,2020,00,00*"))

    def test_format_angle(self):
        fa: FormattedAngle = format_angle(43.000003270800001)
        self.assertEqual(43, fa.degrees)
        self.assertEqual(0.0000032708000006209659, fa.minutes)
        self.assertEqual(1, fa.hemisphere)

        fa: FormattedAngle = format_angle(-74.999996729200006)
        self.assertEqual(74, fa.degrees)
        self.assertEqual(0.99999672920000648, fa.minutes)
        self.assertEqual(0, fa.hemisphere)

    def test_unit_normal(self):
        state: State = State()

        max_itr: int = 1_000_000
        test_unit_normal = np.zeros((max_itr,))
        for i in range(max_itr):
            test_unit_normal[i] = state.unit_normal()

        logger.debug(f"Num iterations: {max_itr}")
        logger.debug(f"Mean: {np.mean(test_unit_normal)}, min: {min(test_unit_normal)}, max: {max(test_unit_normal)}")

        self.assertAlmostEqual(0.0, np.mean(test_unit_normal), 2)
        self.assertLess(-5.75, min(test_unit_normal))
        self.assertGreater(5.75, max(test_unit_normal))

    def __test_header_packets(self, buff: bytes):
        # First packet is SerialiserVersion
        # Packet ID for SerialiserVersion packet type is 0
        self.assertEqual(0, struct.unpack('<I', buff[0:4])[0])
        # Length for SerialiserVersion packet type is 22
        self.assertEqual(22, struct.unpack('<I', buff[4:8])[0])
        # Major version in bytes 7-8, equals 1
        self.assertEqual(1, struct.unpack('<H', buff[8:10])[0])
        # Minor version in bytes 9-10, equals 0
        self.assertEqual(3, struct.unpack('<H', buff[10:12])[0])
        # NMEA2000 major version in bytes 11-12, equals 1
        self.assertEqual(1, struct.unpack('<H', buff[12:14])[0])
        # NMEA2000 minor version in bytes 13-14, equals 0
        self.assertEqual(1, struct.unpack('<H', buff[14:16])[0])
        # NMEA2000 patch version in bytes 15-16, equals 0
        self.assertEqual(0, struct.unpack('<H', buff[16:18])[0])
        # NMEA0183 major version in bytes 17-18, equals 1
        self.assertEqual(1, struct.unpack('<H', buff[18:20])[0])
        # NMEA0183 minor version in bytes 19-20, equals 0
        self.assertEqual(0, struct.unpack('<H', buff[20:22])[0])
        # NMEA0183 patch version in bytes 21-22, equals 0
        self.assertEqual(1, struct.unpack('<H', buff[22:24])[0])
        # IMU major version in bytes 23-24, equals 1
        self.assertEqual(1, struct.unpack('<H', buff[24:26])[0])
        # IMU minor version in bytes 25-26, equals 0
        self.assertEqual(0, struct.unpack('<H', buff[26:28])[0])
        # IMU patch version in bytes 27-28, equals 0
        self.assertEqual(0, struct.unpack('<H', buff[28:30])[0])

        # Second packet is Metadata
        # Packet ID for Metadata packet type is 12
        self.assertEqual(12, struct.unpack('<I', buff[30:34])[0])
        # Length for this Metadata packet is 35
        self.assertEqual(35, struct.unpack('<I', buff[34:38])[0])
        # Logger name length in bytes 37-40, equals 13
        self.assertEqual(13, struct.unpack('<I', buff[38:42])[0])
        # Logger name in bytes 41-53, equals 'Gulf Surveyor'
        self.assertEqual('Gulf Surveyor', struct.unpack('<13s', buff[42:55])[0].decode('UTF-8'))
        # Logger ID length in bytes 54-57, equals 14
        self.assertEqual(14, struct.unpack('<I', buff[55:59])[0])
        # Logger ID in bytes 58-71, equals 'WIBL-Simulator'
        self.assertEqual('WIBL-Simulator', struct.unpack('<14s', buff[59:73])[0].decode('UTF-8'))

    def test_generate_gga(self):
        state: State = State()
        # Simulate first position after initial position step
        state.current_longitude = -74.999996729200006
        state.current_latitude = 43.000003270800001
        # Simulate first time after initial time step
        state.update_ticks(300536)
        state.ref_time.update(state.curr_ticks)
        state.sim_time.update(math.floor(state.curr_ticks / 2))
        gen: DataGenerator = DataGenerator(use_data_constructor=True, logger_file_version='1.3')

        writer: Writer = MemoryWriter('Gulf Surveyor', 'WIBL-Simulator',
                                      logger_file_version='1.3')
        gen.generate_gga(state, writer)

        buff: bytes = writer.getvalue()
        self.assertIsNotNone(buff)
        self.__test_header_packets(buff)

        # Message type in bytes 72-75
        self.assertEqual(PacketTypes.SerialString.value, struct.unpack('<I', buff[73:77])[0])
        # Message length in bytes 75-79
        self.assertEqual(88, struct.unpack('<I', buff[77:81])[0])
        # Days since epoch from bytes 80-83
        self.assertEqual(state.sim_time.tick_count_to_milliseconds(), struct.unpack('<I', buff[81:85])[0])

        # First byte of message body is '$' = ASCII 36 (decimal)
        self.assertEqual(36, buff[85])
        # Message descriptor: GPGGA
        # G = 71
        self.assertEqual(71, buff[86])
        # P = 80
        self.assertEqual(80, buff[87])
        self.assertEqual(71, buff[88])
        self.assertEqual(71, buff[89])
        # A = 65
        self.assertEqual(65, buff[90])
        # Component separator is , = 44
        self.assertEqual(44, buff[91])
        # Hour, minute, and decimal seconds (all initially ASCII 0=48 decimal)
        self.assertEqual(48, buff[92])
        self.assertEqual(48, buff[93])
        self.assertEqual(48, buff[94])
        self.assertEqual(48, buff[95])
        # Seconds '00.500'
        self.assertEqual(48, buff[96])
        # '0' = 48
        self.assertEqual(48, buff[97])
        # '.' = 46
        self.assertEqual(46, buff[98])
        # Decimal part of seconds
        # '1' = 49
        self.assertEqual(49, buff[99])
        # '5' = 53
        self.assertEqual(53, buff[100])
        # '0' = 48
        self.assertEqual(48, buff[101])
        # Component separator is , = 44
        self.assertEqual(44, buff[102])
        # Beginning of latitude: 43 degrees, 00.000003 minutes/seconds (in ASCII)
        self.assertEqual(52, buff[103])
        self.assertEqual(51, buff[104])
        self.assertEqual(48, buff[105])
        self.assertEqual(48, buff[106])
        # . = 46
        self.assertEqual(46, buff[107])
        self.assertEqual(48, buff[108])
        self.assertEqual(48, buff[109])
        self.assertEqual(48, buff[110])
        self.assertEqual(48, buff[111])
        self.assertEqual(48, buff[112])
        # 3 = 51
        self.assertEqual(51, buff[113])
        # Component separator is , = 44
        self.assertEqual(44, buff[114])
        # N (North) = 78
        self.assertEqual(78, buff[115])
        # Component separator is , = 44 (end of latitude)
        self.assertEqual(44, buff[116])
        # Beginning of longitude: 074 degrees, 00.999997 minutes/seconds (in ASCII)
        self.assertEqual(48, buff[117])
        # 7 = 55
        self.assertEqual(55, buff[118])
        # 4 = 52
        self.assertEqual(52, buff[119])
        self.assertEqual(48, buff[120])
        self.assertEqual(48, buff[121])
        # . = 46
        self.assertEqual(46, buff[122])
        # 9 = 57
        self.assertEqual(57, buff[123])
        self.assertEqual(57, buff[124])
        self.assertEqual(57, buff[125])
        self.assertEqual(57, buff[126])
        self.assertEqual(57, buff[127])
        # 7 = 55
        self.assertEqual(55, buff[128])
        # Component separator is , = 44
        self.assertEqual(44, buff[129])
        # W (West) = 87
        self.assertEqual(87, buff[130])
        # Component separator is , = 44
        self.assertEqual(44, buff[131])
        # Dummy part of message: 3,12,1.0,-19.5,M,22.5,M,0.0,0000*
        # '3'
        self.assertEqual(51, buff[132])
        # Component separator is , = 44
        self.assertEqual(44, buff[133])
        # '12'
        self.assertEqual(49, buff[134])
        self.assertEqual(50, buff[135])
        # Component separator is , = 44
        self.assertEqual(44, buff[136])
        # '1.0'
        self.assertEqual(49, buff[137])
        self.assertEqual(46, buff[138])
        self.assertEqual(48, buff[139])
        # Component separator is , = 44
        self.assertEqual(44, buff[140])
        # '-19.5'
        self.assertEqual(45, buff[141])
        self.assertEqual(49, buff[142])
        self.assertEqual(57, buff[143])
        self.assertEqual(46, buff[144])
        self.assertEqual(53, buff[145])
        # Component separator is , = 44
        self.assertEqual(44, buff[146])
        # 'M'
        self.assertEqual(77, buff[147])
        # Component separator is , = 44
        self.assertEqual(44, buff[148])
        # '22.5'
        self.assertEqual(50, buff[149])
        self.assertEqual(50, buff[150])
        self.assertEqual(46, buff[151])
        self.assertEqual(53, buff[152])
        # Component separator is , = 44
        self.assertEqual(44, buff[153])
        # 'M'
        self.assertEqual(77, buff[154])
        # Component separator is , = 44
        self.assertEqual(44, buff[155])
        # '0.0'
        self.assertEqual(48, buff[156])
        self.assertEqual(46, buff[157])
        self.assertEqual(48, buff[158])
        # Component separator is , = 44
        self.assertEqual(44, buff[159])
        # '0000*'
        self.assertEqual(48, buff[160])
        self.assertEqual(48, buff[161])
        self.assertEqual(48, buff[162])
        self.assertEqual(48, buff[163])
        self.assertEqual(42, buff[164])
        # Checksum: '78'
        self.assertEqual(b'78', buff[165:167])
        # End of message: '\r\n'
        self.assertEqual(b'\r\n', buff[167:170])

        with self.assertRaises(IndexError):
            buff[170]

    def test_generate_gga_compare(self):
        """
        Compare results from buffer vs. data constructor for GGA SerialString packet
        :return:
        """
        state: State = State()
        # Simulate first position after initial position step
        state.current_longitude = -74.999996729200006
        state.current_latitude = 43.000003270800001
        # Simulate first time after initial time step
        state.update_ticks(300536)
        state.ref_time.update(state.curr_ticks)
        state.sim_time.update(math.floor(state.curr_ticks / 2))

        gen_data_const: DataGenerator = DataGenerator(use_data_constructor=True, logger_file_version='1.3')
        writer_data_const: Writer = MemoryWriter('Gulf Surveyor', 'WIBL-Simulator',
                                                 logger_file_version='1.3')
        gen_data_const.generate_gga(state, writer_data_const)
        buff_data_const: bytes = writer_data_const.getvalue()

        gen_buff_const: DataGenerator = DataGenerator(use_data_constructor=False, logger_file_version='1.3')
        writer_buff_const: Writer = MemoryWriter('Gulf Surveyor', 'WIBL-Simulator',
                                                 logger_file_version='1.3')
        gen_buff_const.generate_gga(state, writer_buff_const)
        buff_buff_const: bytes = writer_buff_const.getvalue()

        self.assertEqual(buff_data_const, buff_buff_const)

    def test_generate_system_time(self):
        state: State = State()
        # Simulate first time after initial time step
        state.update_ticks(300536)
        state.ref_time.update(state.curr_ticks)
        gen: DataGenerator = DataGenerator(use_data_constructor=True,
                                           logger_file_version='1.3')

        writer: Writer = MemoryWriter('Gulf Surveyor', 'WIBL-Simulator',
                                      logger_file_version='1.3')
        gen.generate_system_time(state, writer)

        buff: bytes = writer.getvalue()
        self.assertIsNotNone(buff)
        self.__test_header_packets(buff)

        # Message type in bytes 72-75
        self.assertEqual(PacketTypes.SystemTime.value, struct.unpack('<I', buff[73:77])[0])
        # Message length in bytes 76-79
        self.assertEqual(15, struct.unpack('<I', buff[77:81])[0])
        # Days since epoch from bytes 80-81
        self.assertEqual(18262, struct.unpack('<H', buff[81:83])[0])
        # Read timestamp from bytes 82-89
        self.assertEqual(0.300536, struct.unpack('<d', buff[83:91])[0])
        # Elapsed time should equal state.tick_count_to_milliseconds()
        self.assertEqual(state.tick_count_to_milliseconds(), struct.unpack('<I', buff[91:95])[0])
        # Data source is the final byte (23) and should be 0 for now
        self.assertEqual(0, buff[95])

        with self.assertRaises(IndexError):
            buff[96]

    def test_generate_system_time_compare(self):
        """
        Compare results from buffer vs. data constructor for SystemTime packet
        :return:
        """
        state: State = State()
        # Simulate first time after initial time step
        state.update_ticks(300536)
        state.ref_time.update(state.curr_ticks)

        gen_data_const: DataGenerator = DataGenerator(use_data_constructor=True,
                                                      logger_file_version='1.3')
        writer_data_const: Writer = MemoryWriter('Gulf Surveyor', 'WIBL-Simulator',
                                                 logger_file_version='1.3')
        gen_data_const.generate_system_time(state, writer_data_const)
        buff_data_const: bytes = writer_data_const.getvalue()

        gen_buffer_const: DataGenerator = DataGenerator(use_data_constructor=False,
                                                        logger_file_version='1.3')
        writer_buffer_const: Writer = MemoryWriter('Gulf Surveyor', 'WIBL-Simulator',
                                                   logger_file_version='1.3')
        gen_buffer_const.generate_system_time(state, writer_buffer_const)
        buff_buffer_const: bytes = writer_buffer_const.getvalue()

        self.assertEqual(buff_data_const, buff_buffer_const)

    def test_generate_attitude(self):
        state: State = State()
        # Simulate first time after initial time step
        state.update_ticks(300536)
        state.ref_time.update(state.curr_ticks)
        gen: DataGenerator = DataGenerator(use_data_constructor=True, logger_file_version='1.3')

        writer: Writer = MemoryWriter('Gulf Surveyor', 'WIBL-Simulator',
                                      logger_file_version='1.3')
        gen.generate_attitude(state, writer)

        buff: bytes = writer.getvalue()
        self.assertIsNotNone(buff)
        self.__test_header_packets(buff)

        # Message type in bytes 72-75
        self.assertEqual(PacketTypes.Attitude.value, struct.unpack('<I', buff[73:77])[0])
        # Message length in bytes 76-79
        self.assertEqual(38, struct.unpack('<I', buff[77:81])[0])
        # Days since epoch from bytes 80-81
        self.assertEqual(18262, struct.unpack('<H', buff[81:83])[0])
        # Read timestamp from bytes 82-89
        self.assertEqual(0.300536, struct.unpack('<d', buff[83:91])[0])
        # Elapsed time should equal state.tick_count_to_milliseconds()
        self.assertEqual(state.tick_count_to_milliseconds(), struct.unpack('<I', buff[91:95])[0])
        # Read yaw from bytes 94-101
        yaw = struct.unpack('<d', buff[95:103])[0]
        self.assertGreaterEqual(yaw, 0)
        self.assertLessEqual(yaw, MAX_RAD)
        # Read pitch from bytes 102-109
        pitch = struct.unpack('<d', buff[103:111])[0]
        self.assertGreaterEqual(pitch, 0)
        self.assertLessEqual(pitch, MAX_RAD)
        # Read roll from bytes 110-117
        roll = struct.unpack('<d', buff[111:119])[0]
        self.assertGreaterEqual(roll, 0)
        self.assertLessEqual(roll, MAX_RAD)

        with self.assertRaises(IndexError):
            buff[119]

    def test_generate_attitude_compare(self):
        """
        Compare results from buffer vs. data constructor for Attitude packet
        :return:
        """
        state: State = State()
        # Simulate first time after initial time step
        state.update_ticks(300536)
        state.ref_time.update(state.curr_ticks)

        gen_data_const: DataGenerator = DataGenerator(use_data_constructor=True, logger_file_version='1.3')
        writer_data_const: Writer = MemoryWriter('Gulf Surveyor', 'WIBL-Simulator',
                                                 logger_file_version='1.3')
        gen_data_const.generate_attitude(state, writer_data_const)
        buff_data_const: bytes = writer_data_const.getvalue()

        gen_buffer_const: DataGenerator = DataGenerator(use_data_constructor=False, logger_file_version='1.3')
        writer_buffer_const: Writer = MemoryWriter('Gulf Surveyor', 'WIBL-Simulator',
                                                   logger_file_version='1.3')
        gen_buffer_const.generate_attitude(state, writer_buffer_const)
        buff_buffer_const: bytes = writer_buffer_const.getvalue()

        self.assertEqual(buff_data_const, buff_buffer_const)

    def test_generate_gnss(self):
        state: State = State()
        # Simulate first time after initial time step
        state.update_ticks(300536)
        state.ref_time.update(state.curr_ticks)
        state.sim_time.update(math.floor(state.curr_ticks / 2))
        # Simulate first position after initial position step
        state.current_longitude = -74.999996729200006
        state.current_latitude = 43.000003270800001
        gen: DataGenerator = DataGenerator(use_data_constructor=True, logger_file_version='1.3')

        writer: Writer = MemoryWriter('Gulf Surveyor', 'WIBL-Simulator',
                                      logger_file_version='1.3')
        gen.generate_gnss(state, writer)

        buff: bytes = writer.getvalue()
        self.assertIsNotNone(buff)
        self.__test_header_packets(buff)

        # Message type in bytes 72-75
        self.assertEqual(PacketTypes.GNSS.value, struct.unpack('<I', buff[73:77])[0])
        # Message length in bytes 76-79
        self.assertEqual(87, struct.unpack('<I', buff[77:81])[0])
        # Days since epoch from bytes 80-81
        self.assertEqual(18262, struct.unpack('<H', buff[81:83])[0])
        # Read timestamp from bytes 82-89
        self.assertEqual(0.150268, struct.unpack('<d', buff[83:91])[0])
        # Elapsed time should equal state.tick_count_to_milliseconds()
        self.assertEqual(state.sim_time.tick_count_to_milliseconds(), struct.unpack('<I', buff[91:95])[0])

        # Message date should equal state.sim_time.days_since_epoch()
        self.assertEqual(state.sim_time.days_since_epoch(), struct.unpack('<H', buff[95:97])[0])
        # Message timestamp = state.sim_time.seconds_in_day()
        self.assertEqual(state.sim_time.seconds_in_day(), struct.unpack('<d', buff[97:105])[0])
        # Latitude
        self.assertEqual(state.current_latitude, struct.unpack('<d', buff[105:113])[0])
        # Longitude
        self.assertEqual(state.current_longitude, struct.unpack('<d', buff[113:121])[0])
        # Hard-coded altitude
        self.assertEqual(-19.323, struct.unpack('<d', buff[121:129])[0])
        # Hard-coded rx_type
        self.assertEqual(0, buff[129])
        # Hard-coded rx_method
        self.assertEqual(2, buff[130])
        # Hard-coded num SVs
        self.assertEqual(12, buff[131])
        # Hard-coded horizontal DOP
        self.assertEqual(1.5, struct.unpack('<d', buff[132:140])[0])
        # Hard-coded position DOP
        self.assertEqual(2.2, struct.unpack('<d', buff[140:148])[0])
        # Hard-coded sep
        self.assertEqual(22.3453, struct.unpack('<d', buff[148:156])[0])
        # Hard-coded n_refs
        self.assertEqual(1, buff[156])
        # Hard-coded refs_type
        self.assertEqual(4, buff[157])
        # Hard-coded refs_id
        self.assertEqual(12312, struct.unpack('<H', buff[158:160])[0])
        # Hard-coded correction_age
        self.assertEqual(2.32, struct.unpack('<d', buff[160:168])[0])

        with self.assertRaises(IndexError):
            buff[168]

    def test_generate_gnss_compare(self):
        """
        Compare results from buffer vs. data constructor for GNSS packet
        :return:
        """
        state: State = State()
        # Simulate first time after initial time step
        state.update_ticks(300536)
        state.ref_time.update(state.curr_ticks)
        state.sim_time.update(math.floor(state.curr_ticks / 2))
        # Simulate first position after initial position step
        state.current_longitude = -74.999996729200006
        state.current_latitude = 43.000003270800001

        gen_data_const: DataGenerator = DataGenerator(use_data_constructor=True,
                                                      logger_file_version='1.3')
        writer_data_const: Writer = MemoryWriter('Gulf Surveyor', 'WIBL-Simulator',
                                                 logger_file_version='1.3')
        gen_data_const.generate_gnss(state, writer_data_const)
        buff_data_const: bytes = writer_data_const.getvalue()

        gen_buff_const: DataGenerator = DataGenerator(use_data_constructor=False,
                                                      logger_file_version='1.3')
        writer_buff_const: Writer = MemoryWriter('Gulf Surveyor', 'WIBL-Simulator',
                                                 logger_file_version='1.3')
        gen_buff_const.generate_gnss(state, writer_buff_const)
        buff_buff_const: bytes = writer_buff_const.getvalue()

        self.assertEqual(buff_data_const, buff_buff_const)

    def test_generate_depth(self):
        state: State = State()
        # Simulate first time after initial time step
        state.update_ticks(300536)
        state.ref_time.update(state.curr_ticks)
        gen: DataGenerator = DataGenerator(use_data_constructor=True, logger_file_version='1.3')

        writer: Writer = MemoryWriter('Gulf Surveyor', 'WIBL-Simulator',
                                      logger_file_version='1.3')
        gen.generate_depth(state, writer)

        buff: bytes = writer.getvalue()
        self.assertIsNotNone(buff)
        self.__test_header_packets(buff)

        # Message type in bytes 72-75
        self.assertEqual(PacketTypes.Depth.value, struct.unpack('<I', buff[73:77])[0])
        # Message length in bytes 76-79
        self.assertEqual(38, struct.unpack('<I', buff[77:81])[0])
        # Days since epoch from bytes 80-81
        self.assertEqual(18262, struct.unpack('<H', buff[81:83])[0])
        # Read timestamp from bytes 82-89
        self.assertEqual(0.0, struct.unpack('<d', buff[83:91])[0])
        # Elapsed time should equal state.tick_count_to_milliseconds()
        self.assertEqual(state.sim_time.tick_count_to_milliseconds(), struct.unpack('<I', buff[91:95])[0])

        # Depth should equal state.current_depth
        self.assertEqual(state.current_depth, struct.unpack('<d', buff[95:103])[0])
        # Hard-coded offset
        self.assertEqual(0.0, struct.unpack('<d', buff[103:111])[0])
        # Hard-coded range
        self.assertEqual(200.0, struct.unpack('<d', buff[111:119])[0])

        with self.assertRaises(IndexError):
            buff[119]

    def test_generate_depth_compare(self):
        """
        Compare results from buffer vs. data constructor for Depth packet
        :return:
        """
        state: State = State()
        # Simulate first time after initial time step
        state.update_ticks(300536)
        state.ref_time.update(state.curr_ticks)

        gen_data_const: DataGenerator = DataGenerator(use_data_constructor=True, logger_file_version='1.3')
        writer_data_const: Writer = MemoryWriter('Gulf Surveyor', 'WIBL-Simulator',
                                                 logger_file_version='1.3')
        gen_data_const.generate_depth(state, writer_data_const)
        buff_data_const: bytes = writer_data_const.getvalue()

        gen_buff_const: DataGenerator = DataGenerator(use_data_constructor=False, logger_file_version='1.3')
        writer_buff_const: Writer = MemoryWriter('Gulf Surveyor', 'WIBL-Simulator',
                                                 logger_file_version='1.3')
        gen_buff_const.generate_depth(state, writer_buff_const)
        buff_buff_const: bytes = writer_data_const.getvalue()

        self.assertEqual(buff_data_const, buff_buff_const)

    def test_generate_zda(self):
        state: State = State()
        # Simulate first position after initial position step
        state.current_longitude = -74.999996729200006
        state.current_latitude = 43.000003270800001
        # Simulate first time after initial time step
        state.update_ticks(300536)
        state.ref_time.update(state.curr_ticks)
        state.sim_time.update(math.floor(state.curr_ticks / 2))
        gen: DataGenerator = DataGenerator(use_data_constructor=True, logger_file_version='1.3')

        writer: Writer = MemoryWriter('Gulf Surveyor', 'WIBL-Simulator',
                                      logger_file_version='1.3')
        gen.generate_zda(state, writer)

        buff: bytes = writer.getvalue()
        self.assertIsNotNone(buff)
        self.__test_header_packets(buff)

        # Message type in bytes 72-75
        self.assertEqual(PacketTypes.SerialString.value, struct.unpack('<I', buff[73:77])[0])
        # Message length in bytes 76-79
        self.assertEqual(43, struct.unpack('<I', buff[77:81])[0])
        # Days since epoch from bytes 80-83
        self.assertEqual(state.sim_time.tick_count_to_milliseconds(), struct.unpack('<I', buff[81:85])[0])

        # First byte of message body is '$' = ASCII 36 (decimal)
        self.assertEqual(36, buff[85])
        # Message descriptor: GPZDA
        # G = 71
        self.assertEqual(71, buff[86])
        # P = 80
        self.assertEqual(80, buff[87])
        # Z = 90
        self.assertEqual(90, buff[88])
        # D = 68
        self.assertEqual(68, buff[89])
        # A = 65
        self.assertEqual(65, buff[90])
        # Component separator is , = 44
        self.assertEqual(44, buff[91])
        # Hour, minute, and decimal seconds (all initially ASCII 0=48 decimal)
        self.assertEqual(48, buff[92])
        self.assertEqual(48, buff[93])
        self.assertEqual(48, buff[94])
        self.assertEqual(48, buff[95])
        # Seconds '00.150'
        self.assertEqual(48, buff[96])
        # '0' = 48
        self.assertEqual(48, buff[97])
        # '.' = 46
        self.assertEqual(46, buff[98])
        # Decimal part of seconds
        # '1' = 49
        self.assertEqual(49, buff[99])
        # '5' = 53
        self.assertEqual(53, buff[100])
        # '0' = 48
        self.assertEqual(48, buff[101])
        # Component separator is , = 44
        self.assertEqual(44, buff[102])
        # Month day is '01'
        self.assertEqual(b'01', buff[103:105])
        # Component separator is , = 44
        self.assertEqual(44, buff[105])
        # Month is '01'
        self.assertEqual(b'01', buff[106:108])
        # Component separator is , = 44
        self.assertEqual(44, buff[108])
        # Year is '2020'
        self.assertEqual(b'2020', buff[109:113])
        # Component separator is , = 44
        self.assertEqual(44, buff[113])
        # End of message is hard-coded with '00,00*'
        self.assertEqual(b'00,00*', buff[114:120])
        # Checksum: '52'
        self.assertEqual(b'52', buff[120:122])
        # End of message: '\r\n'
        self.assertEqual(b'\r\n', buff[122:124])

        with self.assertRaises(IndexError):
            buff[124]

    def test_generate_zda_compare(self):
        """
        Compare results from buffer vs. data constructor for ZDA SerialString packet
        :return:
        """
        state: State = State()
        # Simulate first position after initial position step
        state.current_longitude = -74.999996729200006
        state.current_latitude = 43.000003270800001
        # Simulate first time after initial time step
        state.update_ticks(300536)
        state.ref_time.update(state.curr_ticks)
        state.sim_time.update(math.floor(state.curr_ticks / 2))

        gen_data_const: DataGenerator = DataGenerator(use_data_constructor=True, logger_file_version='1.3')
        writer_data_const: Writer = MemoryWriter('Gulf Surveyor', 'WIBL-Simulator',
                                                 logger_file_version='1.3')
        gen_data_const.generate_zda(state, writer_data_const)
        buff_data_const: bytes = writer_data_const.getvalue()

        gen_buff_const: DataGenerator = DataGenerator(use_data_constructor=False, logger_file_version='1.3')
        writer_buff_const: Writer = MemoryWriter('Gulf Surveyor', 'WIBL-Simulator',
                                                 logger_file_version='1.3')
        gen_buff_const.generate_zda(state, writer_buff_const)
        buff_buff_const: bytes = writer_buff_const.getvalue()

        self.assertEqual(buff_data_const, buff_buff_const)

    def test_generate_dbt(self):
        state: State = State()
        # Simulate first position after initial position step
        state.current_longitude = -74.999996729200006
        state.current_latitude = 43.000003270800001
        # Simulate first time after initial time step
        state.update_ticks(300536)
        state.ref_time.update(state.curr_ticks)
        state.sim_time.update(math.floor(state.curr_ticks / 2))
        gen: DataGenerator = DataGenerator(use_data_constructor=True, logger_file_version='1.3')

        writer: Writer = MemoryWriter('Gulf Surveyor', 'WIBL-Simulator',
                                      logger_file_version='1.3')
        gen.generate_dbt(state, writer, override_depth=10.0)

        buff: bytes = writer.getvalue()
        self.assertIsNotNone(buff)
        self.__test_header_packets(buff)

        # Message type in bytes 72-75
        self.assertEqual(PacketTypes.SerialString.value, struct.unpack('<I', buff[73:77])[0])
        # Message length in bytes 76-79
        # Length may vary a bit due to random depth values, so let's just make sure it's a valid int
        exc_raised = False
        try:
            msg_len = int(struct.unpack('<I', buff[77:81])[0])
        except ValueError:
            exc_raised = True
        self.assertFalse(exc_raised)
        # Days since epoch from bytes 80-83
        self.assertEqual(state.sim_time.tick_count_to_milliseconds(), struct.unpack('<I', buff[81:85])[0])

        # First byte of message body is '$' = ASCII 36 (decimal)
        self.assertEqual(36, buff[85])
        # Message descriptor: SDDBT
        # S = 83
        self.assertEqual(83, buff[86])
        # D = 68
        self.assertEqual(68, buff[87])
        # D = 68
        self.assertEqual(68, buff[88])
        # B = 66
        self.assertEqual(66, buff[89])
        # T = 84
        self.assertEqual(84, buff[90])
        # Component separator is , = 44
        self.assertEqual(44, buff[91])

        # Depth in feet
        self.assertEqual(32.8, float(buff[92:96]))
        # Component separator is , = 44
        self.assertEqual(44, buff[96])
        # Unit: 'f' = 102
        self.assertEqual(102, buff[97])
        # Component separator is , = 44
        self.assertEqual(44, buff[98])

        # Depth in metres
        exc_raised = False
        self.assertEqual(10.0, float(buff[99:103]))
        # Component separator is , = 44
        self.assertEqual(44, buff[103])
        # Unit: 'M' = 77
        self.assertEqual(77, buff[104])
        # Component separator is , = 44
        self.assertEqual(44, buff[105])

        # Depth in fathoms
        self.assertEqual(5.5, float(buff[106:109]))
        # Component separator is , = 44
        self.assertEqual(44, buff[109])
        # Unit and message end: 'F*'
        self.assertEqual(b'F*', buff[110:112])

        # Checksum
        self.assertEqual(14, int(buff[112:114], 16))
        # End of message: '\r\n'
        self.assertEqual(b'\r\n', buff[114:116])

        with self.assertRaises(IndexError):
            buff[116]

    def test_generate_dbt_compare(self):
        """
        Compare results from buffer vs. data constructor for DBT SerialString packet
        :return:
        """
        state: State = State()
        # Simulate first position after initial position step
        state.current_longitude = -74.999996729200006
        state.current_latitude = 43.000003270800001
        # Simulate first time after initial time step
        state.update_ticks(300536)
        state.ref_time.update(state.curr_ticks)
        state.sim_time.update(math.floor(state.curr_ticks / 2))

        gen_data_const: DataGenerator = DataGenerator(use_data_constructor=True, logger_file_version='1.3')
        writer_data_const: Writer = MemoryWriter('Gulf Surveyor', 'WIBL-Simulator',
                                                 logger_file_version='1.3')
        gen_data_const.generate_dbt(state, writer_data_const, override_depth=10.0)
        buff_data_const: bytes = writer_data_const.getvalue()

        gen_buff_const: DataGenerator = DataGenerator(use_data_constructor=False, logger_file_version='1.3')
        writer_buff_const: Writer = MemoryWriter('Gulf Surveyor', 'WIBL-Simulator',
                                                 logger_file_version='1.3')
        gen_buff_const.generate_dbt(state, writer_buff_const, override_depth=10.0)
        buff_buff_const: bytes = writer_buff_const.getvalue()

        self.assertEqual(buff_data_const, buff_buff_const)


if __name__ == '__main__':
    unittest.main(
        testRunner=xmlrunner.XMLTestRunner(output='test-reports'),
        failfast=False, buffer=False, catchbreak=False
    )
