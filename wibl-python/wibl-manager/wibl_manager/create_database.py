from wibl_manager.app_globals import app, db, s3_client
# Import data models even though we don't directly use them here
# so that SQLAlchemy will be made aware of them before ``db.create_all()`` is called.
from wibl_manager.wibl_data import WIBLData
from wibl_manager.geojson_data import GeoJSONData

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
