## \file GeoJSONConvert.py
# \brief Convert the interpolated data from the logger into correctly formatted GeoJSON data for DCDB
#
# The data logger provides data in binary format, and the Timestamping.py module reads that format
# (using LoggerFile.py) and then fixes the timestamps, end up with a dictionary that contains the
# reference times for each depth measurement, along with the depth in metres and position in latitude
# and logitude.  The code here converts this to the GeoJSON format required by DCDB for submission.
#
# This code is based on work done by Taylor Roy et al., as part of a UNH Computer Science undergraduate
# programme final year project, and then modified for slightly better maintainability.
#
# Copyright 2021 Center for Coastal and Ocean Mapping & NOAA-UNH Joint
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

import json
from datetime import datetime, timezone
from typing import Dict, Any

import deepmerge

from wibl.core import getenv, Lineage
from wibl.core.algorithm import AlgorithmPhase
from wibl.core.algorithm.runner import run_algorithms


FMT_OBS_TIME='%Y-%m-%dT%H:%M:%S.%fZ'


def translate(data: Dict[str,Any], lineage: Lineage, filename: str, config: Dict[str,Any], *,
              process_algorithms: bool = False) -> Dict[str,Any]:
    """
    Translate from the internal working data dictionary to the GeoJSON structure required by
    DCDB for upload.  This forms the structure for the metadata in addition to re-structuring the
    core data, and fills in any metadata that was stored in the logger, any algorithm information
    and any lineage data.  The current output metadata format is based on IHO Crowd-sourced
    Bathymetry Working Group document B.12 v 3.0.0 (2022-10-01) available at
    https://iho.int/uploads/user/pubs/bathy/B_12_CSB-Guidance_Document-Edition_3.0.0_Final.pdf

    :param data:     Data dictionary from time-interpolation and clean-up
    :type data:      Dict[str,Any] with at least 'depth', 'loggername', 'platform', and 'loggerversion'
    :param lineage:  `wibl.core.Lineage` instance used to track any processing done on `data`
    :poram filename: str representing name of original WIBL file being translated to GeoJSON
    :param config:   Configuration parameters from defaults file for instasll
    :type config:    Dict[str,Any] (see config.py for details)
    :param process_algorithms: Bool set True to enable execution of algorithms for `AlgorithmPhase.AFTER_GEOJSON_CONVERSION`
    :return:         Data dictionary with tags required for conversion to GeoJSON for DCDB
    :rtype:          Dict[str,Any]
    :raises:         UnknownAlgorithm if an unknown processing algorithm is encountered
    """
    # Original comment was:
    # geojson formatting - Taylor Roy
    # based on https://ngdc.noaa.gov/ingest-external/#_testing_csb_data_submissions example geojson
    verbose = config.get('verbose', False)
    feature_lst = []

    for i in range(len(data['depth']['z'])):
        timestamp = datetime.fromtimestamp(data['depth']['t'][i], tz=timezone.utc).strftime(FMT_OBS_TIME)
        
        feature_dict = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [
                data['depth']['lon'][i],
                data['depth']['lat'][i]
                ]
            },
            "properties": {
                "depth": data['depth']['z'][i],
                "time": timestamp
            }
        }

        feature_lst.append(dict(feature_dict))

    final_json_dict: dict[str, Any] = {
        "type": "FeatureCollection",
        "crs": {
            "type": "name",
            "properties": {
                "name": "EPSG:4326"
            }
        },
        "properties": {
            "trustedNode": {
                "providerOrganizationName":     "CCOM/JHC, UNH",
                "providerEmail":                "wibl@ccom.unh.edu",
                "uniqueVesselID":               data['loggername'],
                "convention":                   "GeoJSON CSB 3.1",
                "dataLicense":                  "CC0 1.0",
                "providerLogger":               "WIBL",
                "providerLoggerVersion":        data['loggerversion'],
                "navigationCRS":                "EPSG:4326",
                "verticalReferenceOfDepth":     "Transducer",
                "vesselPositionReferencePoint": "GNSS"
            },
            "platform": {
                "uniqueID":                     data['loggername'],
                "type":                         "Ship",
                "name":                         data['platform'],
                "soundSpeedDocumented":         False,
                "positionOffsetsDocumented":    False,
                "dataProcessed":                False
            }
        },
        "features": feature_lst
    }

    if data['metadata'] is not None:
        meta = json.loads(data['metadata'])
        if 'crs' in meta:
            # If 'crs' metadata have been provided, use that instead of the default defined above in ``final_json_dict``.
            # Note: we can't just blindly merge elements from the root of ``data['metadata']``
            # as it could contain GeoJSON metadata that would not be valid, such as "type" != "FeatureCollection".
            final_json_dict['crs'] = meta['crs']
        if 'properties' in meta:
            # For the remaining metadata objects stored in properties, simply deep merge these with the defaults
            # defined above in ``final_json_dict``.
            deepmerge.always_merger.merge(final_json_dict['properties'], meta['properties'])

    # The database requires that the unique ID contains the provider's ID, presumably to avoid
    # namespace clashes.  We therefore check now (after the platform metadata is finalised) to make
    # sure that this is the case.
    provider_id = getenv('PROVIDER_ID')
    if provider_id not in final_json_dict['properties']['trustedNode']['uniqueVesselID']:
        final_json_dict['properties']['trustedNode']['uniqueVesselID'] = provider_id + '-' + final_json_dict['properties']['trustedNode']['uniqueVesselID']
    # In 3.1.0 of the metadata, we need to duplicate the uniqueVeseelID as /properties/platform/uniqueID so that the DCDB
    # data ingestion platform can find this without stress.  It's also a requirement of the schema validator!  We do this last
    # to make sure that any changes to the /properties/trustedNode are propagated
    final_json_dict['properties']['platform']['uniqueID'] = final_json_dict['properties']['trustedNode']['uniqueVesselID']

    if process_algorithms:
        final_json_dict = run_algorithms(final_json_dict,
                                         data['algorithms'],
                                         AlgorithmPhase.AFTER_GEOJSON_CONVERSION,
                                         filename,
                                         lineage,
                                         verbose)

    # The last phase of algorithms has been run, finalize lineage into a list of dicts that can easily be
    # serialized into the GeoJSON output
    if not lineage.empty():
        data['lineage'] = lineage.export()

    if 'lineage' in data:
        if 'processing' not in final_json_dict['properties']:
            final_json_dict['properties']['processing'] = []
        final_json_dict['properties']['processing'] += data['lineage']

    if 'processing' in final_json_dict['properties'] and len(final_json_dict['properties']['processing']) > 0:
        # Make sure /properties/platform/dataProcessed flag reflects the presence of /properties/processing children
        # after all potential processing has been done.
        final_json_dict['properties']['platform']['dataProcessed'] = True

    return final_json_dict
