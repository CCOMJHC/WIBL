# \file timestamp_data.py
# \brief Read a binary data file from the SB2030 data logger, and generate timestamped data
#
# The SB2030 data logger reports, for each packet received, the elapsed time with respect
# to the logger's time ticker, and the data.  It also estimates the real time for the packet's
# reception time using whatever time information it has available, in real-time, using a forward
# extrapolation of the last time reference.  Of course, this isn't great, because it has to be
# causal.  This code is designed to get around that by reading all of the data to find the best
# time reference information, and then going back through again to provide timestamps for the
# packets based on all of the time reference data.
#    The code is pretty simple, just doing linear interpolation between timestamps of the reference
# time in order to generate the timestamps.  Reference time is, by preference NMEA2000 SystemTime,
# then the timestamps from NMEA2000 GNSS packets, and then finally from NMEA0183 GPGGA packets if
# there's nothing else available.
#
# Copyright (c) 2020, University of New Hampshire, Center for Coastal and Ocean Mapping & NOAA-UNH
# Joint Hydrographic Center.  All Rights Reserved.

import sys
import json
import boto3
import LoggerFile
import datetime as dt
import numpy as np
import pynmea2 as nmea
from urllib.parse import unquote_plus
import uuid

# You may or may not have to do this, depending on whether you fix the path externally, or move
# the data file parser library into the current directory.
sys.path.append(r'../DataParser')

feature_lst = []
ref_times = []
ref_lon = [] 
ref_lat = [] 
depth_table_z = []

s3_client = boto3.client('s3')

class NoTimeSource(Exception):
    pass

def time_interpolation(upload_path, key):
    # Assume that we're dealing with a file, rather than a stream, which is provided as the first
    # argument on the command line; it's a requirement that this is also rewind-able, so that we
    # can take a second pass through the file to determine the timestamps.
    file = open(upload_path, 'rb')

    global ref_times
    global ref_lon
    global ref_lat
    global depth_table_z

    # First pass through the file: we need to count the packets in order to determine what sources
    #of information we have, and should use for timestamping and positioning.

    packet_count = 0        # Total number of packets of all types
    systime_packets = 0     # Count of NMEA2000 SystemTime packets
    depth_packets = 0       # Count of NMEA2000 Depth packets
    gnss_packets = 0        # Count of NMEA2000 GNSS packets
    ascii_packets = 0       # Count of all NMEA0183 packets (which all show up as the same type to start with)
    gga_packets = 0         # Count of NMEA0183 GPGGA packets.
    dbt_packets = 0         # Count of NMEA0183 SDDBT packets.
    zda_packets = 0         # Count of NMEA0183 ZDA packets.

    source = LoggerFile.PacketFactory(file)

    while source.has_more():
        pkt = source.next_packet()
        if pkt is not None:
            if isinstance(pkt, LoggerFile.SystemTime):
                systime_packets += 1
            if isinstance(pkt, LoggerFile.Depth):
                depth_packets += 1
            if isinstance(pkt, LoggerFile.GNSS):
                gnss_packets += 1
            if isinstance(pkt, LoggerFile.SerialString):
                # Note that parsing the NMEA string doesn't guarantee that it's actually valid,
                # and you can end up with problems later on when getting at the data.
                msg = nmea.parse(pkt.payload.decode('ASCII'))
                if isinstance(msg, nmea.GGA):
                    gga_packets += 1
                if isinstance(msg, nmea.DBT):
                    dbt_packets += 1
                if isinstance(msg, nmea.ZDA):
                    zda_packets += 1
                ascii_packets += 1
            packet_count += 1

    print("Found " + str(packet_count) + " packet total")
    print("Found " + str(systime_packets) + " NMEA2000 SystemTime packets")
    print("Found " + str(depth_packets) + " NMEA2000 Depth packets")
    print("Found " + str(gnss_packets) + " NMEA2000 Position packets")
    print("Found " + str(ascii_packets) + " NMEA0183 packets")
    print("Found " + str(gga_packets) + " NMEA0183 GGA packets")
    print("Found " + str(dbt_packets) + " NMEA0183 DBT packets")
    print("Found " + str(zda_packets) + " NMEA0183 ZDA packets")

    # We need to decide on the source of master time provision.  In general, we prefer to use NMEA2000
    # SystemTime if it's available, but otherwise use either GNSS information for NMEA2000, or ZDA
    # information for NMEA0183, preferring GNSS if both are available.  The ordering reflects the idea
    # that NMEA2000 should have lower (or at least better controlled) latency than NMEA0183 due to not
    # being on a 4800-baud serial line.

    use_systime = False
    use_zda = False
    use_gnss = False
    if systime_packets > 0:
        use_systime = True
    else:
        if gnss_packets > 0:
            use_gnss = True
        else:
            if zda_packets > 0:
                use_zda = True
            else:
                raise NoTimeSource()

    # Second pass through the file, converting into the lists needed for interpolation, using the time source
    # determined above.

    time_table_t = []
    time_table_reftime = []
    position_table_t = []
    position_table_lon = []
    position_table_lat = []
    depth_table_t = []
    depth_table_z = []

    seconds_per_day = 24.0 * 60.0 * 60.0

    file.seek(0)
    source = LoggerFile.PacketFactory(file)
    while source.has_more():
        pkt = source.next_packet()
        if pkt is not None:
            if isinstance(pkt, LoggerFile.SystemTime):
                if use_systime:
                    time_table_t.append(pkt.elapsed)
                    time_table_reftime.append(pkt.date*seconds_per_day + pkt.timestamp)
            if isinstance(pkt, LoggerFile.Depth):
                depth_table_t.append(pkt.elapsed)
                depth_table_z.append(pkt.depth)
            if isinstance(pkt, LoggerFile.GNSS):
                if use_gnss:
                    time_table_t.append(pkt.elapsed)
                    time_table_reftime.append(pkt.date*seconds_per_day + pkt.timestamp)
                position_table_t.append(pkt.elapsed)
                position_table_lat.append(pkt.latitude)
                position_table_lon.append(pkt.longitude)
            if isinstance(pkt, LoggerFile.SerialString):
                try:
                    msg = nmea.parse(pkt.payload.decode('ASCII'))
                    if isinstance(msg, nmea.ZDA):
                        if use_zda:
                            timestamp = pkt.elapsed
                            reftime = dt.datetime.combine(msg.datestamp, msg.timestamp)
                            time_table_t.append(timestamp)
                            time_table_reftime.append(reftime.timestamp())
                    if isinstance(msg, nmea.GGA):
                        # Convert all of the elements first to make sure we have valid conversion
                        timestamp = pkt.elapsed
                        latitude = msg.latitude
                        longitude = msg.longitude
                        # Add all of the elements as a group
                        position_table_t.append(timestamp)
                        position_table_lat.append(latitude)
                        position_table_lon.append(longitude)
                    if isinstance(msg, nmea.DBT):
                        timestamp = pkt.elapsed
                        depth = msg.depth_meters
                        depth_table_t.append(timestamp)
                        depth_table_z.append(depth)
                except nmea.ParseError as e:
                    print('Parse error: {}'.format(e))
                    continue
                except AttributeError as e:
                    print('Attribute error: {}'.format(e))
                    continue

    print('Reference time table length = ', len(time_table_t))
    print('Position table length = ', len(position_table_t))
    print('Depth observations = ', len(depth_table_t))

    # Finally, do the interpolations to generate the output data
    ref_times = np.interp(depth_table_t, time_table_t, time_table_reftime)
    ref_lat = np.interp(depth_table_t, position_table_t, position_table_lat)
    ref_lon = np.interp(depth_table_t, position_table_t, position_table_lon)
    

