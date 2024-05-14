import os
from pathlib import Path
import tempfile
from typing import Sequence, Optional
import subprocess

import pygmt
import rasterio

from wibl import get_logger

RASTER_NODATA = -99999.
RASTER_MAX = 40_000
RASTER_RES = 0.002
REGION_INSET_MULT = 4

GEBCO_PATH: str = os.getenv('WIBL_GEBCO_PATH')

logger = get_logger()


def gdal_rasterize(dest_rast: Path, src_ds: Path, *,
                   xRes: float,
                   yRes: float,
                   noData: float,
                   attribute: str,
                   outputSRS: str = 'EPSG:4326',
                   format: str = 'GTiff',
                   where: Optional[str] = None,
                   creationOptions: Optional[Sequence] = None) -> subprocess.CompletedProcess:
    """
    Call gdal_rasterize program via subprocess rather than calling osgeo.gdal.Rasterize() because the latter
    fails after cold start in AWS lambda environment (likely due to some deeply buried shared state in the GDAL Python
    bindings).
    :param dest_rast:
    :param src_ds:
    :param xRes:
    :param yRes:
    :param noData:
    :param attribute:
    :param outputSRS:
    :param format:
    :param where:
    :param creationOptions:
    :return:
    """
    args = [
        'gdal_rasterize', '-q',
        '-tr', str(xRes), str(yRes),
        '-a_nodata', str(noData),
        '-a', attribute,
        '-a_srs', outputSRS,
        '-of', format
    ]
    if where:
        args.extend(['-where', where])
    if creationOptions:
        for co in creationOptions:
            args.extend(['-co', co])
    args.extend([src_ds, dest_rast])
    return subprocess.run(args, text=True)


def map_soundings(sounding_geojson: Path,
                  observer_name: str,
                  map_filename_prefix: str) -> Path:
    # Prepare output file in a new temporary directory
    out_path: Path = Path(tempfile.mkdtemp()).absolute()
    map_filename: Path = out_path / map_filename_prefix

    sounding_rast: Path = sounding_geojson.with_suffix('.tif')

    # Generate GeoTIFF of soundings from GeoJSON file
    p: subprocess.CompletedProcess = gdal_rasterize(sounding_rast,
                                                    sounding_geojson,
                                                    format='GTiff',
                                                    outputSRS='EPSG:4326',
                                                    xRes=RASTER_RES,
                                                    yRes=-RASTER_RES,
                                                    noData=RASTER_NODATA,
                                                    creationOptions=['COMPRESS=DEFLATE', 'ZLEVEL=9'],
                                                    attribute='depth',
                                                    where=f"depth > 0 AND depth < {RASTER_MAX}")
    if p.returncode != 0:
        output = f"stdout: {p.stdout}, stderr: {p.stderr}"
        mesg = (f"Unable to rasterize {sounding_geojson} to {sounding_rast} "
                f"due to error: {output}, return code was: {p.returncode}.")
        logger.error(mesg)
        raise Exception(mesg)

    # Get bounds from raster metadata
    with rasterio.open(sounding_rast) as d:
        xmin = d.bounds.left
        xmax = d.bounds.right
        ymin = d.bounds.bottom
        ymax = d.bounds.top

    # Buffer map bounds around data based on the maximum of the x- and y-ranges
    #   to avoid extremely tall or wide maps
    xrng = xmax - xmin
    yrng = ymax - ymin
    buffer = max(xrng, yrng) / 3
    buffer_inset = REGION_INSET_MULT * buffer

    # Setup region, projections and polygons for main map an insets...
    region = [xmin - buffer,
              xmax + buffer,
              ymin - buffer,
              ymax + buffer]
    region_poly = [[region[0], region[2], region[1], region[3]]]

    region_inset = [xmin - buffer_inset,
                    xmax + buffer_inset,
                    ymin - buffer_inset,
                    ymax + buffer_inset]

    global_poly = [[region_inset[0],
                    region_inset[2],
                    region_inset[1],
                    region_inset[3]]]

    center_lon: float = (xmin + xmax) / 2
    center_lat: float = (ymin + ymax) / 2
    global_inset_proj = f"G{center_lon}/{center_lat}/?"

    pygmt.config(FONT_TITLE='20p,Helvetica',
                 FONT_LABEL='12p,Helvetica')
    f = pygmt.Figure()

    title = f"Soundings from '{observer_name}'"
    f.basemap(region=region,
              projection='M16c',
              frame=["afg", f"+t{title}"])

    f.grdimage(GEBCO_PATH,
               region=region,
               projection="M16c",
               cmap='terra',
               dpi=120)

    f.colorbar(position="JBC", frame=["x+lGEBCO 2023 Bathymetry", "y+lm"])

    # Plot soundings
    f.grdimage(sounding_rast, cmap='seis', dpi=300, nan_transparent=True)
    f.colorbar(position="JLM+o-2.0c/0c+w8c",
               box="+gwhite@30+p0.8p,black",
               frame=["x+lSounding depth", "y+lm"])

    # Plot global inset
    with f.inset(
            position="jTR+w2c+o0.25c/0.25c",
            box="+gwhite+p1p+c0.1c"
    ):
        f.coast(
            region='g',
            projection=global_inset_proj,
            land='grey',
            water='white',
            frame='gf'
        )
        f.plot(data=global_poly, style="r+s", pen="0.5p,blue")

    # Plot region inset
    with f.inset(
            position="jTR+w2c/2.2c+o0.25c/2.55c",
            box="+gwhite+p1p+c0.1c"
    ):
        f.coast(
            region=region_inset,
            projection='M2c',
            land='grey',
            water='white'
        )
        f.plot(data=region_poly, style="r+s", pen="0.5p,blue")

    f.psconvert(prefix=map_filename, fmt='f', resize='+m0.2c')

    # Update map_filename with suffix (.pdf) so that it can be returned to the caller
    map_filename = map_filename.with_suffix('.pdf')
    return map_filename
