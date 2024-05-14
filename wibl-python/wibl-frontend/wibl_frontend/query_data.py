from flask import Blueprint, request, jsonify
from flask_login import login_required

from wibl_frontend.app_globals import db

querydata = Blueprint("querydata", __name__)


@querydata.route('/query', methods=['GET'])
@login_required
def query():
    try:
        id1 = request.args.get('id', '')
        db_instance = db.query.filter_by(id=id1).first()

        if db_instance:
         query_result = {"id": db_instance.id, "data": db_instance.data}
        else:
            query_result = {"error": "Item not found"}

        return jsonify(query_result)
    except Exception as e:
        error_message = {"error": str(e)}
        return jsonify(error_message), 500

@querydata.route('/submit', methods=['POST'])
@login_required
def submit():
    try:
        data = request.json.get('data', '')
        new_db_instance = db(id="unique_id", data=data)
        db.session.add(new_db_instance)
        db.session.commit()

        response_data = {"success": "Data submitted successfully"}
        return jsonify(response_data)
    except Exception as e:
        error_message = {"error": str(e)}
        return jsonify(error_message), 500
