from io import BytesIO
import os
from flask import Flask, render_template, request, send_file, Blueprint
from fileinput import filename
from flask_sqlalchemy import SQLAlchemy 
from flask_login import login_required
import requests
import json
import uuid

#from requests_toolbelt import MultipartEncoder
from requests_toolbelt.multipart.encoder import MultipartEncoder

# werkzeug utils
from werkzeug.utils import secure_filename

WEB_DATABASE_URI = os.environ.get('FRONTEND_DATABASE_URI', 'sqlite:///database.db')

app = Flask(__name__) # WIBL-Manager

# var for current working dir
cwd = os.getcwd()

UPLOAD_FOLDER = cwd + '/file_upload'

app.config['SQLALCHEMY_DATABASE_URI'] = WEB_DATABASE_URI

# configure upload folder to store files
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

#'sqlite:///db.sqlite3' obsolete
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False 

#below line may be obsolete
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


    #172.17.0.1 is the "default docker bridge link", required for the local connectivity
    #between containers: https://github.com/HTTP-APIs/hydra-python-agent/issues/104
    # series of GET checks to ensure connectivity
    connectManager = requests.get('http://172.17.0.1:5000/heartbeat')
    print(f"Result of request to Manager/Heartbeat: {connectManager}")

    connectMoreManager = requests.get('http://172.17.0.1:5000/wibl/all')
    print(f"Result of request to Manager/wibl/all: {connectMoreManager}")
    print(json.dumps(connectMoreManager.json()))

    connectManagerGeoJson = requests.get('http://172.17.0.1:5000/geojson/all')
    print(f"Result of request to Manager/geojson/all: {connectManagerGeoJson}")
    print(json.dumps(connectManagerGeoJson.json()))
    

    return render_template("home.html")


@query_main.route('/home', methods=['GET', 'POST'])
@login_required
def index():

    print("made it to query_main.index() - file upload")
    print(UPLOAD_FOLDER)

    if request.method == 'POST':

        # this method doesnt actually put the wibl file in? rather initializes?

        # check if file is actually part of the post request
        """
        if 'file' not in request.files:
            flash('No file has been selected silly')
            return redirect(request.url) # verify
        """
        f = request.files['file']

        """
        # check if a file has actually been selected
        if f.filename == '':
            flash('No selected file, try again')
            return redirect(request.url) # verify
        """
        fname = secure_filename(f.filename)

        # proof of concept, save to staging 'launchpad' dir
        f.save(os.path.join(app.config['UPLOAD_FOLDER'], fname))
        #f.save(fname)

        #convertToBinaryData
        #file = open(str(f.filename), 'rb')
        
        """
        payload = MultipartEncoder({'uploadedFile': (fname, f, 'application/json')})
        #multipart/form-data
        #application/octet-stream
        print("query_main.index() - file name: " + fname)
        """
        fileNameStripped = os.path.splitext(fname)[0]

        #print(f"File name without extension: {fileNameStripped}")
        url = 'http://172.17.0.1:5000/wibl/' + fileNameStripped  #fname

        #headers = {'Content-type': 'application/octet-stream'}

        #fileUp = requests.post(url, data=payload, headers={'Content-Type': payload.content_type, 'Accept':payload.content_type}, json={'size':10.4}) 

        fileUp = requests.post(url, json={'size':10.4})

        print(f"File Upload Status: {fileUp}")

        """
        upload = Upload(filename=file.filename, data=file.read())
        db2.session.add(upload)
        db2.session.commit()
        """
        #TODO: modify return statement to redirect back to home.html
        return f'Uploaded: {f.filename}'

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