def geojson_translation(upload_path, key):
    #geojson formatting - Taylor Roy
    #based off https://ngdc.noaa.gov/ingest-external/#_testing_csb_data_submissions example geojson

    file_name = key

    boat_information = file_name.split("+", 1)

    print(file_name)
    for i in range(len(depth_table_z)):
        #print("[", i, "]: ", ref_times[i], ref_lon[i], ref_lat[i], depth_table_z[i])
        feature_dict = {
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [
            ref_lon[i],
            ref_lat[i]
            ]
        },
        "properties": {
            "depth": depth_table_z[i],
            "time": ref_times[i]
        }
        }

        feature_lst.append(dict(feature_dict))


    final_json_dict = {
        "type": "FeatureCollection",
        "crs": {
        "type": "name",
        "properties": {
            "name": "EPSG:4326"
        }
        },
        "properties": {
        "platform": {
            "name": boat_information[1].replace(".bin", ""),
            "uniqueID": boat_information[0]
        }
        },
        "features": feature_lst
    }

    #dump this to a text file that saves into a different bucket
    print(json.dumps(final_json_dict))

    bucket_name = "csb-submission"
    s3_path = file_name.replace(".bin", "") + ".json"
    s3 = boto3.resource("s3")

    encoded_string = json.dumps(final_json_dict).encode("utf-8")

    s3.Bucket(bucket_name).put_object(Key=s3_path, Body=encoded_string)


def lambda_handler(event, context):
    # TODO implement
    
    for record in event['Records']:
        bucket = record['s3']['bucket']['name']
        key =  unquote_plus(record['s3']['object']['key'])
        download_path = '/tmp/{}{}'.format(uuid.uuid4(), key)
        
        s3_client.download_file(bucket, key, download_path)
        
        #process_geojson(download_path, str(key))
        time_interpolation(download_path, str(key))
        geojson_translation(download_path, key)
        
    return {
        'statusCode': 200,
        'body': json.dumps('Hello from Lambda!')
    }

    