# backend_model.py
from wibl_frontend.app_globals import db


class Query(db.Model):
    id = db.Column(db.String(50), primary_key=True, unique=True)
    data = db.Column(db.String(255), nullable=False)
