import tempfile
from pathlib import Path
import os

from wibl.core.util import geojson_pt_to_ln

from tests.fixtures import geojson_path, tempdir, get_named_tempfile


def test_geojson_pt_to_ln(geojson_path, tempdir):
    filename = '00e8421e-abf2-437e-8873-a886f09a84ae.json'
    out_fp = get_named_tempfile(tempdir, suffix='.json')
    geojson_pt_to_ln(lambda l, f: open(os.path.join(l, f)), str(geojson_path), filename, out_fp)
    ln_geojson: Path = Path(out_fp.name)
    out_fp.close()
    assert ln_geojson.exists() and ln_geojson.is_file()
    assert ln_geojson.stat().st_size > 0
