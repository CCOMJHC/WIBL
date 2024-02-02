from io import BytesIO
import os
from flask import Flask, render_template, request, send_file
from flask_sqlalchemy import SQLAlchemy 

MANAGER_DATABASE_URI = os.environ.get('MANAGER_DATABASE_URI', 'sqlite:///database.db')

app = Flask(__name__) # WIBL-Manager
app.config['SQLALCHEMY_DATABASE_URI'] = MANAGER_DATABASE_URI
#'sqlite:///db.sqlite3' obsolete
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False 
db2 = SQLAlchemy(app)

class Upload(db2.Model):
    id = db2.Column(db2.Integer, primary_key=True)
    filename = db2.Column(db2.String(50))
    data = db2.Column(db2.LargeBinary)

@app.route('/home', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        file = request.files['file']

        upload = Upload(filename=file.filename, data=file.read())
        db2.session.add(upload)
        db2.session.commit()

        return f'Uploaded: {file.filename}'
    elif request.method == 'GET':
        upload_id = request.args.get('upload_id')
        if upload_id:
           upload = Upload.query.filter_by(id=upload_id).first()

           if upload:
                # Return the file as a downloadable response
               return send_file(BytesIO(upload.data), attachment_filename=upload.filename, as_attachment=True)
           else:
                return "File not found."

        
    return render_template('home.html')

@app.route('/download/<upload_id>')
def download(upload_id):
    upload = Upload.query.filter_by(id=upload_id).first()
    return send_file(BytesIO(upload.data), attachment_filename=upload.filename, as_attachment=True)
