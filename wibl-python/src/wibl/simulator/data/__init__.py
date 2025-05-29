##\file __init__.py
# \brief WIBL data simulator.
#
# Copyright 2022 Center for Coastal and Ocean Mapping & NOAA-UNH Joint
# Hydrographic Center, University of New Hampshire.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights to use,
# copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE
# OR OTHER DEALINGS IN THE SOFTWARE.

import math
from typing import NamedTuple, NoReturn, Union, TypeVar, Tuple, Any
from datetime import datetime, date, timedelta
import binascii
import struct
import random
import logging


import wibl.core.logger_file as lf
from wibl.simulator.data.writer import Writer


logger = logging.getLogger(__name__)


CLOCKS_PER_SEC = 1_000_000
EPOCH_START = datetime(1970, 1, 1)
MAX_RAND = (1 << 31) - 1
MAX_RAD = math.pi * 2
DUMMY_YAW = random.random() * MAX_RAD
DUMMY_PITCH = random.random() * MAX_RAD
DUMMY_ROLL = random.random() * MAX_RAD
NA_DATA_DOUBLE: float = -1e9
NA_DATA_UINT32: int = 0xFFFFFFFF


def unit_uniform() -> float:
    return random.uniform(0, MAX_RAND) / MAX_RAND


class FormattedAngle(NamedTuple):
    """
    Break an angle in degrees into the components required to format for ouptut
    in a NMEA0183 GGA message (i.e., integer degrees and decimal minutes, with an
    indicator for which hemisphere to use).  To allow this to be uniform, the code
    assumes a positive angle is hemisphere 1, and negative angle hemisphere 0.  It's
    up to the caller to decide what decorations are used for those in the display.
    """
    # Reference to space for the integer part of the angle (degrees)
    degrees: int
    # Reference to space for the decimal minutes part of the angle
    minutes: float
    # Reference to space for a hemisphere indicator
    hemisphere: int


def format_angle(angle: float) -> FormattedAngle:
    """
    Convert an angle in decimal degrees into integer degrees and decimal minutes, with hemispehere indicator
    :param angle:
    :return: FormattedAngle
    """
    if angle > 0.0:
        out_hemi = 1
        out_angle = angle
    else:
        out_hemi = 0
        out_angle = -angle

    out_degrees = int(out_angle)
    out_minutes = out_angle - out_degrees

    return FormattedAngle(degrees=out_degrees, minutes=out_minutes, hemisphere=out_hemi)


class TickCountMillisecondsMixin:
    def tick_count_to_milliseconds(self) -> int:
        """
        Convert from internal count to milliseconds
        :param count:
        :return:
        """
        # Conversion factor = 1000 / CLOCKS_PER_SEC
        return int(self.tick_count * 0.001)


class ComponentDateTime(TickCountMillisecondsMixin):
    """
    POD structure to maintain the broken-out components associated with a date-time

    The simulator has to be able to record a current time of the system state, which is modelled
    as a number of ticks of the system clock since the Unix epoch.  The class also allows for this
    information to be converted into a number of different formats as required by the NMEA0183 and
    NMEA2000 packets.
    """
    def __init__(self, tick_count: int, *,
                 datetime_timestamp: int = None):
        """

        :param tick_count:
        """
        if datetime_timestamp:
            self._dt: datetime = datetime.utcfromtimestamp(datetime_timestamp)
        else:
            self._dt: datetime = datetime(2020, 1, 1, 0, 0, 0, 0)
        self.tick_count = tick_count
        self._init_time_ticks: int = tick_count
        self._init_time_sec: int = int(self._init_time_ticks / CLOCKS_PER_SEC)

    @property
    def year(self):
        """
        Converted Gregorian year
        :return:
        """
        return self._dt.year if self._dt else None

    @property
    def month(self):
        """
        Month of year
        :return:
        """
        return self._dt.month if self._dt else None

    @property
    def day(self):
        """
        Day of month
        :return:
        """
        return self._dt.day if self._dt else None

    @property
    def day_of_year(self):
        """
        Day of the current time within the year
        :return:
        """
        if self._dt:
            return (self._dt.date() - date(self._dt.year, 1, 1)).days
        return None

    @property
    def hour(self):
        """
        Hour of the current time with the day-of-year
        :return:
        """
        return self._dt.hour if self._dt else None

    @property
    def minute(self):
        """
        Minute of the current time within the hour
        :return:
        """
        return self._dt.minute if self._dt else None

    @property
    def second(self):
        """
        Second (with fractions) of the current time within the minute
        :return:
        """
        if self._dt:
            return float(self._dt.second) + (self._dt.microsecond / 1000000)
        return None

    def update(self, new_count: int):
        """
        Set the current time (in clock ticks)
        :param new_count:
        :return:
        """
        delta_tics = new_count - self.tick_count
        delta_sec = delta_tics / CLOCKS_PER_SEC
        delta = timedelta(seconds=delta_sec)
        self._dt = self._dt + delta
        self.tick_count = new_count

    def days_since_epoch(self) -> int:
        """
        Compute and return the number of days since Unix epoch for the current time
        :return:
        """
        return (self._dt - EPOCH_START).days

    def seconds_in_day(self) -> float:
        """
        Compute and return the total number of seconds for the current time since midnight
        :return:
        """
        begining_of_day = datetime(self._dt.year, self._dt.month, self._dt.day)
        delta = self._dt - begining_of_day
        return delta.seconds + (delta.microseconds / 1_000_000)

    def time(self):
        """
        Convert the current time into a TimeDatum for use in data construction
        :return: ?! Timestamp::TimeDatum but maybe just Python datetime !?
        """
        pass


