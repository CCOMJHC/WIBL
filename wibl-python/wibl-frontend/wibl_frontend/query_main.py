import os
import uuid
import random
import time
from flask import Flask, render_template, request, Blueprint, redirect, url_for
from flask_sqlalchemy import SQLAlchemy 
from flask_login import login_required
import requests
import json, datetime
import boto3


# werkzeug utils
from werkzeug.utils import secure_filename

WEB_DATABASE_URI = os.environ.get('FRONTEND_DATABASE_URI', 'sqlite:///database.db')

app = Flask(__name__) # WIBL-Manager

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
@login_required
def home():
    print("Made it to query_main.home() method")


    #172.17.0.1 is the "default docker bridge link", required for the local connectivity
    #between containers: https://github.com/HTTP-APIs/hydra-python-agent/issues/104
    # series of GET checks to ensure connectivity
    connectManager = requests.get('http://manager:5000/heartbeat')
    print(f"Result of request to Manager/Heartbeat: {connectManager}")
    """
    connectMoreManager = requests.get('http://manager:5000/wibl/all')
    print(f"Result of request to Manager/wibl/all: {connectMoreManager}")
    print(json.dumps(connectMoreManager.json()))

    connectManagerGeoJson = requests.get('http://manager:5000/geojson/all')
    print(f"Result of request to Manager/geojson/all: {connectManagerGeoJson}")
    print(json.dumps(connectManagerGeoJson.json()))
    """ 

    return render_template("home.html")


@query_main.route('/home', methods=['GET', 'POST', 'PUT', 'DELETE'])
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

    # Initializes metadata entry in the manager
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
    # get method is found in the "download" route
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

    # updates metadata fields/parameters
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

#setup route, after running cloud/localstack commands, curl this route to populate the manager with cloud bucket entries
@query_main.route('/setup')
#@login_required
def setupCloudData():
    #TODO put cloud.localstack here
    s3 = boto3.client('s3',
                      endpoint_url="http://localstack:4566",
                      use_ssl=False,
                      aws_access_key_id='test',
                      aws_secret_access_key='test')
    # check if buckets are live 
    print("ALL BUCKETS PRESENT:")
    print(s3.list_buckets())

    # can do all this with a curl command, curl -X GET http://127.0.0.1:8000/setup
    # c/p some of Toms code for multiple parameters n stuff

    def current_milli_time():
        return round(time.time() * 1000)

    shipNames = ["USS Alabama", "USS Alaska", "USS Albany", "USS Alexandria", "USS Arlington",
          "USS Maine", "USS Maryland", "USS Constitution", "USS Green Bay", "USS Hawaii"]

    loggerNames = []
    for i in range(10):
        loggerNames.append('UNHJHC-wibl-' + str(i))

    manager_endpoint = os.getenv('MANAGEMENT_URL', 'http://host.docker.internal:5000')

    #TODO make a check to see if there is anything on s3 buckets, empty buckets will fail do to no 'contents' field
    wiblBucket = s3.list_objects(Bucket='wibl-test')['Contents']
    geojsonBucket = s3.list_objects(Bucket='geojson-test')['Contents']

    # iterate through each bucket, and post each filetype
    json_array = []
    geojson_array = []

    count = 0

    for i in wiblBucket:

        #file_name = 'wibl_' + str(count)
        #fileid = str(uuid.uuid64())
        #fileid_wibl = fileid + '.wibl'

        print(i['Key'])
        logger = loggerNames[int(count/100)]
        platform = shipNames[int(count/100)]
        observations = random.randint(75000, 125000)
        soundings = random.randint(8000, 12000)

        #end date would be something like 12 to 24 hrs in advance?
        #24*60*60*1000?
        iso_startdate: int = time.time() - (86400 * count)
        iso_enddate = random.randint(12*60*60, 24*60*60) + iso_startdate
        iso_startdate = datetime.datetime.fromtimestamp(iso_startdate).isoformat()
        iso_enddate = datetime.datetime.fromtimestamp(iso_enddate).isoformat()

        status = 1

        json_object = {
            'url' : (manager_endpoint + '/wibl/' + i['Key']),
            'size' : (observations/10000.0),
            'logger' : logger, 'platform' : platform,
            'observations' : observations, 'soundings' : soundings,
            'startTime' : iso_startdate, 'endTime' : iso_enddate,
            'status' : status, 'messages' : '',
        }
        print(json_object.__str__)
        json_array.append(json_object)

        response = requests.post(manager_endpoint + '/wibl/' + i['Key'], json={'size': observations/10000.0})
        response = requests.put(manager_endpoint + '/wibl/' + i['Key'],
                                    json=json_object)
        count+=1
        #fileUp = requests.post('http://manager:5000/wibl/' + i['Key'], json={'size':10.4})

    count = 0

    for i in geojsonBucket:
        print(i['Key'])
        logger = loggerNames[int(count/100)]
        platform = shipNames[int(count/100)]
        observations = random.randint(75000, 125000)
        soundings = random.randint(8000, 12000)

        #end date would be something like 12 to 24 hrs in advance?
        #24*60*60*1000?
        iso_startdate: int = time.time() - (86400 * count)
        iso_enddate = random.randint(12*60*60, 24*60*60) + iso_startdate
        iso_startdate = datetime.datetime.fromtimestamp(iso_startdate).isoformat()
        iso_enddate = datetime.datetime.fromtimestamp(iso_enddate).isoformat()

        status = 1

        json_object_geojson = {
            'url' : (manager_endpoint + '/geojson/' + i['Key']),
            'size' : (observations/10000.0),
            'logger' : logger, 'platform' : platform,
            'observations' : observations, 'soundings' : soundings,
            'status' : status, 'messages' : '',
        }
        print(json_object.__str__)
        geojson_array.append(json_object)

        response = requests.post(manager_endpoint + '/geojson/' + i['Key'], json={'size': observations/10000.0})
        response = requests.put(manager_endpoint + '/geojson/' + i['Key'],
                                    json=json_object_geojson)
        count+=1
        #fileUp = requests.post('http://manager:5000/geojson/' + i['Key'], json={'size':10.4})

    return ''
    
