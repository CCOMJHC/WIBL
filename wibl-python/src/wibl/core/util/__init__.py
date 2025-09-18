from typing import Callable, IO, List, Dict, Any, AnyStr, Optional
import json
from pathlib import Path

from wibl import get_logger


logger = get_logger()


def open_fs_file_read(directory: str, filename: str) -> Optional[IO[AnyStr]]:
    file_to_merge = Path(directory, filename)
    if not file_to_merge.exists() or not file_to_merge.is_file():
        logger.warning(f"Unabled to open {str(file_to_merge)}: Path does not exist or is not a file.")
        return None
    return open(file_to_merge, 'r')


def merge_geojson(open_geojson: Callable[[str, str], Optional[IO[AnyStr]]],
                  location: str, filenames: List[str], out_geojson_fp, *,
                  fail_on_error: bool = False) -> None:
    """
    Merge multiple geojson files into one geojson file.
    :param geojson_path:
    :param out_geojson_path:
    :param files_glob:
    :param files_to_merge:
    :param fail_on_error:
    :return:
    """
    out_features: List[Dict[str, Any]] = []

    out_dict: Dict[str, Any] = {
        'type': 'FeatureCollection',
        'crs': {
            'type': 'name',
            'properties': {
                'name': 'urn:ogc:def:crs:OGC:1.3:CRS84'
            }
        },
        'features': out_features
    }

    # Read each file to merge
    for filename in filenames:
        file_like = open_geojson(location, filename)
        if file_like is None:
            mesg = f"Unable to merge {filename}: Could not open resource."
            if fail_on_error:
                logger.error(mesg)
                raise Exception(mesg)
            else:
                logger.warning(mesg)
                continue

        tmp_geojson: Dict = json.load(file_like)

        if 'features' not in tmp_geojson:
            mesg = f"Unable to merge features from {filename}: No features found."
            if fail_on_error:
                logger.error(mesg)
                raise Exception(mesg)
            else:
                logger.warning(mesg)
                continue

        tmp_feat: List[Dict[str, Any]] = tmp_geojson['features']
        if not isinstance(tmp_feat, list):
            mesg = (f"Unable to merge features from {filename}: "
                    "Expected 'features' to be an array, but it is not.")
            if fail_on_error:
                logger.error(mesg)
                raise Exception(mesg)
            else:
                logger.warning(mesg)
                continue

        out_features.extend(tmp_feat)

    # Write out merged features
    json.dump(out_dict, out_geojson_fp)


def new_line(pt1: dict, pt2: dict) -> dict:
    line = {
        "type": "Feature",
        "geometry": {
            "type": "LineString",
            "coordinates": [
                pt1["geometry"]["coordinates"],
                pt2["geometry"]["coordinates"]
            ],
        },
        "properties": {
            "depth": min(pt1["properties"]["depth"], pt2["properties"]["depth"]),
            "start_time": pt1["properties"]["time"],
            "end_time": pt2["properties"]["time"]
        }
    }
    return line


def geojson_pt_to_ln(open_geojson: Callable[[str, str], Optional[IO[AnyStr]]],
                     location: str, filename: str, out_geojson_fp) -> None:
    """

    :param open_geojson:
    :param location:
    :param filename:
    :param out_geojson_fp:
    :param fail_on_error:
    :return:
    """
    out_features: List[Dict[str, Any]] = []

    out_dict: Dict[str, Any] = {
        'type': 'FeatureCollection',
        'crs': {
            'type': 'name',
            'properties': {
                'name': 'urn:ogc:def:crs:OGC:1.3:CRS84'
            }
        },
        'features': out_features
    }

    file_like = open_geojson(location, filename)
    if file_like is None:
        mesg = f"Unable to convert point {filename}: Could not open resource."
        logger.error(mesg)
        raise Exception(mesg)

    pt_geojson: Dict = json.load(file_like)

    if 'features' not in pt_geojson:
        mesg = f"Unable to convert point features from {filename}: No features found."
        logger.error(mesg)
        raise Exception(mesg)

    pt_feat: List[Dict[str, Any]] = pt_geojson['features']
    if not isinstance(pt_feat, list):
        mesg = (f"Unable to convert point features from {filename}: "
                "Expected 'features' to be an array, but it is not.")
        logger.error(mesg)
        raise Exception(mesg)

    ln_feat = []

    # Sort pt_feat by time
    sorted_pt = sorted(pt_feat, key=lambda i: i['properties']['time'])

    num_pt: int = len(sorted_pt)
    if num_pt < 2:
        mesg = f"Unable to convert point features from {filename} to lines because there are less than 2 points."
        logger.error(mesg)
        raise Exception(mesg)

    # Iterate by twos
    for j in range(1, num_pt):
        i = j - 1
        pt1 = sorted_pt[i]
        pt2 = sorted_pt[j]
        ln_feat.append(new_line(pt1, pt2))

    out_features.extend(ln_feat)

    # Write out line features
    json.dump(out_dict, out_geojson_fp)