class State(TickCountMillisecondsMixin):
    def __init__(self):
        """
        State objects should only be constructed from within Engine
        """
        # Current timestamp for the simulation
        # self.init_ticks: int = get_clock_ticks()
        self.init_ticks: int = 0
        self.curr_ticks: int = self.init_ticks
        self.tick_count: int = 0
        self.sim_time: ComponentDateTime = ComponentDateTime(self.tick_count)
        # Depth in metres
        self.current_depth: float = 10.0
        # Depth sounder measurement uncertainty, std. dev.
        self.measurement_uncertainty: float = 0.06
        # Reference timestamp for the ZDA/SystemTime
        self.ref_time: ComponentDateTime = ComponentDateTime(self.tick_count)
        # Longitude in degrees
        self.current_longitude: float = -70.0
        # Latitude in degress
        self.current_latitude: float = 43.0

        # Next clock tick count at which to update reference time state
        self.target_reference_time: int = 0
        # Next clock tick count at which to update depth state
        self.target_depth_time: int = 0
        # Next clock tick count at which to update position state
        self.target_position_time: int = 0

        # Standard deviation, metres change in one second
        self.depth_random_walk: float = 0.02

        # Change in latitude/longitude per second
        self.position_step: float = 3.2708e-06
        # Current direction of latitude change
        self.latitude_scale: float = 1.0
        # Last time the latitude changed direction
        self.last_latitude_reversal: float = 0.0

        # Global for Gaussian variate generator (from Numerical Recipies)
        self._iset: bool = False
        # Global state for Gaussian variate generator (from Numerical Recipies)
        self._gset: float = None

    def update_ticks(self, ticks: int) -> NoReturn:
        self.curr_ticks = ticks
        self.tick_count = self.curr_ticks - self.init_ticks

    def unit_normal(self) -> float:
        fac: float; rsq: float; v1: float; v2: float
        u: float; v: float; r: float

        if not self._iset:
            while True:
                u = unit_uniform()
                v = unit_uniform()
                v1 = 2.0 * u - 1.0
                v2 = 2.0 * v - 1.0
                rsq = v1 * v1 + v2 * v2
                if not (rsq >= 1.0 or rsq == 0.0):
                    break
            fac = math.sqrt(-2.0 * math.log(rsq) / rsq)
            self._gset = v1 * fac
            self._iset = True
            r = v2 * fac
        else:
            self._iset = False
            r = self._gset

        return r


