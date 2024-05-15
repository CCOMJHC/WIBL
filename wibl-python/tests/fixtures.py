import shutil
from pathlib import Path
from typing import IO, AnyStr
import tempfile

import pytest


@pytest.fixture(scope="session")
def data_path() -> Path:
    return Path(Path(__file__).parent, 'data').absolute()


@pytest.fixture(scope="session")
def geojson_path() -> Path:
    return Path(Path(__file__).parent, 'data', 'geojson').absolute()


@pytest.fixture(scope="function")
def tempdir() -> Path:
    tempdir = Path(tempfile.mkdtemp())
    yield tempdir
    shutil.rmtree(tempdir)


def get_named_tempfile(dir: Path, suffix: str) -> IO[AnyStr]:
    return tempfile.NamedTemporaryFile(mode='w',
                                       encoding='utf-8',
                                       newline='\n',
                                       dir=dir,
                                       suffix=suffix,
                                       delete=False)
