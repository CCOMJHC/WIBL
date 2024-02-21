from io import BytesIO
import os
from flask import Flask, render_template, request, send_file, Blueprint
from flask_sqlalchemy import SQLAlchemy 
from flask_login import login_required

WEB_DATABASE_URI = os.environ.get('FRONTEND_DATABASE_URI', 'sqlite:///database.db')

app = Flask(__name__) # WIBL-Manager
app.config['SQLALCHEMY_DATABASE_URI'] = WEB_DATABASE_URI
#'sqlite:///db.sqlite3' obsolete
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False 
db2 = SQLAlchemy(app)

query_main = Blueprint('query_main', __name__)
print("query_main Blueprint set")

class Upload(db2.Model):
    id = db2.Column(db2.Integer, primary_key=True)
    filename = db2.Column(db2.String(50))
    data = db2.Column(db2.LargeBinary)

@query_main.route('/home')
@login_required
def home():
    print("Made it to query_main.home() method")
    return render_template("home.html")


@query_main.route('/home', methods=['GET', 'POST'])
@login_required
def index():

    print("made it to query_main.index() - file upload")

    if request.method == 'POST':
        file = request.files['file']
        print("query_main.index() - file name: " + file.filename)
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



@query_main.route('/download/<upload_id>')
@login_required
def download(upload_id):
    upload = Upload.query.filter_by(id=upload_id).first()
    return send_file(BytesIO(upload.data), attachment_filename=upload.filename, as_attachment=True)