class DataGenerator:
    """
    Encapsulate the requirements for generating NMEA data logged in binary format

    This provides a reference mechanism for generate NMEA messages from the simulator, and writing
    them into the output data file in the appropriate format.  This includes NMEA2000 and NMEA0183 data
    messages for the same position, time, and depths, so that the output data file is consistent with either
    data source.
    """
    def __init__(self, emit_nmea0183: bool = True, emit_nmea2000: bool = True, *,
                 use_data_constructor: bool = True,
                 duplicate_depth_prob: float = 0.0,
                 no_data_prob: float = 0.0):
        """
        Default constructor, given the NMEA2000 object that's doing the data capture
        :param emit_nmea0183:
        :param emit_nmea2000:
        :param use_data_constructor: When True, use data constructor for data packets. When False,
            use buffer constructor for data packets.
        :param duplicate_depth_prob: Probability of generating duplicate depth values
        :return:
        """
        # Flag for verbose debug output
        self._m_verbose: bool = False
        # Timestamp information for the current output state
        # self._m_now: Timestamp = Timestamp(0, 0.0, 0)
        # Emit serial strings for NMEA0183
        self._m_serial: bool = emit_nmea0183
        # Emit binary data for NMEA2000
        self._m_binary: bool = emit_nmea2000
        self._use_data_constructor = use_data_constructor
        self._duplicate_depth_prob = duplicate_depth_prob
        self._no_data_prob = no_data_prob

        if not emit_nmea0183 and not emit_nmea2000:
            logger.warning('User asked for neither NMEA0183 or NMEA2000; defaulting to generating NMEA2000')
            self._m_binary = True

    V = TypeVar('V', bound=Union[Any])
    def _get_possible_na_values(self,
                                na_values: Tuple[V, ...],
                                valid_values: Tuple[V, ...]) -> Tuple[V, ...]:
        if self._no_data_prob > 0.0 and \
                random.random() <= self._no_data_prob:
            return na_values
        else:
            return valid_values

    def emit_time(self, state: State, output: Writer) -> None:
        """
        Generate a timestamping message for the current state of the simulator
        :param state:
        :param output:
        :return:
        """
        if self._m_binary:
            self.generate_system_time(state, output)
        if self._m_serial:
            self.generate_zda(state, output)

    def emit_position(self, state: State, output: Writer) -> None:
        """
        Generate messages for the current configuration of the simulator
        :param state:
        :param output:
        :return:
        """
        if self._m_binary:
            self.generate_gnss(state, output)
        if self._m_serial:
            self.generate_gga(state, output)

    def emit_depth(self, state: State, output: Writer) -> None:
        """
        Generate a depth message from the current state of the simulator
        :param state:
        :param output:
        :return:
        """
        if self._m_binary:
            self.generate_depth(state, output)
        if self._m_serial:
            self.generate_dbt(state, output)

    def set_verbose(self, verb: bool):
        """
        Set verbose logging state
        :param verb:
        :return:
        """
        self._m_verbose = verb

    def generate_system_time(self, state: State, output: Writer) -> None:
        """
        Generate NMEA2000 timestamp information
        :param state: Simulator state to use for generation
        :param output: Output writer to use for serialisation of the simulated system time report
        :return:
        """
        ref_time, = self._get_possible_na_values((ComponentDateTime(NA_DATA_UINT32,
                                                                    datetime_timestamp=NA_DATA_UINT32),),
                                                 (state.ref_time,))

        if self._use_data_constructor:
            data = {
                'date': ref_time.days_since_epoch(),
                'timestamp': ref_time.seconds_in_day(),
                'elapsed_time': ref_time.tick_count_to_milliseconds(),
                'data_source': 0
            }
            pkt: lf.DataPacket = lf.SystemTime(**data)
        else:
            # Use buffer constructor
            buffer = struct.pack('<HdLB',
                                 ref_time.days_since_epoch(),
                                 ref_time.seconds_in_day(),
                                 ref_time.tick_count_to_milliseconds(),
                                 0)
            pkt: lf.DataPacket = lf.SystemTime(buffer=buffer)

        output.record(pkt)

    def generate_attitude(self, state: State, output: Writer) -> None:
        """
        Generate attitude message containing estimates of roll, pitch, and yaw of the ship
        :param state: Simulator state to use for generation
        :param output: Output writer to use for serialisation of the simulated system time report
        :return:
        """
        if self._use_data_constructor:
            data = {
                'date': state.ref_time.days_since_epoch(),
                'timestamp': state.ref_time.seconds_in_day(),
                'elapsed_time': state.ref_time.tick_count_to_milliseconds(),
                'yaw': DUMMY_YAW,
                'pitch': DUMMY_PITCH,
                'roll': DUMMY_ROLL
            }
            pkt: lf.DataPacket = lf.Attitude(**data)
        else:
            # Use buffer constructor
            buffer = struct.pack('<HdIddd',
                                 state.ref_time.days_since_epoch(),
                                 state.ref_time.seconds_in_day(),
                                 state.ref_time.tick_count_to_milliseconds(),
                                 DUMMY_YAW,
                                 DUMMY_PITCH,
                                 DUMMY_ROLL)
            pkt: lf.DataPacket = lf.Attitude(buffer=buffer)

        output.record(pkt)

    def generate_gnss(self, state: State, output: Writer) -> None:
        """
        Generate a GNSS packet using the current state information
        :param state: Simulator state to use for generation
        :param output: Output writer to use for serialisation of the simulated GNSS report
        :return:
        """
        # Simulate random generation of no-data values
        lat, lon = self._get_possible_na_values((NA_DATA_DOUBLE, NA_DATA_DOUBLE),
                                                (state.current_latitude, state.current_longitude,))
        if self._use_data_constructor:
            data = {
                'date': state.sim_time.days_since_epoch(),
                'timestamp': state.sim_time.seconds_in_day(),
                'elapsed_time': state.sim_time.tick_count_to_milliseconds(),
                'msg_date': state.sim_time.days_since_epoch(),
                'msg_timestamp': state.sim_time.seconds_in_day(),
                'latitude': lat,
                'longitude': lon,
                'altitude': -19.323,
                'rx_type': 0,   # GPS
                'rx_method': 2, # DGNSS
                'num_svs': 12,
                'horizontal_dop': 1.5,
                'position_dop': 2.2,
                'sep': 22.3453,
                'n_refs': 1,
                'refs_type': 4, # All constellations
                'refs_id': 12312,
                'correction_age': 2.32
            }

            pkt: lf.DataPacket = lf.GNSS(**data)
        else:
            # Use buffer constructor
            # H = sim_time.days since epoch
            # d = sim_time.seconds in day
            # I = sim_time.tick_count milliseconds
            # H = sim_time.days since epoch
            # d = sim_time.seconds in day
            # d = curr lat
            # d = curr lon
            # d = altitude
            # B = rx_type
            # B = rx_method
            # B = num_SVs
            # d = hdop
            # d = pdop
            # d = sep
            # B = n ref stations
            # B = ref station type
            # H = ref station ID
            # d = correction age
            buffer = struct.pack('<HdIHddddBBBdddBBHd',
                                 state.sim_time.days_since_epoch(),
                                 state.sim_time.seconds_in_day(),
                                 state.sim_time.tick_count_to_milliseconds(),
                                 state.sim_time.days_since_epoch(),
                                 state.sim_time.seconds_in_day(),
                                 lat,
                                 lon,
                                 -19.323,
                                 0,  # GPS
                                 2,  # DGNSS
                                 12,
                                 1.5,
                                 2.2,
                                 22.3453,
                                 1,
                                 4,  # All constellations
                                 12312,
                                 2.32
                                 )
            pkt: lf.DataPacket = lf.GNSS(buffer=buffer)

        output.record(pkt)

    def generate_depth(self, state: State, output: Writer) -> None:
        """
        Construct a NMEA2000 depth packet using the current state information
        :param state: Simulator state to use for generation
        :param output: Output writer to use for serialisation of the simulated depth report
        :return:
        """
        # Simulate random generation of no-data values
        depth, = self._get_possible_na_values((NA_DATA_DOUBLE,), (state.current_depth,))

        if self._use_data_constructor:
            data = {
                'date': state.sim_time.days_since_epoch(),
                'timestamp': state.sim_time.seconds_in_day(),
                'elapsed_time': state.sim_time.tick_count_to_milliseconds(),
                'depth': depth,
                'offset': 0.0,
                'range': 200.0
            }

            pkt: lf.DataPacket = lf.Depth(**data)
        else:
            # Use buffer constructor
            # H = sim_time.days since epoch
            # d = sim_time.seconds in day
            # I = sim_time.tick_count milliseconds
            # d = state.curr depth
            # d = offset
            # d = range
            buffer = struct.pack('<HdIddd',
                                 state.sim_time.days_since_epoch(),
                                 state.sim_time.seconds_in_day(),
                                 state.sim_time.tick_count_to_milliseconds(),
                                 depth,
                                 0.0, # offset hard-coded to 0
                                 200.0 # range hard-coded to 200
                                 )
            pkt: lf.DataPacket = lf.Depth(buffer=buffer)

        output.record(pkt)
        if self._duplicate_depth_prob > 0.0 and \
                random.random() <= self._duplicate_depth_prob:
            # Duplicate the packet
            output.record(pkt)

    def generate_zda(self, state: State, output: Writer) -> None:
        """
        Generate NMEA0183 timestamp (ZDA) information
        :param state: Simulator state to use for generation
        :param output: Output writer to use for serialisation of the simulated ZDA report
        :return:
        """
        msg = "$GPZDA,{hour:02d}{minute:02d}{second:06.3f},{day:02d},{month:02d},{year:04d},00,00*".format(
            hour=state.sim_time.hour,
            minute=state.sim_time.minute,
            second=state.sim_time.second,
            day=state.sim_time.day,
            month=state.sim_time.month,
            year=state.sim_time.year
        )
        chksum = DataGenerator.compute_checksum(msg)
        msg = f"{msg}{chksum:02X}\r\n"

        if self._use_data_constructor:
            data = {'payload': bytes(msg, 'ascii'),
                    'elapsed_time': state.sim_time.tick_count_to_milliseconds()
                    }

            pkt: lf.DataPacket = lf.SerialString(**data)
        else:
            # Use buffer constructor
            elapsed_bytes = struct.pack('<I', state.sim_time.tick_count_to_milliseconds())
            buffer = elapsed_bytes + bytes(msg, 'ascii')
            pkt: lf.DataPacket = lf.SerialString(buffer=buffer)

        output.record(pkt)

    def generate_gga(self, state: State, output: Writer) -> None:
        """
        Generate a simulated position (GGA) message.  This formats the current state for position as
        required for GGA messages, and then appends a standard trailer to meet the NMEA0183 requirements.
        Since this trailer is always fixed, it won't exercise potential modifications based on changes
        to the ellipsoid separation or antenna height, etc., although those are expected to be very low
        priority for the expected use of the data being generated.
        :param state: Simulator state to use for generation
        :param output: Output writer to use for serialisation of the simulated GGA report
        :return:
        """
        msg = "$GPGGA,{hour:02d}{minute:02d}{second:06.3f}".format(
            hour=state.sim_time.hour,
            minute=state.sim_time.minute,
            second=state.sim_time.second
        )
        formatted_angle = format_angle(state.current_latitude)
        msg = "{msg},{degrees:02d}{minutes:09.6f},{hemisphere}".format(
            msg=msg,
            degrees=formatted_angle.degrees,
            minutes=formatted_angle.minutes,
            hemisphere='N' if formatted_angle.hemisphere == 1 else 'S'
        )
        formatted_angle = format_angle(state.current_longitude)
        msg = "{msg},{degrees:03d}{minutes:09.6f},{hemisphere}".format(
            msg=msg,
            degrees=formatted_angle.degrees,
            minutes=formatted_angle.minutes,
            hemisphere='E' if formatted_angle.hemisphere == 1 else 'W'
        )
        # Dummy remainder of message
        msg = f"{msg},3,12,1.0,-19.5,M,22.5,M,0.0,0000*"
        chksum = DataGenerator.compute_checksum(msg)
        msg = f"{msg}{chksum:02X}\r\n"

        if self._use_data_constructor:
            data = {'payload': bytes(msg, 'ascii'),
                    'elapsed_time': state.sim_time.tick_count_to_milliseconds()
                    }

            pkt: lf.DataPacket = lf.SerialString(**data)
        else:
            # Use buffer constructor
            elapsed_bytes = struct.pack('<I', state.sim_time.tick_count_to_milliseconds())
            buffer = elapsed_bytes + bytes(msg, 'ascii')
            pkt: lf.DataPacket = lf.SerialString(buffer=buffer)

        output.record(pkt)

    def generate_dbt(self, state: State, output: Writer, *,
                     override_depth: float = None) -> None:
        """
        Generate NMEA0183 depth (SDDBT) information
        :param state: Simulator state to use for generation
        :param output: Output writer to use for serialisation of the simulated DBT report
        :param override_depth: Override depth with this value (used for unit testing so as to avoid stochastic depth)
        :return:
        """
        if override_depth is not None:
            depth_metres: float = override_depth
        else:
            depth_metres: float = state.current_depth + state.measurement_uncertainty * state.unit_normal()
        depth_feet: float = depth_metres * 3.2808
        depth_fathoms: float = depth_metres * 0.5468

        msg = "$SDDBT,{feet:.1f},f,{metres:.1f},M,{fathoms:.1f},F*".format(
            feet=depth_feet,
            metres=depth_metres,
            fathoms=depth_fathoms
        )
        chksum = DataGenerator.compute_checksum(msg)
        msg = f"{msg}{chksum:02X}\r\n"

        if self._use_data_constructor:
            data = {'payload': bytes(msg, 'ascii'),
                    'elapsed_time': state.sim_time.tick_count_to_milliseconds()
                    }

            pkt: lf.DataPacket = lf.SerialString(**data)
        else:
            # Use buffer constructor
            elapsed_bytes = struct.pack('<I', state.sim_time.tick_count_to_milliseconds())
            buffer = elapsed_bytes + bytes(msg, 'ascii')
            pkt: lf.DataPacket = lf.SerialString(buffer=buffer)

        output.record(pkt)
        if self._duplicate_depth_prob > 0.0 and \
                random.random() <= self._duplicate_depth_prob:
            # Duplicate the packet
            output.record(pkt)

    @staticmethod
    def compute_checksum(msg: str) -> int:
        """
        Compute a NMEA0183 sentence checksum
        :param msg:
        :return:
        """
        chk: int = 0
        for b in binascii.a2b_qp(msg[1:-1]):
            chk ^= b
        return chk