# this route is for the get request, and brings the user into the display_json page to view and filter metadata entries
@query_main.route('/download')
@login_required
def download():
    #arg upload_id
    """
    upload = Upload.query.filter_by(id=upload_id).first()
    return send_file(BytesIO(upload.data), attachment_filename=upload.filename, as_attachment=True)
    """
    print("MADE IT TO GET METHOD")

    url = 'http://manager:5000/'

    #TODO need to make a conditional for when use queries a specific file from display_json
    uploadID = request.args.get('upload_id')

    if uploadID:
        print(f"UPLOAD ID: {uploadID}")

        if uploadID.endswith('.wibl'):
            url = url + 'wibl/' + uploadID
        elif uploadID.endswith('.geojson'):
            url = url + 'geojson/' + uploadID

        individualGet = requests.get(url)
        print(json.dumps(individualGet.json()))
        print(f"File Get Status: {individualGet}")

        return f'File Downloaded {json.dumps(individualGet.json())}'

    else:

        # case when view results button is clicked. First, initalize connect with s3 buckets and update the manager (localstack)
        json_output = []

        filetype = request.args.get('filetype')
        if filetype:
            print(filetype)
        else:
            filetype = 'both'
            print(filetype)

        noWibl = "{'message': 'That WIBL file does not exist.'}"
        noGeoJson = "{'message': 'That GeoJSON file does not exist.'}"

        #determine which files to retrieve

        if filetype == "both" or filetype == "wibl":
            fileGet = requests.get(url + 'wibl/all')
            print(f"File Get Status: {fileGet}")
            wiblJson = fileGet.json()
            if noWibl != str(wiblJson):
                print("Adding WIBL to form table")
                json_output += wiblJson

        if filetype == "both" or filetype == "json":
            #TEST append geojson output to json_output, have it reflect in forms
            geoJsonGet = requests.get(url + 'geojson/all')
            geoJsonJson = geoJsonGet.json()
            #print(geoJsonJson)
            if noGeoJson != str(geoJsonJson):
                print("Adding geoJSON to form table")
                json_output += geoJsonJson
        
        
        print("JSON OUTPUT OF ALL ENTRIES")
        #print(json_output)

        #https://stackoverflow.com/questions/46831044/using-jinja2-templates-to-display-json

        #if you want to query an parameter that may have  more than one argument, must convert from
        #multidict to list
        loggers = request.args.getlist('loggers')
        unqiue_loggers = {}
        if loggers:
            print(loggers)
            print(type(loggers))
            if type(loggers) is str:
                new_loggers = []
                new_loggers.append(loggers)
                loggers = new_loggers
                print(type(loggers))

        sorting = request.args.get('sorting')
        if sorting:
            print(sorting)

        #getting unique loggers (and other attributes?) from the returned json.
        #haha unqiue
        #key is logger, value is # occurances
        output_list = []
        for x in json_output:

            if x['logger'] not in unqiue_loggers:
                unqiue_loggers[x['logger']] = 1
            else:
                unqiue_loggers[x['logger']] = unqiue_loggers.get(x['logger']) + 1

            #check to see if entry has desired logger, if not, removes it from output list
            if loggers:
                print(x['logger'] in loggers)
                if (x['logger'] in loggers) == False:
                    print("removed entry")
                    continue

            #add human readable time to wibl output? only wibl files have these attributes
            if 'starttime' in x and 'endtime' in x:
                if x['starttime'] != 'Unknown':
                    x['readablestarttime'] = datetime.datetime.fromisoformat(x['starttime']).strftime("%d %B, %Y, %H:%M:%S")
                else:
                    x['readablestarttime'] = 'Unknown'
                if x['endtime'] != 'Unknown':
                    x['readableendtime'] = datetime.datetime.fromisoformat(x['endtime']).strftime("%d %B, %Y, %H:%M:%S")
                else:
                    x['readableendtime'] = 'Unknown'
                #use same mechanism for status
                if x['status'] == 1:
                    x['readablestatus'] = 'Processing Successful'
                elif x['status'] == 2:
                    x['readablestatus'] = 'Processing Failed'
                else:
                    x['readablestatus'] = 'Processing In Progress'
            else:
                if x['uploadtime']:
                    x['readableuploadtime'] = datetime.datetime.fromisoformat(x['uploadtime']).strftime("%d %B, %Y, %H:%M:%S")
                else:
                    x['readableuploadtime'] = 'Unknown'
                if x['updatetime']:
                     x['readableupdatetime'] = datetime.datetime.fromisoformat(x['updatetime']).strftime("%d %B, %Y, %H:%M:%S")
                else:
                    x['readableupdatetime'] = 'Unknown'
                #use same mechanism for status
                if x['status'] == 1:
                    x['readablestatus'] = 'Upload Successful'
                elif x['status'] == 2:
                    x['readablestatus'] = 'Upload Failed'
                else:
                    x['readablestatus'] = 'Upload In Progress'

            output_list.append(x)
            
        #print("Output list before sorting:")
        #print(output_list)

        sort_output_list = []

        if sorting and sorting != 'default':
            if sorting == 'filesizeup':
                sort_output_list = sorted(output_list, key=lambda d: d['size'])
            elif sorting == 'filesizedown':
                sort_output_list = sorted(output_list, key=lambda d: d['size'], reverse=True)
            output_list = sort_output_list

        #print("Output list after sorting:")
        #print(output_list)

        unqiue_loggers_output = unqiue_loggers.items()
        return render_template('display_json.html', 
                              loggers=unqiue_loggers_output,data=output_list)

# view visual artifacts, WIP
@query_main.route('/artifact')
def artifact():
    return render_template('artifact.html')    

