from pathlib import Path
from importlib import resources

from flask_sqlalchemy import SQLAlchemy

__version__ = '1.0.0'


db = SQLAlchemy()


def get_templates_path(templates_dir: str = 'templates') -> Path:
    return Path(
        str(resources.files('wibl_frontend').joinpath(templates_dir))
    )