class Engine:
    """
    Run the core simulator for NMEA data output
    """
    def __init__(self, data_generator: DataGenerator):
        """
        Default constructor for a simulation engine
        """
        # current state information
        self._m_state = State()
        # converter for state to output representation
        self._m_generator = data_generator

    def step_time(self, now: int) -> bool:
        """
        Move the real-world time component of the system state to the elapsed time count provided.  Note that this code can
        be called at any time, but may not step the state until a given target time is reached.
        :param now: Elapsed time count for the current state instant
        :return: True if the state was updated, otherwise false
        """
        if now < self._m_state.target_reference_time:
            return False

        self._m_state.ref_time.update(now)

        self._m_state.target_reference_time = self._m_state.ref_time.tick_count + CLOCKS_PER_SEC

        return True

    def step_position(self, now: int) -> bool:
        """
        Move the position component of the system state to the elapsed time count provided.  Note that this code can
        be called at any time, but may not step the state until a given target time is reached.
        :param now: Elapsed time count for the current state instant
        :return: True if the state was updated, otherwise false
        """
        if now < self._m_state.target_position_time:
            return False

        self._m_state.current_latitude += self._m_state.latitude_scale * self._m_state.position_step
        self._m_state.current_longitude += 1.0 * self._m_state.position_step

        if (now - self._m_state.last_latitude_reversal) / 3600.0 > CLOCKS_PER_SEC:
            self._m_state.latitude_scale = -self._m_state.latitude_scale
            self._m_state.last_latitude_reversal = now

        self._m_state.target_position_time = now + CLOCKS_PER_SEC
        return True

    def step_depth(self, now: int) -> bool:
        """
        Move the depth component of the system state to the elapsed time count provided.  Note that this code can
        be called at any time, but may not step the state until a given target time is reached.
        :param now:
        :return:
        """
        if now < self._m_state.target_depth_time:
            return False

        self._m_state.current_depth += self._m_state.depth_random_walk * self._m_state.unit_normal()

        self._m_state.target_depth_time = now + CLOCKS_PER_SEC + int(CLOCKS_PER_SEC * unit_uniform())

        return True

    def step_engine(self, output: Writer) -> int:
        """
        Move the state of the system forward to the next target time (depending on when the next depth or
        position packet is simulated to occur).  This steps the real-world time, depth, and position
        components of the state as requried, and then generates output packets according to the embedded
        data generator, and writes them to the specified output location.
        :param output:
        :return:
        """
        next_time: int = min(self._m_state.target_depth_time, self._m_state.target_position_time)
        next_time = min(next_time, self._m_state.target_reference_time)

        self._m_state.sim_time.update(next_time)

        time_change: bool = self.step_time(next_time)
        position_change: bool = self.step_position(next_time)
        depth_change: bool = self.step_depth(next_time)

        if time_change:
            self._m_generator.emit_time(self._m_state, output)
        if position_change:
            self._m_generator.emit_position(self._m_state, output)
        if depth_change:
            self._m_generator.emit_depth(self._m_state, output)

        return next_time
