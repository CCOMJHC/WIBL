# backend_model.py
from __init__ import db2

class Query(db2.Model):
    id = db2.Column(db2.String(50), primary_key=True, unique=True)
    data = db2.Column(db2.String(255), nullable=False)
