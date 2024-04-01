from io import BytesIO
import os
from flask import Flask, render_template, request, send_file, Blueprint, flash, redirect, url_for
from flask_cors import CORS, cross_origin
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

# enable cors
cors = CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'
# var for current working dir

cwd = os.getcwd()

UPLOAD_FOLDER = cwd + '/file_upload/'

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
@cross_origin(origin='*')
@login_required
def home():
    print("Made it to query_main.home() method")


    #172.17.0.1 is the "default docker bridge link", required for the local connectivity
    #between containers: https://github.com/HTTP-APIs/hydra-python-agent/issues/104
    # series of GET checks to ensure connectivity
    connectManager = requests.get('http://manager:5000/heartbeat')
    print(f"Result of request to Manager/Heartbeat: {connectManager}")

    connectMoreManager = requests.get('http://manager:5000/wibl/all')
    print(f"Result of request to Manager/wibl/all: {connectMoreManager}")
    print(json.dumps(connectMoreManager.json()))

    connectManagerGeoJson = requests.get('http://manager:5000/geojson/all')
    print(f"Result of request to Manager/geojson/all: {connectManagerGeoJson}")
    print(json.dumps(connectManagerGeoJson.json()))
    

    return render_template("home.html")


@query_main.route('/home', methods=['GET', 'POST', 'PUT', 'DELETE'])
@cross_origin(origin='*')
@login_required
def index():

    print("made it to query_main.index() - file upload")
    print(UPLOAD_FOLDER) 

    def formatURL():
        #TODO: make sure input is sanitized!!!
       f = str(request.get_data().decode())
       print(f"FILE NAME: {f}")
       baseURL = 'http://manager:5000/' 
       url = ''
       if f.endswith('.wibl'):
           url = baseURL + 'wibl/' + f
       elif f.endswith('.geojson'):
           url = baseURL+ 'geojson/' + f
       print(f"URL TO GO: {url}") 

       return url

    if request.method == 'POST':

        print("MADE IT TO POST METHOD")

        # post request initializes file, does not need payload or data. doesnt even transfer a file, just initializes space in the DB
        # distinguish if either wibl/json to correctly set size
        fileUp = requests.post(formatURL(), json={'size':10.4})

        print(f"File Post Status: {fileUp}")

        return redirect(url_for('query_main.index'))
        #return 'File Uploaded!'

    """
    #TODO: needs work
    if request.method == 'GET':

        print("MADE IT TO GET METHOD")

        upload_id = request.args.get('upload_id')

        print(f"UPLOAD ID: {upload_id}")
        if upload_id:

           url = 'http://manager:5000/wibl/' + upload_id

           fileGet = requests.get(url)
           print(json.dumps(fileGet.json()))
           print(f"File Get Status: {fileGet}")

           upload = Upload.query.filter_by(id=upload_id).first()

           if upload:
                # Return the file as a downloadable response
               return send_file(BytesIO(upload.data), attachment_filename=upload.filename, as_attachment=True)
           else:
                return "File not found."
           """


    if request.method == 'PUT':
        print("IN PUT FUNCTION")
        filePut = requests.put(formatURL(), json={'logger':'Logger A', 'platform': 'USS Tallship'})
        print(f"File Update Status: {filePut}")
        print(json.dumps(filePut.json()))

        #return redirect(url_for('query_main.index'))
        return ''

    #Delete Method
    if request.method == "DELETE":
        print("IN DELETE FUNCTION")
        fileDelete = requests.delete(formatURL())
        print(f"File Delete Status: {fileDelete}")

        #return redirect(url_for('query_main.index'))
        return ''

    return render_template('home.html')

@query_main.route('/download')
@login_required
def download():
    #arg upload_id
    """
    upload = Upload.query.filter_by(id=upload_id).first()
    return send_file(BytesIO(upload.data), attachment_filename=upload.filename, as_attachment=True)
    """
    print("MADE IT TO GET METHOD")

    upload_id = request.args.get('upload_id')

    print(f"UPLOAD ID: {upload_id}")

    url = 'http://manager:5000/'

    if upload_id.endswith('.wibl'):
       url = url + 'wibl/' + upload_id
    elif upload_id.endswith('.geojson'):
       url = url + 'geojson/' + upload_id
    else:
        url += upload_id

    fileGet = requests.get(url)
    print(json.dumps(fileGet.json()))
    print(f"File Get Status: {fileGet}")

    #return f'File Downloaded {json.dumps(fileGet.json())}'
    fileGet = requests.get(url)
    #should return some sort of list
    json_output = fileGet.json()
    print(json_output)
    #https://stackoverflow.com/questions/46831044/using-jinja2-templates-to-display-json
    print(f"File Get Status: {fileGet}")

    loggers = request.args.get('loggers')
    if loggers:
        print(loggers)

        #getting unique loggers (and other attributes?) from the returned json.
        #key is logger, value is # occurances
        unqiue_loggers = {}
        for x in json_output:
            if x['logger'] not in unqiue_loggers:
            unqiue_loggers[x['logger']] = 1
        else:
            unqiue_loggers[x['logger']] = unqiue_loggers.get(x['logger']) + 1
        

        unqiue_loggers_output = unqiue_loggers.items()
        return render_template('display_json.html', 
                              loggers=unqiue_loggers_output,data=json_output)
        
    else:
        return render_template("home.html")
